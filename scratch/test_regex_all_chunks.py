import json
import re

with open('data/processed/chunks.json', 'r', encoding='utf-8') as f:
    chunks = json.load(f)

print(f"Total chunks: {len(chunks)}")

pattern = re.compile(r"(?m)^(\d{1,3}\.\s+([A-Z][^\n]{2,90}))")

found_sections = []
for c in chunks:
    txt = c.get('text', '')
    matches = pattern.findall(txt)
    for m in matches:
        sec = m[0].strip()
        # Clean trailing colon or punctuation
        sec = re.sub(r":\s*$", "", sec)
        found_sections.append((c.get('filename'), c.get('page_start'), sec))

print(f"Total numbered section matches found: {len(found_sections)}")
kyc_matches = [s for s in found_sections if s[0] == 'kyc.pdf']
print(f"KYC matches: {len(kyc_matches)}")
for fn, p, s in kyc_matches:
    if any(k in s.lower() for k in ['42.', '43.', '44.', '45.', '46.', '68.', '38.', '33.']):
        print(f"  Page {p}: {s[:80]}")
