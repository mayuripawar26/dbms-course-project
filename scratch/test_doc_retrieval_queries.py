import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from retrieval.document_retriever import DocumentRetriever

retriever = DocumentRetriever()

queries = [
    "circular fund flow closed cycle FATF Recommendation 20 PMLA Section 12 PML Rules suspicious transaction",
    "What are the reporting obligations for circular fund flows under FATF Recommendation 20 and PMLA?",
    "Vikas Trading Syndicate circular fund flow round tripping closed cycles"
]

for q in queries:
    print(f"\nQUERY: {q}")
    results = retriever.search(q, top_k=5)
    for r in results:
        print(f"Rank {r['rank']} | Score: {r['score']} | {r['filename']} | Page {r['page']} | Section: {r['section']}")
        print("  Snippet: " + r['text'][:120].replace('\n', ' '))
