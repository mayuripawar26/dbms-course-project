import sys
import json
import re
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

chunks_path = Path(r"C:\Users\Shreeya B. Kulkarni\Desktop\DBms_project\data\processed\chunks.json")
with open(chunks_path, "r", encoding="utf-8") as f:
    chunks = json.load(f)

print(f"Total chunks: {len(chunks)}")

# Search for Recommendation 20 specifically
print("=== SEARCHING FATF RECOMMENDATION 20 ===")
for c in chunks:
    txt = c.get("text", "")
    sec = c.get("section_heading", "")
    fn = c.get("filename", "")
    if "fatf" in fn.lower():
        if re.search(r"\b20\.\s*Reporting of suspicious transactions\b", txt, re.I) or "recommendation 20" in sec.lower() or "recommendation 20" in txt.lower():
            print(f"MATCH: [{fn}, Page {c.get('page_start')}, Section: '{sec}']")
            print(txt[:400].strip())
            print("=" * 60)

print("\n=== SEARCHING PMLA SECTION 12 & PML RULES ===")
for c in chunks:
    txt = c.get("text", "")
    sec = c.get("section_heading", "")
    fn = c.get("filename", "")
    if "pmla" in txt.lower() or "pml rules" in txt.lower() or "prevention of money-laundering" in txt.lower():
        if "section 12" in txt.lower() or "rule 3" in txt.lower() or "rule 7" in txt.lower() or "rule 8" in txt.lower() or "rule 9" in txt.lower():
            print(f"MATCH: [{fn}, Page {c.get('page_start')}, Section: '{sec}']")
            print(txt[:400].strip())
            print("=" * 60)
