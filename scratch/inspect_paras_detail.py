import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

with open('data/processed/chunks.json', 'r', encoding='utf-8') as f:
    chunks = json.load(f)

for idx in range(971, 977):
    c = chunks[idx]
    print(f"=== INDEX {idx} | ID: {c.get('chunk_id')} | Page: {c.get('page_start')} to {c.get('page_end')} ===")
    print("Document:", c.get('filename'))
    print("Section heading in JSON:", repr(c.get('section_heading')))
    print("Text snippet (first 600 chars):")
    print(c.get('text', '')[:600])
    print("-" * 60)
