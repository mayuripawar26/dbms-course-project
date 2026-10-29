import sys
sys.path.insert(0, ".")
from retrieval.document_retriever import DocumentRetriever

retriever = DocumentRetriever()
for c in retriever.chunks:
    if c.get("filename") == "kyc.pdf" and "beneficial owner" in c.get("text", "").lower():
        text = c.get("text", "")
        # Find lines with paragraph numbers or beneficial owner
        for line in text.split("\n"):
            if "beneficial owner" in line.lower() or "beneficial ownership" in line.lower():
                print(f"Chunk: {c.get('chunk_id')}, Page: {c.get('page_start')}: {line.strip()[:100]}")
