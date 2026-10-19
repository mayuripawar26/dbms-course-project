"""
ingestion/inspect_documents.py

Phase 1 Document Inspection Pipeline
- Scans data/ for all PDF documents without modifying them.
- Analyzes file size, SHA256 checksums, and duplicate detection.
- Inspects PyMuPDF text streams, page counts, and embedded images.
- Distinguishes digitally extractable PDFs from scanned (OCR required) PDFs.
- Gathers title, source, publication date, and category based on document contents.
- Outputs structured inventory to data/metadata/document_inventory.json and reports/document_inventory_report.md.
"""

import os
import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
try:
    import pymupdf as fitz
except ImportError:
    import fitz


def compute_sha256(filepath: Path) -> str:
    """Compute SHA256 hash of a file for exact duplicate detection."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def parse_pdf_date(date_str: str) -> str:
    """Parse PDF date format (e.g., D:20180829173000) into ISO format if possible."""
    if not date_str or not isinstance(date_str, str):
        return ""
    clean = date_str.strip()
    if clean.startswith("D:"):
        clean = clean[2:]
    try:
        # Expected YYYYMMDDHHMMSS or YYYYMMDD
        if len(clean) >= 8:
            year = clean[0:4]
            month = clean[4:6]
            day = clean[6:8]
            return f"{year}-{month}-{day}"
    except Exception:
        pass
    return date_str


def analyze_document_content(doc: fitz.Document, filename: str) -> Dict[str, Any]:
    """Inspect text streams, images, and content markers across all pages."""
    page_count = len(doc)
    page_stats = []
    total_chars = 0
    zero_text_pages = 0
    total_images = 0

    first_pages_text = []

    for page_idx in range(page_count):
        page = doc[page_idx]
        text = page.get_text("text").strip()
        chars = len(text)
        total_chars += chars
        images = len(page.get_images(full=True))
        total_images += images

        if chars == 0:
            zero_text_pages += 1

        if page_idx < 3:
            first_pages_text.append(text)

        page_stats.append({
            "page_number": page_idx + 1,
            "char_count": chars,
            "image_count": images
        })

    avg_chars_per_page = total_chars / page_count if page_count > 0 else 0

    # Determine extraction status
    if total_chars == 0:
        extraction_status = "Scanned (OCR Required)"
    elif zero_text_pages > 0.5 * page_count and avg_chars_per_page < 100:
        extraction_status = "Primarily Scanned (OCR Required)"
    elif zero_text_pages > 0 and avg_chars_per_page >= 100:
        extraction_status = "Mixed (Partially Scanned, Extractable Text Available)"
    else:
        extraction_status = "Extractable Digital Text"

    sample_snippet = "\n---\n".join(first_pages_text)[:2000]

    return {
        "page_count": page_count,
        "total_chars": total_chars,
        "avg_chars_per_page": round(avg_chars_per_page, 2),
        "zero_text_pages": zero_text_pages,
        "total_images": total_images,
        "extraction_status": extraction_status,
        "sample_snippet": sample_snippet,
        "first_page_text": first_pages_text[0] if first_pages_text else ""
    }


def infer_metadata_and_category(filename: str, meta: Dict[str, Any], text_sample: str) -> Dict[str, str]:
    """
    Infer document source, true title, publication date, and category 
    strictly from internal content and metadata, not merely guessing from filename.
    """
    sample_lower = text_sample.lower()
    
    # 1. Source Determination
    source = "Unknown Source"
    if "reserve bank of india" in sample_lower or "rbi/" in sample_lower or "rbi.org.in" in sample_lower:
        source = "Reserve Bank of India (RBI)"
    elif "financial action task force" in sample_lower or "fatf" in sample_lower:
        source = "Financial Action Task Force (FATF)"
    elif "basel committee" in sample_lower:
        source = "Basel Committee on Banking Supervision (BCBS)"
    
    # 2. Category Determination
    category = "Banking & Financial Document"
    if "annual report" in sample_lower or "annual report" in (meta.get("title") or "").lower():
        category = "Official Annual Report"
    elif "master direction" in sample_lower:
        category = "RBI Master Direction (Regulatory Directive)"
    elif "master circular" in sample_lower:
        category = "RBI Master Circular"
    elif "working paper" in sample_lower or "rbi working paper" in sample_lower:
        category = "Research Working Paper (Non-regulatory / Analytical)"
    elif "fatf recommendations" in sample_lower or "international standards on combating money laundering" in sample_lower:
        category = "International AML/CFT Standards"
    elif "cyber security framework" in sample_lower:
        category = "Cyber Security Regulatory Framework"
    elif "know your customer" in sample_lower or "kyc" in sample_lower:
        category = "KYC & Customer Due Diligence Direction"
    elif "credit information" in sample_lower:
        category = "Credit Information Regulation"
    elif "interest rate" in sample_lower:
        category = "Interest Rate Regulatory Direction"
    elif "supervisory" in sample_lower:
        category = "Supervisory Guidelines"
    elif "operational" in sample_lower:
        category = "Operational Guidelines"

    # 3. Document Title
    meta_title = meta.get("title", "").strip() if meta.get("title") else ""
    inferred_title = meta_title
    if not inferred_title or inferred_title.lower().endswith(".pdf") or len(inferred_title) < 5:
        # Extract title from the first non-empty lines
        lines = [line.strip() for line in text_sample.splitlines() if line.strip()]
        if lines:
            inferred_title = " - ".join(lines[:2])
        else:
            inferred_title = Path(filename).stem

    # 4. Publication / Effective Date
    meta_date = parse_pdf_date(meta.get("creationDate", ""))
    pub_date = meta_date
    # Look for common date patterns in header text
    for line in text_sample.splitlines()[:25]:
        line_clean = line.strip()
        for month in ["January", "February", "March", "April", "May", "June", 
                      "July", "August", "September", "October", "November", "December"]:
            if month in line_clean and any(year in line_clean for year in ["2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025", "2026"]):
                pub_date = line_clean
                break
        if pub_date and pub_date != meta_date:
            break

    return {
        "source": source,
        "category": category,
        "title": inferred_title[:120],
        "publication_date": pub_date or "Not explicitly stated"
    }


def inspect_workspace(base_dir: Path) -> Dict[str, Any]:
    """Inspect all PDF documents in data/ and return complete inventory."""
    data_dir = base_dir / "data"
    all_files = [data_dir / f for f in os.listdir(data_dir) if f.lower().endswith(".pdf") and (data_dir / f).is_file()]
    pdf_files = sorted(all_files, key=lambda p: p.name.lower())
    
    seen_hashes: Dict[str, str] = {}
    inventory: List[Dict[str, Any]] = []

    print(f"[*] Found {len(pdf_files)} PDF file(s) in {data_dir}...")

    for pdf_path in pdf_files:
        filename = pdf_path.name
        file_size = pdf_path.stat().st_size
        sha256_hash = compute_sha256(pdf_path)

        # Check duplicate
        is_duplicate = sha256_hash in seen_hashes
        duplicate_of = seen_hashes.get(sha256_hash, None)
        seen_hashes[sha256_hash] = filename

        try:
            doc = fitz.open(pdf_path)
            content_info = analyze_document_content(doc, filename)
            meta = doc.metadata or {}
            inferred = infer_metadata_and_category(
                filename, meta, content_info["sample_snippet"]
            )
            doc.close()
            error = None
        except Exception as e:
            content_info = {
                "page_count": 0,
                "total_chars": 0,
                "avg_chars_per_page": 0,
                "zero_text_pages": 0,
                "total_images": 0,
                "extraction_status": f"Error opening PDF: {str(e)}",
                "sample_snippet": "",
                "first_page_text": ""
            }
            meta = {}
            inferred = {
                "source": "Unknown",
                "category": "Unreadable",
                "title": filename,
                "publication_date": "Unknown"
            }
            error = str(e)

        doc_record = {
            "filename": filename,
            "filepath": str(pdf_path.relative_to(base_dir)),
            "file_size_bytes": file_size,
            "file_size_formatted": f"{file_size / (1024*1024):.2f} MB" if file_size >= 1024*1024 else f"{file_size / 1024:.1f} KB",
            "sha256": sha256_hash,
            "is_duplicate": is_duplicate,
            "duplicate_of": duplicate_of,
            "title": inferred["title"],
            "source": inferred["source"],
            "category": inferred["category"],
            "publication_date": inferred["publication_date"],
            "page_count": content_info["page_count"],
            "total_chars": content_info["total_chars"],
            "avg_chars_per_page": content_info["avg_chars_per_page"],
            "zero_text_pages": content_info["zero_text_pages"],
            "total_images": content_info["total_images"],
            "extraction_status": content_info["extraction_status"],
            "pdf_metadata": {
                "title": meta.get("title"),
                "author": meta.get("author"),
                "creator": meta.get("creator"),
                "producer": meta.get("producer"),
                "creation_date": meta.get("creationDate"),
                "mod_date": meta.get("modDate"),
            },
            "error": error
        }
        inventory.append(doc_record)

    # Save JSON inventory
    metadata_dir = data_dir / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    inventory_json_path = metadata_dir / "document_inventory.json"
    
    summary = {
        "inspection_timestamp": datetime.now().isoformat(),
        "total_documents": len(inventory),
        "total_pages": sum(d["page_count"] for d in inventory),
        "total_extractable_chars": sum(d["total_chars"] for d in inventory),
        "duplicate_count": sum(1 for d in inventory if d["is_duplicate"]),
        "extractable_count": sum(1 for d in inventory if "Extractable" in d["extraction_status"]),
        "scanned_count": sum(1 for d in inventory if "OCR Required" in d["extraction_status"]),
        "documents": inventory
    }

    with open(inventory_json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"[+] Saved structured inventory to: {inventory_json_path}")

    # Generate Markdown Report
    reports_dir = base_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_md_path = reports_dir / "document_inventory_report.md"

    md_lines = [
        "# Document Inventory and Assessment Report",
        "",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Total Documents Inspected:** {summary['total_documents']}",
        f"**Total Pages:** {summary['total_pages']}",
        f"**Total Characters:** {summary['total_extractable_chars']:,}",
        f"**Extractable Digital Documents:** {summary['extractable_count']}",
        f"**Scanned (OCR Required):** {summary['scanned_count']}",
        f"**Duplicate Files:** {summary['duplicate_count']}",
        "",
        "---",
        "",
        "## Document Details Table",
        "",
        "| Filename | Category | Source | Pub Date / Version | Pages | Size | Status |",
        "| --- | --- | --- | --- | --- | --- | --- |"
    ]

    for d in inventory:
        md_lines.append(
            f"| `{d['filename']}` | {d['category']} | {d['source']} | {d['publication_date']} | {d['page_count']} | {d['file_size_formatted']} | {d['extraction_status']} |"
        )

    md_lines.extend([
        "",
        "---",
        "",
        "## Detailed Document Breakdown",
        ""
    ])

    for d in inventory:
        md_lines.extend([
            f"### {d['filename']}",
            f"- **Inferred Title:** {d['title']}",
            f"- **Document Category:** {d['category']}",
            f"- **Issuing Source:** {d['source']}",
            f"- **Publication / Revision Date:** {d['publication_date']}",
            f"- **File Size:** {d['file_size_formatted']} ({d['file_size_bytes']:,} bytes)",
            f"- **SHA256:** `{d['sha256']}`",
            f"- **Duplicate Check:** {'Duplicate of ' + str(d['duplicate_of']) if d['is_duplicate'] else 'Unique'}",
            f"- **Page Count:** {d['page_count']}",
            f"- **Extractable Characters:** {d['total_chars']:,} (avg {d['avg_chars_per_page']} chars/page)",
            f"- **Zero-Text Pages:** {d['zero_text_pages']} / {d['page_count']}",
            f"- **Embedded Images:** {d['total_images']}",
            f"- **Extraction Feasibility:** **{d['extraction_status']}**",
            ""
        ])

    with open(report_md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
    print(f"[+] Saved markdown inspection report to: {report_md_path}")

    return summary


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    summary = inspect_workspace(project_root)
    print("\n--- Summary of Inspection ---")
    print(f"Total Documents: {summary['total_documents']}")
    print(f"Total Pages: {summary['total_pages']}")
    print(f"Digitally Extractable: {summary['extractable_count']}")
    print(f"Scanned / OCR Required: {summary['scanned_count']}")
    print(f"Duplicate Files: {summary['duplicate_count']}")
