# GraphRAG-Based Banking Compliance & Risk Intelligence System

An M.Tech engineering project implementing an intelligent document ingestion, graph knowledge preparation, dynamic risk calculation, and hybrid GraphRAG retrieval pipeline for banking compliance and fraud/AML risk intelligence.

**Architecture Principle:** Operates as a verifiable **GraphRAG system WITHOUT an LLM** (utilizing Neo4j knowledge graphs, BM25 regulatory document retrieval, deterministic financial calculations, and grounded evidence synthesis).

---

## 1. Project Overview & Architecture

The system bridges unstructured regulatory directives with structured financial transaction graphs:

1. **Official Banking Regulations & Directives**: 1,237 indexed chunks across 10 official regulatory PDFs (RBI Master Directions on KYC, Cyber Security, Credit Information, Interest Rates, Operational Guidelines, Supervisory Credit, and FATF 40 Recommendations).
2. **Knowledge Graph Subgraph Engine**: Live Neo4j property graph modeling `Customer`, `Account`, `Transaction`, `RiskIndicator`, and `FraudPattern` entities.
3. **Deterministic Graph Reasoning & Risk Analyzer**: Mathematically verifiable risk calculation rules (fan-in senders, chronological rapid drain, disproportionate turnover-to-income multiples, FATF high-risk jurisdiction screening, circular round-tripping cycles, and dormant account reactivation).
4. **Hybrid GraphRAG Evidence Assembly**: Multi-intent routing separating public educational inquiries from authenticated customer portals, hypothetical scenarios, and multi-customer comparisons.
5. **Explainable Compliance Synthesis**: Grounded reports adhering to strict evidence transparency, explicitly distinguishing confirmed statutory obligations from investigative recommendations.

```
DBms_project/
├── data/
│   ├── [10 Original PDF documents preserved]
│   ├── processed/            # Page-level JSON extractions & 1,237 master chunks.json
│   ├── metadata/             # Document inventory & extraction manifests
│   └── synthetic/            # 7 benchmark customer scenarios with accounts & txs
├── ingestion/
│   ├── inspect_documents.py  # Phase 1: Inspects PDFs, detects OCR status, computes hashes
│   ├── extract_text.py       # Phase 3: Page-level text extraction with PyMuPDF
│   ├── chunk_documents.py    # Phase 3: Semantic paragraph chunking with metadata
│   └── build_graph.py        # Phase 5: Neo4j idempotent knowledge graph builder
├── graph/
│   ├── constraints.cypher    # Uniqueness constraints & performance indexes
│   └── schema.cypher         # Complete Neo4j schema & sample queries
├── retrieval/
│   ├── document_retriever.py # BM25 retriever with acronym expansion & authority mapping
│   ├── graph_retriever.py    # Hybrid graph traversal & multi-modal query orchestrator
│   ├── query_router.py       # Role-based access control & intent classification
│   ├── scenario_analyzer.py  # Parameter extraction without customer keyword binding
│   ├── risk_analyzer.py      # Explainable risk calculation engine with temporal causality
│   ├── evidence_validator.py # Claim-to-evidence statutory verification
│   └── answer_generator.py   # Grounded report generator (deterministic & educational)
├── tests/
│   └── test_pipeline.py      # Automated test suite (51 comprehensive tests)
├── app.py                    # Streamlit interactive UI application
├── .env.example              # Safe environment variables template
├── .gitignore                # Environment secrets and cache protection
├── requirements.txt          # Python dependencies
└── README.md                 # Project documentation
```

---

## 2. Prerequisites & Environment Setup

- **Python**: Python 3.10+ (tested on Python 3.13 on Windows)
- **Neo4j**: Live Neo4j Sandbox, AuraDB, or local Neo4j Desktop / Docker instance. *(If offline, local index fallback ensures full functionality).*

### Step 1: Install Python Dependencies
```powershell
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables
Copy `.env.example` to `.env` and fill in your Neo4j credentials:
```powershell
Copy-Item .env.example .env
```

Example `.env` configuration:
```env
NEO4J_URI=bolt://<sandbox-ip>:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<sandbox-password>
NEO4J_DATABASE=neo4j
```

*(Note: No API keys for OpenAI, Gemini, or third-party LLMs are required. The system operates deterministically).*

---

## 3. Four Core Query Categories

The system strictly isolates customer contexts across 4 distinct operational categories:

### Category A: Generic Regulatory Queries (Mode A - Public)
- **Access Level**: Public / Unauthenticated.
- **Behavior**: Retrieves official RBI / FATF regulatory provisions and provides educational compliance guidance.
- **Privacy Assurance**: Exposes **zero** private customer accounts, balances, or transaction graphs.
- **Example**: `"What are the KYC periodic updation rules and customer due diligence requirements under RBI directions?"`

### Category B: Customer-Specific Investigations (Mode C - Compliance Officer)
- **Access Level**: Authenticated Compliance Officer (`OFFICER` role).
- **Behavior**: Retrieves live Neo4j subgraphs, executes dynamic risk indicators, reconciles ledger transactions, and produces structured 8-section investigation reports.
- **Identity Enforcement**: Requires explicit Customer ID or validated unambiguous customer name.
- **Example**: `"Investigate transaction activity and calculated risk signals for customer CUST_SYNTH_101"`

### Category C: Hypothetical Scenario Analysis (Mode C - Simulation)
- **Access Level**: Public or Compliance Officer.
- **Behavior**: Evaluates hypothetical compliance questions (e.g. large cross-border remittances, immediate sweeps) without binding to database entities.
- **Structure**: Outputs `# Hypothetical Compliance Scenario Analysis (Not Stored Customer Facts)` outlining scenario assumptions, applicable statutory provisions, quantitative detection formulas, thresholds, required evidentiary documents, and limitations.
- **Example**: `"What if an account receives 8.5 lakhs from overseas and immediately drains it?"`

### Category D: Cross-Customer Comparisons (Mode D - Comparative Intelligence)
- **Access Level**: Authenticated Compliance Officer.
- **Behavior**: Independently retrieves and compares two or more customer profiles side-by-side.
- **Isolation Assurance**: Strict data separation guarantees zero cross-customer data leakage.
- **Example**: `"Compare risk profiles of CUST_SYNTH_101 and CUST_SYNTH_106"`

---

## 4. Deterministic Risk Rules & Formulas

Every risk signal in `retrieval/risk_analyzer.py` is explainable, reproducible, and provides complete formulaic inputs:

### 1. Chronological Pass-Through / Rapid Drain Ratio (`IND_PASS_THROUGH_RAPID_DRAIN`)
- **Causality Rule**: Outflows must chronologically succeed inflows (`outflow_time >= inflow_time`) on linked accounts. Absolute time deltas (`abs()`) are prohibited.
- **Formula**:
  $$\text{Drain Ratio} = \frac{\sum \text{Chronologically Subsequent Outflows}}{\sum \text{Preceding Inflows}} \times 100\%$$
- **Threshold**: $\ge 80.0\%$ drained within $180\text{ minutes}$ of receipt.
- **Statutory Source**: RBI KYC Master Direction Section 68 & FATF Money Mule Typology.

### 2. Disproportionate Turnover-to-Income Multiple (`IND_DISPROPORTIONATE_TURNOVER`)
- **Formula**:
  $$\text{Turnover Multiple} = \frac{\text{Aggregate External Inflow Turnover}}{\text{Declared Annual Income}}$$
- **Threshold**: $\ge 3.0\times$ declared annual income.
- **Zero / Missing Income Handling**: If declared income is zero or unrecorded and external turnover exceeds ₹100,000, triggers `IND_TURNOVER_UNVERIFIED_INCOME` without division by zero.
- **Statutory Source**: PMLA Rule 9(1) (Customer Financial Profiling) & RBI KYC Direction Chapter VI.

### 3. Cross-Border & High-Risk Jurisdiction Screening (`IND_CROSS_BORDER_HIGH_RISK_INFLOW`)
- **Verification Rule**: Evaluates counterparty jurisdiction against the dated FATF Public Statement (Call for Action / Blacklist: DPRK, Iran, Myanmar; Increased Monitoring / Greylist: Bulgaria, Cameroon, etc.).
- **Distinction**: Standard cross-border wire transfers without adverse jurisdiction nexus trigger `IND_CROSS_BORDER_WIRE_TRANSFER` (Medium severity) with explicit metadata limitation disclosure, preventing false sanctions attribution.
- **Statutory Source**: FATF Recommendation 19 & RBI KYC Master Direction Section 35 / Section 50.

### 4. Circular / Round-Tripping Flow Detection (`IND_CIRCULAR_ROUTING_DETECTED`)
- **Graph Traversal**: Identifies closed directed transaction cycles: $A_1 \to A_2 \to \dots \to A_n \to A_1$.
- **Strict Metric Separation**:
  1. *Cumulative Ledger Turnover*: Gross debits traversed across the cycle (e.g. ₹14,85,000.00).
  2. *Net Balance Change*: Real external capital movement across the participating accounts (strictly ₹0.00).
  3. *Supported Commercial Variance*: Turnover minus verified commercial activity (₹14,85,000.00 artificial turnover).
  *(These three metrics represent distinct accounting dimensions and are never equated).*
- **Statutory Source**: FATF Recommendation 20 & PML Rules Rule 2(1)(g) (Suspicious Transaction Definition).

### 5. Dormant Account Reactivation (`IND_DORMANT_ACCOUNT_REACTIVATION`)
- **Rule**: Flags active debits/credits on accounts with status `DORMANT` or `INACTIVE` without formal regularisation.
- **Statutory Source**: RBI Master Direction on Customer Service & KYC Periodic Updation.

---

## 5. Synthetic Benchmark Dataset

Located in `data/synthetic/customers.json`, `accounts.json`, and `transactions.json`:

| Customer ID | Entity Name | Type | Typology & Observed Anomaly |
| :--- | :--- | :--- | :--- |
| `CUST_SYNTH_101` | **Arjun Sharma** | INDIVIDUAL | Money Mule: 4 sub-threshold credits (₹1.96L) rapidly swept out (99.2% drain) in 20 mins |
| `CUST_SYNTH_102` | **Priya Verma** | INDIVIDUAL | Unauthorized UPI: Nighttime rapid micro-transfers within 3 minutes |
| `CUST_SYNTH_103` | **Ramesh Chandra** | INDIVIDUAL | Account Takeover (ATO): Password change followed by uncharacteristic high-value transfer |
| `CUST_SYNTH_104` | **Apex Global Consultancy** | CORPORATE | High-Risk Remittance: ₹8.5M transfer from overseas shell jurisdiction (7.1x income multiple) |
| `CUST_SYNTH_105` | **Rajesh Gupta** | INDIVIDUAL | Dormant Reactivation: Inactive account suddenly executing substantial transactions |
| `CUST_SYNTH_106` | **Vikas Trading Syndicate** | CORPORATE | Round-Tripping: 3-hop closed cycle (`ACC_300601` $\to$ `ACC_300602` $\to$ `ACC_300603` $\to$ `ACC_300601`) |
| `CUST_SYNTH_107` | **Sunita Enterprises** | CORPORATE | High Fan-In: Multiple incoming credits aggregated without commercial invoices |

---

## 6. Execution Commands & CLI Examples

### Category A: Generic Regulatory Query (Public Mode)
```powershell
python -m retrieval.graph_retriever --query "What is customer due diligence and enhanced due diligence under RBI KYC directions?" --role public
```

### Category B: Customer Investigation (Compliance Officer Mode)
```powershell
python -m retrieval.graph_retriever --query "Investigate transaction activity and calculated risk signals for customer CUST_SYNTH_101" --customer-id CUST_SYNTH_101 --role officer
```

### Category C: Hypothetical Scenario Simulation
```powershell
python -m retrieval.graph_retriever --query "What if an account receives 8.5 lakhs from overseas and immediately drains it?" --role officer
```

### Category D: Cross-Customer Comparison
```powershell
python -m retrieval.graph_retriever --query "Compare risk profiles of CUST_SYNTH_101 and CUST_SYNTH_106" --role officer
```

### Interactive Streamlit Web Console
```powershell
streamlit run app.py
```
*Access in browser at `http://localhost:8501` to test Public, Customer, and Compliance Officer modes.*

### Automated Test Suite Execution
Run the complete automated regression suite (all 51 unit and regression tests):
```powershell
python -m unittest tests/test_pipeline.py -v
```

---

## 7. Automated Test Verification Summary

The test suite in `tests/test_pipeline.py` contains **51 tests**, all passing cleanly (`OK`):
- **Tests 1–13**: Core ingestion, PDF extraction, page tracking, chunk hashing, Cypher constraints, and synthetic integrity.
- **Tests 14–25**: Acronym expansion, BM25 scoring, citation section correctness, numerical reconciliation, and unknown customer handling.
- **Tests 26–33**: Scenario test cases (Apex 85L, Vikas circular cycles, generic queries, unindexed regulation handling, unsupported claim refutation, FATF Rec 20 text ranking).
- **Tests 34–51 (Requirement 9 Regression Suite)**:
  1. `test_generic_kyc_no_customer_selection`: Generic KYC query never binds a customer.
  2. `test_generic_aml_no_customer_selection`: Generic AML mule query does not bind customer.
  3. `test_explicit_valid_customer_id`: Resolves customer ID and retrieves actual graph.
  4. `test_unknown_customer_id_safe_handling`: Non-existent customer returns safe profile not found.
  5. `test_ambiguous_customer_name_clarification`: Ambiguous name prompts for clarification.
  6. `test_cross_customer_isolation_no_data_leakage`: Guarantees zero cross-customer data leakage.
  7. `test_hypothetical_scenario_never_stored_facts`: Hypothetical queries output Category C template without stored facts.
  8. `test_passthrough_drain_requires_chronological_order`: Enforces `outflow_time >= inflow_time`.
  9. `test_unrelated_accounts_no_false_passthrough`: Blocks false pass-through across unlinked accounts.
  10. `test_turnover_to_income_formula`: Verifies documented multiple calculation formula.
  11. `test_turnover_missing_or_zero_income_handled`: Safely handles zero/missing declared income.
  12. `test_cross_border_does_not_assume_high_risk_jurisdiction`: Distinguishes standard wire from designated high risk.
  13. `test_risk_signal_explainable_evidence_structure`: Asserts formula, inputs, threshold, and source presence.
  14. `test_unsupported_regulatory_claims_rejected`: Refutes invalid legal claims (e.g. branch 7-day criminal freeze).
  15. `test_missing_document_evidence_no_fabrication`: Refuses to invent unindexed laws (e.g. EU MiCA).
  16. `test_public_generic_query_zero_customer_exposure`: Public queries expose zero accounts or balances.
  17. `test_unauthorized_role_blocks_customer_investigation`: Role-based access control blocks unauthorized queries.
  18. `test_cli_commands_and_backward_compatibility`: Validates CLI parameters and function backward compatibility.

---

## 8. Known Limitations

1. **Document Knowledge Base Scope**: The indexed regulatory corpus is focused on Indian banking directions (RBI Master Directions) and FATF Standards. Non-indexed frameworks (e.g. EU MiCA, US BSA) are explicitly flagged as unindexed rather than fabricated.
2. **Synthetic Data Notice**: All customer names, account numbers, and transaction IDs are synthetic test artifacts created for engineering research and compliance evaluation.
3. **Non-Criminal Attribution**: Calculated signals and typology matches serve as internal compliance indicators for transaction monitoring and do NOT constitute legal proof of criminal guilt or adjudication of fraud.
