import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from retrieval.document_retriever import DocumentRetriever

retriever = DocumentRetriever()

queries = [
    "What EDD measures apply to non-face-to-face customer onboarding under paragraph 44?",
    "What due diligence and monitoring measures apply to politically exposed persons under paragraph 45?",
    "What diligence measures are required for money mule accounts under RBI Section 68?",
    "What are the reporting obligations for suspicious transactions under FATF Recommendation 20?"
]

for q in queries:
    print(f"\n========================================================")
    print(f"QUERY: {q}")
    results = retriever.search(q, top_k=3)
    for r in results:
        print(f"Rank {r['rank']} [Score: {r['score']:.2f}]: {r['chunk_id']}")
        print(f"  Citation: {r['citation']}")
        print(f"  Rationale: {r['ranking_rationale']}")
        print(f"  Snippet: {r['text'][:120].replace(chr(10), ' ')}")
