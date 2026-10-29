import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

with open('data/processed/chunks.json', 'r', encoding='utf-8') as f:
    chunks = json.load(f)

for idx, c in enumerate(chunks):
    if c.get('filename') == 'kyc.pdf':
        txt = c.get('text', '')
        for p in [42, 43, 44, 45, 46]:
            if f'{p}.' in txt or f'Paragraph {p}' in txt or f'paragraph {p}' in txt:
                print(f"Index: {idx} | ID: {c.get('chunk_id')} | Page: {c.get('page_start')} | Sec: {c.get('section_heading')}")
                for line in txt.splitlines():
                    if f'{p}.' in line or f'paragraph {p}' in line.lower():
                        print(f"   [Para {p} Match]: {line.strip()[:100]}")
