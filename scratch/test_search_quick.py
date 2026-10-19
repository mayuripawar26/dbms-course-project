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

# Test searching for FATF Rec 20 chunk directly
print("Testing search...")
res = retriever.search("FATF Recommendation 20 reporting of suspicious transactions", top_k=3)
for r in res:
    print(r["rank"], r["filename"], r["page"], r["section"], r["score"])
