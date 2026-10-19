import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

with open('data/processed/chunks.json', 'r', encoding='utf-8') as f:
    chunks = json.load(f)

print(f"Total chunks: {len(chunks)}")

for idx, c in enumerate(chunks):
    txt = c.get('text', '')
    fn = c.get('filename', '')
    sec = c.get('section_heading', '')
    pg = c.get('page_start', 0)
    
    # Check for Section 12 of PMLA
    if "section 12" in txt.lower() and ("pml" in txt.lower() or "prevention" in txt.lower() or "act" in txt.lower()):
        print(f"MATCH SEC 12: Chunk {idx} | {fn} | Page {pg} | Section: {sec}")
        print(txt[:300].strip())
        print("-" * 50)
        
    # Check for PML Rules (Maintenance of Records)
    if "pml rules" in txt.lower() or "pml (maintenance of records" in txt.lower() or "maintenance of records) rules" in txt.lower():
        print(f"MATCH PML RULES: Chunk {idx} | {fn} | Page {pg} | Section: {sec}")
        print(txt[:300].strip())
        print("-" * 50)
