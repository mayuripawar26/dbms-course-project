import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from retrieval.document_retriever import DocumentRetriever, tokenize

retriever = DocumentRetriever()
chunk_20 = retriever.chunks[692]
print("Chunk 692 tokens:", tokenize(chunk_20["text"])[:30])
q_tokens = tokenize("FATF Recommendation 20 reporting of suspicious transactions")
print("Query tokens:", q_tokens)
matched = set(tokenize(chunk_20["text"])) & set(q_tokens)
print("Matched tokens:", matched)
