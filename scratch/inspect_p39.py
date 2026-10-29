import sys
sys.path.insert(0, ".")
from retrieval.document_retriever import DocumentRetriever

retriever = DocumentRetriever()
for c in retriever.chunks:
    if c.get("chunk_id") in ("kyc_p39_0040_s1", "kyc_p39_0040_s2"):
        print(f"=== {c.get('chunk_id')} (Page {c.get('page_start')}) ===")
        print(c.get("text"))
