import json
import re
from pathlib import Path
from collections import Counter, defaultdict

# Load original chunks
with open('data/processed/chunks.json', 'r', encoding='utf-8') as f:
    raw_chunks = json.load(f)

print(f"Loaded {len(raw_chunks)} raw chunks.")

# Test section refinement
processed = []
for c in raw_chunks:
    fn = c.get('filename', '')
    p = c.get('page_start', 0)
    txt = c.get('text', '')
    clean_txt = re.sub(r"^\s*\d{1,3}\s*\n+", "", txt).strip()

    if fn == 'kyc.pdf':
        if p == 45:
            # Contains end of 42, 43, and start of 44
            idx44 = clean_txt.find("44. Enhanced Due Diligence")
            if idx44 != -1:
                # Part 1: Section 43
                c1 = dict(c)
                c1['chunk_id'] = f"{c['chunk_id']}_s43"
                c1['section_heading'] = "43. Requirement of PAN / Form No. 60 for Existing Accounts"
                c1['text'] = clean_txt[:idx44].strip()
                processed.append(c1)
                # Part 2: Section 44 intro
                c2 = dict(c)
                c2['chunk_id'] = f"{c['chunk_id']}_s44_intro"
                c2['section_heading'] = "44. Enhanced Due Diligence (EDD) for Non-Face-to-Face Customer Onboarding"
                c2['text'] = clean_txt[idx44:].strip()
                processed.append(c2)
                continue
        elif p == 46:
            # Contains continuation of 44 (the 6 measures) and start of 45
            idx45 = clean_txt.find("45. Accounts of Politically Exposed Persons")
            if idx45 != -1:
                # Part 1: Section 44 measures
                c1 = dict(c)
                c1['chunk_id'] = f"{c['chunk_id']}_s44_measures"
                c1['section_heading'] = "44. Enhanced Due Diligence (EDD) for Non-Face-to-Face Customer Onboarding (Measures)"
                c1['text'] = clean_txt[:idx45].strip()
                processed.append(c1)
                # Part 2: Section 45 intro
                c2 = dict(c)
                c2['chunk_id'] = f"{c['chunk_id']}_s45_intro"
                c2['section_heading'] = "45. Accounts of Politically Exposed Persons (PEPs)"
                c2['text'] = clean_txt[idx45:].strip()
                processed.append(c2)
                continue
        elif p == 47:
            # Contains continuation of 45 (the measures and definition) and 46
            idx46 = clean_txt.find("46. Client accounts opened by professional intermediaries")
            if idx46 != -1:
                # Part 1: Section 45 measures & definition
                c1 = dict(c)
                c1['chunk_id'] = f"{c['chunk_id']}_s45_measures"
                c1['section_heading'] = "45. Accounts of Politically Exposed Persons (PEPs) (Due Diligence & Monitoring Measures)"
                c1['text'] = clean_txt[:idx46].strip()
                processed.append(c1)
                # Part 2: Section 46
                c2 = dict(c)
                c2['chunk_id'] = f"{c['chunk_id']}_s46"
                c2['section_heading'] = "46. Client Accounts Opened by Professional Intermediaries"
                c2['text'] = clean_txt[idx46:].strip()
                processed.append(c2)
                continue

    chunk_copy = dict(c)
    chunk_copy['text'] = clean_txt
    processed.append(chunk_copy)

print(f"Processed into {len(processed)} chunks.")

# Let's inspect the created chunks for 44 and 45
for c in processed:
    if c.get('filename') == 'kyc.pdf' and c.get('page_start') in [45, 46, 47]:
        print(f"ID: {c.get('chunk_id')} | Page: {c.get('page_start')} | Sec: {c.get('section_heading')}")
        print("   Text start:", c.get('text')[:100].replace('\n', ' '))
