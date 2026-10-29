# GraphRAG Banking Compliance & Risk Intelligence System
## Retrieval & Ranking Evaluation Report

- **Suite Name:** Banking Compliance & GraphRAG Retrieval Evaluation Suite
- **Version:** 2.0.0
- **Evaluation Dataset:** 15 Banking Compliance & Fraud Investigation Categories
- **Corpus:** 1,930 Processed Regulatory Chunks (RBI Master Directions & FATF Standards)

### 1. Macro Retrieval Performance Metrics

| Metric | Value | Percentage / Scale |
| :--- | :--- | :--- |
| **Precision@1** | `1.0000` | **100.0%** |
| **Precision@3** | `0.4103` | **41.0%** |
| **Precision@5** | `0.2769` | **27.7%** |
| **Recall@1** | `0.6500` | **65.0%** |
| **Recall@3** | `0.7000` | **70.0%** |
| **Recall@5** | `0.7538` | **75.4%** |
| **Mean Reciprocal Rank (MRR)** | `1.0000` | Rank-1 reciprocal score |
| **nDCG@3** | `0.7966` | Graded relevance gain at K=3 |
| **nDCG@5** | `0.8040` | Graded relevance gain at K=5 |

### 2. Category-by-Category Results

| ID | Category | P@1 | P@3 | R@3 | RR | nDCG@5 | Top Retrieved Chunk |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `TC01_CDD` | Customer Due Diligence (CDD) | `1` | `0.3333` | `0.5` | `1.0` | `0.7753` | `kyc_p20_0021_s2` |
| `TC02_EDD` | Enhanced Due Diligence (EDD) | `1` | `0.6667` | `0.5` | `1.0` | `0.7044` | `kyc_p45_0046_s44_intro` |
| `TC03_PARA44_NF2F` | Paragraph 44 Non-Face-to-Face Onboarding | `1` | `0.3333` | `1.0` | `1.0` | `0.9468` | `kyc_p46_0047_s44_measures` |
| `TC04_PARA45_PEP` | Paragraph 45 PEP Requirements | `1` | `0.3333` | `1.0` | `1.0` | `1.0` | `kyc_p47_0048_s45_measures` |
| `TC05_MONEY_MULE` | Money Mule Accounts | `1` | `0.3333` | `1.0` | `1.0` | `1.0` | `kyc_p64_0068_s2` |
| `TC06_BENEFICIAL_OWNERSHIP` | Beneficial Ownership | `1` | `0.3333` | `0.3333` | `1.0` | `0.4693` | `kyc_p5_0006` |
| `TC07_SUSPICIOUS_MONITORING` | Suspicious Transaction Monitoring | `1` | `0.3333` | `0.3333` | `1.0` | `0.2323` | `fatf-recommendations_last_updated_june_2026_p20_0025_s2` |
| `TC08_SUSPICIOUS_REPORTING` | Suspicious Transaction Reporting | `1` | `1.0` | `0.6` | `1.0` | `0.9231` | `kyc_p54_0057_s1` |
| `TC09_FATF_REC19` | FATF Recommendation 19 | `1` | `0.3333` | `1.0` | `1.0` | `1.0` | `fatf-recommendations_last_updated_june_2026_p20_0025_s1` |
| `TC10_GENERAL_REGULATORY` | General Regulatory Questions | `1` | `0.3333` | `1.0` | `1.0` | `1.0` | `0anreport201718077745ec9a874db38c991f580ed14242_p139_0162` |
| `TC11_CUSTOMER_SCENARIO` | Customer-Specific Transaction Scenarios | `1` | `0.3333` | `0.3333` | `1.0` | `0.7872` | `fatf-recommendations_last_updated_june_2026_p20_0025_s1` |
| `TC12_MULTI_HOP` | Multi-Hop Graph & Document Evidence | `1` | `0.3333` | `0.5` | `1.0` | `0.6131` | `fatf-recommendations_last_updated_june_2026_p20_0025_s2` |
| `TC13_AMBIGUOUS_CUSTOMER` | Ambiguous Customer Requests | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PASS` |
| `TC14_INSUFFICIENT_EVIDENCE` | Queries with Insufficient Evidence | `N/A` | `N/A` | `N/A` | `N/A` | `N/A` | `PASS` |
| `TC15_PARAPHRASED_QUERY` | Paraphrased Questions (Different Phrasing) | `1` | `0.3333` | `1.0` | `1.0` | `1.0` | `kyc_p46_0047_s44_measures` |

### 3. Key Ranking Enhancements Verified

1. **Paragraph 44 Non-Face-to-Face EDD:** Successfully isolates substantive measures on Page 46 (`kyc_p46_0047_s44_measures`) at **Rank 1**, eliminating previous false Section 43 attribution.
2. **Paragraph 45 PEP Requirements:** Successfully retrieves PEP ongoing monitoring mandates on Page 47 (`kyc_p47_0048_s45_measures`) at **Rank 1** above transitional introductory text.
3. **Money Mule Directives (Section 68):** Ranks official RBI mandate on Page 64 (`kyc_p64_0068`) as top result with zero customer data leakage.
4. **Circular Routing Suppression:** Suppresses FATF Recommendation 29 and ranks Recommendation 20 / Section 68 appropriately for round-tripping cycles.
5. **Scope Limitations & Ambiguity:** Gracefully enforces scope boundary disclosures on unindexed frameworks (e.g. EU MiCA) and triggers interactive clarification for ambiguous customer queries.
