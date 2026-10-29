import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from retrieval.graph_retriever import GraphRetriever
from retrieval.query_router import UserSession, UserRole

gr = GraphRetriever()

print("\n--- TEST A: Generic AML Query ---")
res_a = gr.execute_unified_query(
    query="What indicators should a bank examine when assessing potentially suspicious transactions? Explain how ongoing monitoring and source-of-funds checks relate to the available RBI KYC and FATF evidence. Provide citations and do not retrieve or disclose any individual customer's records.",
    session=UserSession.public_session()
)
print("Intent:", res_a.get("intent"))
print("Customer in graph:", bool(res_a.get("graph_context", {}).get("customer")))
print("Docs retrieved:", len(res_a.get("document_evidence", [])))
for d in res_a.get("document_evidence", []):
    print("  -", d.get("citation"))
print("Answer start:\n", res_a.get("answer")[:300])

print("\n--- TEST B: Hypothetical Cross-Border Transaction ---")
res_b = gr.execute_unified_query(
    query="A hypothetical small retail business receives INR 850000 from an overseas account and transfers most of the amount to three unrelated domestic accounts within 30 minutes. The source of funds is unclear. Identify potential AML risk indicators, explain what additional evidence is needed, retrieve applicable RBI KYC and PMLA-related evidence from the indexed knowledge base, and assess whether further investigation or consideration of suspicious transaction reporting may be appropriate. Clearly separate hypothetical facts from actual database records. Do not invent transactions, customers, citations, or legal obligations.",
    session=UserSession.public_session()
)
print("Intent:", res_b.get("intent"))
print("Is hypo:", res_b.get("is_hypothetical_scenario"))
print("Customer in graph:", bool(res_b.get("graph_context", {}).get("customer")))
print("Docs retrieved:", len(res_b.get("document_evidence", [])))
print("Answer start:\n", res_b.get("answer")[:300])

print("\n--- TEST C: Existing Synthetic Customer ---")
res_c = gr.execute_unified_query(
    query="Investigate transaction activity and calculated risk signals for customer CUST_SYNTH_101",
    session=UserSession.officer_session(officer_id="OFF_01"),
    explicit_customer_id="CUST_SYNTH_101"
)
print("Intent:", res_c.get("intent"))
print("Customer:", res_c.get("graph_context", {}).get("customer", {}).get("full_name"))
print("Calculated risks:", len(res_c.get("graph_context", {}).get("calculated_risks", [])))
print("Answer start:\n", res_c.get("answer")[:300])

print("\n--- TEST D: CDD and EDD (Para 44) ---")
res_d = gr.execute_unified_query(
    query="What enhanced due diligence measures apply to non-face-to-face customer onboarding under paragraph 44 of the RBI KYC Directions available in the knowledge base? Cite the exact supporting passages.",
    session=UserSession.public_session()
)
print("Intent:", res_d.get("intent"))
print("Docs retrieved:", len(res_d.get("document_evidence", [])))
for d in res_d.get("document_evidence", []):
    print("  -", d.get("citation"))

print("\n--- TEST E: PEP Requirements (Para 45) ---")
res_e = gr.execute_unified_query(
    query="What due diligence, senior-management approval, source-of-funds or source-of-wealth, and ongoing monitoring measures apply to politically exposed persons under paragraph 45 of the RBI KYC Directions available in the knowledge base? Cite the actual supporting passages and distinguish RBI provisions from FATF recommendations.",
    session=UserSession.public_session()
)
print("Intent:", res_e.get("intent"))
print("Docs retrieved:", len(res_e.get("document_evidence", [])))
for d in res_e.get("document_evidence", []):
    print("  -", d.get("citation"))

print("\n--- TEST F: Missing Regulatory Knowledge (MiCA) ---")
res_f = gr.execute_unified_query(
    query="Explain the applicable EU MiCA requirements using the indexed knowledge base. If the relevant provisions are unavailable, clearly identify the knowledge gap without inventing legal requirements or citations.",
    session=UserSession.public_session()
)
print("Intent:", res_f.get("intent"))
print("Regulation absent:", res_f.get("scenario_analysis", None) and res_f["scenario_analysis"].regulation_absent)
print("Answer start:\n", res_f.get("answer")[:300])

print("\n--- TEST G: Unknown Customer ---")
res_g = gr.execute_unified_query(
    query="Investigate transactions for customer CUST_SYNTH_9999",
    session=UserSession.officer_session(officer_id="OFF_01"),
    explicit_customer_id="CUST_SYNTH_9999"
)
print("Customer not found:", res_g.get("customer_not_found"))
print("Answer start:\n", res_g.get("answer")[:300])
