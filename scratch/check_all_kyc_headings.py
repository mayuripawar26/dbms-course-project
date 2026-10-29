import json
import re

with open('data/processed/chunks.json', 'r', encoding='utf-8') as f:
    chunks = json.load(f)

kyc_chunks = [c for c in chunks if c.get('filename') == 'kyc.pdf']

for c in kyc_chunks:
    p = c.get('page_start')
    txt = c.get('text', '')
    headings = re.findall(r"(?m)^(\d{1,3}\.\s+[A-Z][^\n]{2,80})", txt)
    if headings or p in [44, 45, 46, 47, 48]:
        clean_heads = [re.sub(r":\s*$", "", h.strip()) for h in headings]
        print(f"Page {p:2d} (Chunk {c.get('chunk_id')}): Headings in body = {clean_heads} | Chunk Sec = {c.get('section_heading')}")
