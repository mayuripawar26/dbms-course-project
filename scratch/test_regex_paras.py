import re
import json

with open('data/processed/chunks.json', 'r', encoding='utf-8') as f:
    chunks = json.load(f)

for idx in [973, 974, 975]:
    c = chunks[idx]
    txt = c.get('text', '')
    matches_colon = list(re.finditer(r"(?m)^(\d{1,3}\.\s+([A-Z][^\n:]{2,80})):", txt))
    matches_no_colon = list(re.finditer(r"(?m)^(\d{1,3}\.\s+([A-Z][^\n]{2,80}))", txt))
    print(f"Chunk {idx} (page {c.get('page_start')}):")
    print("  Matches with colon:", [m.group(1) for m in matches_colon])
    print("  Matches without colon:", [m.group(1) for m in matches_no_colon])
