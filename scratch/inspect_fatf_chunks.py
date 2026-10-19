import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

with open('data/processed/chunks.json', 'r', encoding='utf-8') as f:
    chunks = json.load(f)

for idx, c in enumerate(chunks):
    if 'fatf' in c.get('filename', '').lower() and 18 <= c.get('page_start', 0) <= 23:
        print(f"CHUNK {idx} | Page {c.get('page_start')} | Section: {c.get('section_heading')}")
        print(c.get('text'))
        print("="*60)
