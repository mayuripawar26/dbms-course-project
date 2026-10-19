import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

with open('data/processed/chunks.json', 'r', encoding='utf-8') as f:
    chunks = json.load(f)

for idx, c in enumerate(chunks):
    txt = c.get('text', '').lower()
    if "maintain a record of all transactions" in txt or "reporting entity shall" in txt or "pmla section 12" in txt:
        print(f"CHUNK {idx} | {c.get('filename')} | Page {c.get('page_start')} | Sec: {c.get('section_heading')}")
        print(c.get('text')[:300])
        print("="*60)

print("Search finished.")
