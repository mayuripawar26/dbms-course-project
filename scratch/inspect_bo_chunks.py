import sys
sys.path.insert(0, ".")
from retrieval.document_retriever import DocumentRetriever

retriever = DocumentRetriever()
print(f"Total chunks in retriever: {len(retriever.chunks)}")

for c in retriever.chunks:
    if c.get("filename") == "kyc.pdf" and 33 <= c.get("page_start", 0) <= 38:
        print(f"ID: {c.get('chunk_id')}, Page: {c.get('page_start')}, Section: {c.get('section')}")
        print(f"  Snippet: {c.get('text', '')[:100]}...\n")
