import json

with open("data/processed/chunks.json", "r", encoding="utf-8") as f:
    chunks = json.load(f)

print(f"Total chunks in chunks.json: {len(chunks)}")

def find_chunks(filename, page=None, text_snippet=None):
    matches = []
    for c in chunks:
        if filename in c.get("filename", ""):
            if page is not None and c.get("page_start") != page:
                continue
            if text_snippet and text_snippet.lower() not in c.get("text", "").lower():
                continue
            matches.append((c.get("chunk_id"), c.get("page_start"), c.get("section", "")[:50], c.get("text", "")[:80]))
    return matches

print("\n--- Beneficial Ownership in kyc.pdf ---")
for m in find_chunks("kyc.pdf", text_snippet="beneficial owner")[:5]:
    print(m)

print("\n--- Section 68 in kyc.pdf ---")
for m in find_chunks("kyc.pdf", page=64):
    print(m)

print("\n--- FATF Rec 19 ---")
for m in find_chunks("fatf", page=20):
    print(m)

print("\n--- Customer Liability in Annual Report ---")
for m in find_chunks("0ANREPORT", page=139):
    print(m)
