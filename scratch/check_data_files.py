import json
import sys
from pathlib import Path

data_dir = Path("data")
pdf_files = list(data_dir.rglob("*.pdf"))
print(f"PDF files found ({len(pdf_files)}):")
for p in pdf_files:
    print(f" - {p}")

with open('data/processed/chunks.json', 'r', encoding='utf-8') as f:
    chunks = json.load(f)

filenames = set(c.get('filename') for c in chunks)
print(f"\nUnique filenames in chunks.json ({len(filenames)}):")
for fn in sorted(filenames):
    print(f" - {fn}")
