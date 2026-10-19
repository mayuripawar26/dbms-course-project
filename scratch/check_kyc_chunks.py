import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

with open('data/processed/chunks.json', 'r', encoding='utf-8') as f:
    chunks = json.load(f)

indices_to_check = [942, 980, 991, 999, 1000]

for idx in indices_to_check:
    c = chunks[idx]
    print(f"--- CHUNK {idx} | Page {c.get('page_start')} | Sec: {c.get('section_heading')} ---")
    print(c.get('text'))
    print("="*60)
