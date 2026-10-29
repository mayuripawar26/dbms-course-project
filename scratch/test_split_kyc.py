import json
import re

with open('data/processed/chunks.json', 'r', encoding='utf-8') as f:
    chunks = json.load(f)

print(f"Original chunks count: {len(chunks)}")

# Let's inspect splitting chunks 973, 974, 975
def inspect_split(chunk):
    clean_txt = re.sub(r"^\s*\d{1,3}\s*\n+", "", chunk.get("text", "")).strip()
    # Regex to find numbered sections like '44. Enhanced Due Diligence...' or '45. Accounts of...' or '46. Client accounts...'
    matches = list(re.finditer(r"(?m)^(\d{1,3}\.\s+([A-Z][^\n]{2,90}))", clean_txt))
    print(f"Chunk {chunk.get('chunk_id')} (Page {chunk.get('page_start')}):")
    print(f"  Existing heading: {chunk.get('section_heading')}")
    print(f"  Matches: {[m.group(1).strip() for m in matches]}")
    if matches:
        for i, m in enumerate(matches):
            start = m.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(clean_txt)
            sec_heading = re.sub(r":\s*$", "", m.group(1).strip())
            sub_text = clean_txt[start:end].strip()
            print(f"    Sub-part {i+1} [{sec_heading}]: {sub_text[:120]}... (len {len(sub_text)})")
    if not matches:
        print("  No heading match inside body.")

for idx in [973, 974, 975]:
    inspect_split(chunks[idx])
