import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from retrieval.document_retriever import DocumentRetriever

dr = DocumentRetriever()
tests = [
    ('1. CDD', 'Customer Due Diligence (CDD) procedures for bank accounts'),
    ('2. EDD', 'Enhanced Due Diligence (EDD) requirements and customer categories'),
    ('3. Para 44', 'What enhanced due diligence measures apply to non-face-to-face customer onboarding under paragraph 44 of the RBI KYC Directions?'),
    ('4. Para 45', 'What due diligence, senior-management approval, source-of-funds or source-of-wealth, and ongoing monitoring measures apply to politically exposed persons under paragraph 45 of the RBI KYC Directions?'),
    ('5. Ongoing & unusual', 'ongoing due diligence and unusual transactions without economic rationale'),
    ('6. Money-mule & circular', 'money-mule and circular-fund-flow scenarios round tripping'),
    ('7. STR reporting', 'suspicious transaction reporting FIU-IND'),
    ('8. Generic AML/KYC', 'What indicators should a bank examine when assessing potentially suspicious transactions? Explain how ongoing monitoring and source-of-funds checks relate to the available RBI KYC and FATF evidence.'),
    ('9. Unindexed MiCA', 'Explain the applicable EU MiCA requirements using the indexed knowledge base.')
]

for label, q in tests:
    res = dr.search(q, top_k=2)
    print(f"=== {label} ===")
    for r in res:
        print(f"  {r['rank']}. {r['chunk_id']} | Page {r['page']} | {r['citation']} | Score: {r['score']:.2f}")
        print(f"     Excerpt: {r['text'][:120]}...\n")
