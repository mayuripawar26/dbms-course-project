import sys
sys.path.insert(0, '.')
from scratch.test_retriever_refinement2 import TestDocRetriever2
r = TestDocRetriever2()
q = 'circular fund flow closed cycle FATF Recommendation 20 PMLA Section 12 PML Rules suspicious transaction'

# Let's see what happens to chunk 692 in search
chunk = r.chunks[692]
metadata = r._metadata(chunk)
print("Metadata:", metadata)

from collections import Counter
import math
from retrieval.document_retriever import tokenize, BANKING_ACRONYMS
raw_query_terms = set(tokenize(q))
query_terms = set(raw_query_terms)
for t in raw_query_terms:
    if t in BANKING_ACRONYMS:
        query_terms.update(BANKING_ACRONYMS[t])

tokens = r.tokens_by_doc[692]
doc_len = len(tokens)
term_counts = Counter(tokens)
score = 0.0
matched = []
k1 = 1.5
b = 0.75
for term in query_terms:
    tf = term_counts.get(term, 0)
    if tf == 0:
        continue
    matched.append(term)
    df = r.doc_freq.get(term, 0)
    idf = math.log(1 + (r.total_docs - df + 0.5) / (df + 0.5))
    denominator = tf + k1 * (1 - b + b * doc_len / r.avg_doc_len)
    score += idf * (tf * (k1 + 1)) / denominator

print(f"Base score: {score}, matched: {matched}")
heading_lower = str(metadata.get("section") or "").lower()
body_lower = str(chunk.get("text") or "").lower()
print(f"heading_lower: {heading_lower}")
print(f"is_circular_or_str: True")
import re
print("re.search rec 20:", bool(re.search(r"\b20\.\s*Reporting of suspicious transactions\b", body_lower)))
