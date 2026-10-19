import sys
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from retrieval.document_retriever import DocumentRetriever

retriever = DocumentRetriever()

# Check what chunks exist for Rec 20
rec20_chunks = []
for idx, c in enumerate(retriever.chunks):
    txt = c.get("text", "")
    fn = c.get("filename", "")
    if "fatf" in fn.lower() and ("20." in txt or "recommendation 20" in txt.lower()):
        if "reporting of suspicious transactions" in txt.lower():
            rec20_chunks.append((idx, c))

print(f"Found {len(rec20_chunks)} candidate Rec 20 chunks:")
for idx, c in rec20_chunks:
    print(f"Chunk idx: {idx} | ID: {c.get('chunk_id')} | Page: {c.get('page_start')} | Sec: {c.get('section_heading')}")
    print("  Snippet: " + c.get("text", "")[:180].replace("\n", " "))
