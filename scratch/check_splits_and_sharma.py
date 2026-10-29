import sys
sys.path.insert(0, ".")
from retrieval.document_retriever import DocumentRetriever
from retrieval.graph_retriever import GraphRetriever

retriever = DocumentRetriever()

def show_chunk(cid):
    for c in retriever.chunks:
        if c.get("chunk_id") == cid:
            print(f"[{cid}] Page {c.get('page_start')} | Section: {c.get('section')}")
            print(f"  Snippet: {c.get('text', '')[:100]}...\n")

show_chunk("kyc_p64_0068_s2")
show_chunk("fatf-recommendations_last_updated_june_2026_p20_0025_s1")
show_chunk("fatf-recommendations_last_updated_june_2026_p20_0025_s2")
show_chunk("kyc_p20_0021_s2")

# Check Sharma resolution
gr = GraphRetriever()
cid, is_ambig, candidates = gr.resolve_customer_name("Sharma")
print(f"Sharma resolution: cid={cid}, is_ambiguous={is_ambig}, candidates={candidates}")

# Check what execute_unified_query does on Sharma
res = gr.execute_unified_query(
    query="Show me account transactions and compliance flags for customer Sharma",
    explicit_customer_name="Sharma"
)
print("Sharma query result keys:", res.keys())
print("needs_clarification:", res.get("needs_clarification"))
