import sys
sys.path.insert(0, '.')
from scratch.test_retriever_refinement2 import TestDocRetriever2
r = TestDocRetriever2()
q = 'circular fund flow closed cycle FATF Recommendation 20 PMLA Section 12 PML Rules suspicious transaction'
# find doc_idx of chunk with page 20
idx_20 = None
for i, c in enumerate(r.chunks):
    if c.get('page_start') == 20 and 'fatf' in c.get('filename', '').lower():
        idx_20 = i
        break
print(f"Index of page 20 in r.chunks: {idx_20}")
raw_terms = set(['fatf', 'recommendation', '20', 'pmla', 'suspicious', 'transaction'])
print("Does idx_20 have any of these terms in inverted_index?")
for t in raw_terms:
    postings = [doc_idx for doc_idx, _ in r.inverted_index.get(t, [])]
    if idx_20 in postings:
        print(f"  Yes for {t}")
