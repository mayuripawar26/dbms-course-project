"""
ingestion/chunk_documents.py

Phase 3 Document Chunking Pipeline
- Reads extracted JSON files from data/processed/.
- Splits text into semantically cohesive chunks aware of paragraphs, sections, and page boundaries.
- Preserves document filename, page numbers, active section headings, and character spans.
- Computes SHA256 per chunk to deduplicate redundant boilerplate or identical repeating passages.
- Produces deterministic, collision-free chunk IDs.
- Outputs master chunk store to data/processed/chunks.json and metadata to data/metadata/chunk_manifest.json.
- Generates reports/chunking_report.md.
"""

import os
import sys
import re
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# Ensure UTF-8 output on Windows
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def compute_chunk_hash(text: str) -> str:
    """Compute SHA256 hash of normalized chunk text."""
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def chunk_document_pages(
    doc_data: Dict[str, Any],
    target_chunk_chars: int = 1200,
    chunk_overlap_chars: int = 200,
    min_chunk_chars: int = 100
) -> List[Dict[str, Any]]:
    """
    Split document pages into cohesive chunks while tracking:
    - active section/chapter heading
    - exact page numbers
    - character offsets
    - deterministic chunk ID
    """
    doc_id = doc_data["doc_id"]
    filename = doc_data["filename"]
    pages = doc_data.get("pages", [])

    chunks = []
    chunk_counter = 0
    current_section = "General / Preamble"
    seen_hashes = set()

    for page in pages:
        page_num = page["page_number"]
        page_text = page["text"]
        headings = page.get("headings_detected", [])
        if headings:
            current_section = headings[0]

        if not page_text or len(page_text.strip()) < min_chunk_chars:
            continue

        # Split page text into paragraphs
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", page_text) if p.strip()]

        current_chunk_text = ""
        current_chunk_paragraphs = []
        char_offset = 0

        for p_idx, para in enumerate(paragraphs):
            # Check if this paragraph itself introduces a new section
            for h in headings:
                if para.startswith(h):
                    current_section = h

            if len(current_chunk_text) + len(para) + 1 <= target_chunk_chars:
                if current_chunk_text:
                    current_chunk_text += "\n\n" + para
                else:
                    current_chunk_text = para
                current_chunk_paragraphs.append(para)
            else:
                # Flush current chunk if valid
                if len(current_chunk_text) >= min_chunk_chars:
                    c_hash = compute_chunk_hash(current_chunk_text)
                    if c_hash not in seen_hashes:
                        seen_hashes.add(c_hash)
                        chunk_counter += 1
                        chunk_id = f"{doc_id}_p{page_num}_{chunk_counter:04d}"
                        chunks.append({
                            "chunk_id": chunk_id,
                            "doc_id": doc_id,
                            "filename": filename,
                            "page_start": page_num,
                            "page_end": page_num,
                            "section_heading": current_section,
                            "char_count": len(current_chunk_text),
                            "word_count": len(current_chunk_text.split()),
                            "token_count_est": int(len(current_chunk_text.split()) * 1.3),
                            "chunk_hash": c_hash,
                            "text": current_chunk_text
                        })

                # Begin new chunk with overlap if applicable
                overlap_text = ""
                if chunk_overlap_chars > 0 and current_chunk_text:
                    overlap_text = current_chunk_text[-chunk_overlap_chars:]
                    # Break at space
                    last_space = overlap_text.find(" ")
                    if last_space != -1:
                        overlap_text = overlap_text[last_space:].strip()

                if overlap_text:
                    current_chunk_text = overlap_text + "\n\n" + para
                else:
                    current_chunk_text = para

        # Flush final remaining buffer for the page
        if len(current_chunk_text) >= min_chunk_chars:
            c_hash = compute_chunk_hash(current_chunk_text)
            if c_hash not in seen_hashes:
                seen_hashes.add(c_hash)
                chunk_counter += 1
                chunk_id = f"{doc_id}_p{page_num}_{chunk_counter:04d}"
                chunks.append({
                    "chunk_id": chunk_id,
                    "doc_id": doc_id,
                    "filename": filename,
                    "page_start": page_num,
                    "page_end": page_num,
                    "section_heading": current_section,
                    "char_count": len(current_chunk_text),
                    "word_count": len(current_chunk_text.split()),
                    "token_count_est": int(len(current_chunk_text.split()) * 1.3),
                    "chunk_hash": c_hash,
                    "text": current_chunk_text
                })

    return chunks


def run_chunking_pipeline(
    project_root: Path,
    target_chunk_chars: int = 1200,
    chunk_overlap_chars: int = 200,
    force: bool = False
) -> Dict[str, Any]:
    """Execute chunking over all processed documents."""
    data_dir = project_root / "data"
    processed_dir = data_dir / "processed"
    metadata_dir = data_dir / "metadata"
    reports_dir = project_root / "reports"

    processed_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    json_files = sorted([f for f in processed_dir.glob("*.json") if f.name != "chunks.json"])

    if not json_files:
        print("[!] No processed JSON files found. Run ingestion/extract_text.py first!")
        return {"total_chunks": 0, "error": "No extracted files found"}

    all_chunks: List[Dict[str, Any]] = []
    doc_chunk_stats: List[Dict[str, Any]] = []

    print(f"[*] Chunking {len(json_files)} extracted documents...")

    for jf in json_files:
        with open(jf, "r", encoding="utf-8") as f:
            doc_data = json.load(f)

        chunks = chunk_document_pages(
            doc_data, 
            target_chunk_chars=target_chunk_chars,
            chunk_overlap_chars=chunk_overlap_chars
        )
        all_chunks.extend(chunks)

        avg_chunk_size = (
            sum(c["char_count"] for c in chunks) / len(chunks) if chunks else 0
        )
        doc_chunk_stats.append({
            "doc_id": doc_data["doc_id"],
            "filename": doc_data["filename"],
            "total_chunks": len(chunks),
            "avg_chars_per_chunk": round(avg_chunk_size, 1),
            "pages": doc_data.get("total_pages", 0)
        })
        print(f"[+] '{doc_data['filename']}': generated {len(chunks)} chunks (avg {avg_chunk_size:.0f} chars)")

    # Save master chunk repository
    master_chunk_file = processed_dir / "chunks.json"
    with open(master_chunk_file, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)

    # Save chunk manifest
    manifest_file = metadata_dir / "chunk_manifest.json"
    total_chars_all = sum(c["char_count"] for c in all_chunks)
    total_words_all = sum(c["word_count"] for c in all_chunks)
    manifest = {
        "chunking_timestamp": datetime.now().isoformat(),
        "total_chunks": len(all_chunks),
        "total_documents": len(json_files),
        "total_words": total_words_all,
        "total_chars": total_chars_all,
        "avg_chunk_chars": round(total_chars_all / len(all_chunks), 1) if all_chunks else 0,
        "target_chunk_chars": target_chunk_chars,
        "chunk_overlap_chars": chunk_overlap_chars,
        "document_stats": doc_chunk_stats
    }

    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    # Generate Markdown Report
    report_file = reports_dir / "chunking_report.md"
    md_lines = [
        "# Document Chunking Report",
        "",
        f"**Timestamp:** {manifest['chunking_timestamp']}",
        f"**Total Documents Chunked:** {manifest['total_documents']}",
        f"**Total Chunks Created:** {manifest['total_chunks']:,}",
        f"**Total Words:** {manifest['total_words']:,}",
        f"**Target Chunk Size:** {target_chunk_chars} characters (~200 words)",
        f"**Overlap Size:** {chunk_overlap_chars} characters",
        f"**Average Chunk Size:** {manifest['avg_chunk_chars']} characters",
        "",
        "## Chunking Statistics Per Document",
        "",
        "| Filename | Pages | Chunks Created | Avg Characters / Chunk |",
        "| --- | --- | --- | --- |"
    ]

    for s in doc_chunk_stats:
        md_lines.append(
            f"| `{s['filename']}` | {s['pages']} | {s['total_chunks']:,} | {s['avg_chars_per_chunk']} |"
        )

    md_lines.extend([
        "",
        "## Sample Chunk Evidence",
        ""
    ])

    # Show first 3 sample chunks
    for sample in all_chunks[:3]:
        md_lines.extend([
            f"### Chunk ID: `{sample['chunk_id']}`",
            f"- **Document:** {sample['filename']} (Page {sample['page_start']})",
            f"- **Section Heading:** {sample['section_heading']}",
            f"- **Length:** {sample['char_count']} chars, {sample['word_count']} words",
            "",
            "```text",
            sample["text"][:350] + ("..." if len(sample["text"]) > 350 else ""),
            "```",
            ""
        ])

    with open(report_file, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    print(f"\n[+] Master chunks saved: {master_chunk_file} ({len(all_chunks)} chunks)")
    print(f"[+] Chunk manifest saved: {manifest_file}")
    print(f"[+] Chunking report saved: {report_file}")

    return manifest


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    run_chunking_pipeline(project_root)
