import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

with open('data/processed/chunks.json', 'r', encoding='utf-8') as f:
    chunks = json.load(f)

for idx, c in enumerate(chunks):
    txt = c.get('text', '')
    if "gives rise to a reasonable ground of suspicion" in txt.lower() or "suspicious transaction" in c.get('section_heading', '').lower():
        print(f"CHUNK {idx} | Page {c.get('page_start')} | Sec: {c.get('section_heading')}")
        print(txt)
        print("="*60)
