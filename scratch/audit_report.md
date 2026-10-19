# GraphRAG Banking Compliance & Risk Intelligence System
## Phase 1 Source Code Audit & Defect Report

**Date:** 2026-10-19  
**Auditor:** Senior Banking Compliance Systems Engineer & Python Specialist  
**Workspace:** `C:\Users\Shreeya B. Kulkarni\Desktop\DBms_project`

---

### 1. Confirmed Defects

#### Defect 1: Implicit / Hardcoded Customer Binding in Generic Query Path
- **Files & Line Numbers:**
  - `retrieval/scenario_analyzer.py`, Lines 161–190
  - `retrieval/graph_retriever.py`, Lines 760–763, 803–804
- **Description:** 
  In `retrieval/scenario_analyzer.py`, lines 162–190 automatically bind customer IDs when query keywords match typologies:
  - If query mentions `mule`, `pass-through`, or `rapid dispersal`, it sets `customer_id = "CUST_SYNTH_101"` (Arjun Sharma).
  - If query mentions `circular`, `round-tripping`, or `linked current accounts`, it sets `customer_id = "CUST_SYNTH_106"` (Vikas Trading Syndicate).
  - If query mentions `cross-border` with `declared profile` or amount `8500000`, it sets `customer_id = "CUST_SYNTH_104"` (Apex Global Consultancy).
  In `retrieval/graph_retriever.py`, lines 760–763 and 803–804 adopt `pre_analysis.customer_id` into `target_cust_id` for compliance officer queries.
- **Impact:** Generic inquiries (e.g. "What is a money mule under RBI rules?") or hypothetical questions asked by an officer cause private synthetic customer profiles, account numbers, and transactions to be attached to the report.
- **Remediation:** Remove implicit customer keyword mapping from `scenario_analyzer.py`. Only resolve a customer if explicitly passed via parameter, exact customer ID, or unambiguous name.

---

#### Defect 2: Temporal Inversion & Absolute Time Delta in Pass-Through Drain
- **File & Line Numbers:** `retrieval/risk_analyzer.py`, Lines 183–204 (specifically Line 196)
- **Description:**
  ```python
  delta_seconds = abs((min_out - max_in).total_seconds())
  ```
  Uses `abs()` and computes the difference between `max(inflow_times)` and `min(outflow_times)`. If an outflow occurred hours *before* the inflow arrived, `abs()` produces a positive value and flags it as a "rapid drain within X minutes".
- **Impact:** Chronological causality is broken: money departing an account before incoming funds arrive is falsely treated as pass-through forwarding. Furthermore, inflows and outflows across unrelated accounts owned by the same customer are pooled without account linkage verification.
- **Remediation:** Enforce chronological order (`outflow_time >= inflow_time`) on the same account (or verified intra-account linkage) within the configurable time window. Disallow `abs()`.

---

#### Defect 3: Silent Suppression of Zero / Missing Declared Income in Turnover Rule
- **File & Line Numbers:** `retrieval/risk_analyzer.py`, Lines 306–308
- **Description:**
  ```python
  declared = float(customer.get("declared_annual_income", ...) or 0.0)
  if declared <= 0:
      return None
  ```
- **Impact:** If a customer's declared income is zero or unrecorded, the turnover rule silently returns `None` (zero risk), even if millions in turnover flow through the account.
- **Remediation:** Explicitly handle zero or missing income. When incoming external turnover is significant (> threshold) and declared income is missing or zero, flag an unverified profile risk signal (`IND_TURNOVER_UNVERIFIED_INCOME`) instead of silently ignoring it.

---

#### Defect 4: Conflating All Cross-Border Transfers with "High-Risk Jurisdiction"
- **File & Line Numbers:** `retrieval/risk_analyzer.py`, Lines 388–418
- **Description:**
  `_check_cross_border_risks` triggers `IND_CROSS_BORDER_HIGH_RISK_INFLOW` simply if `SWIFT`, `OVERSEAS`, or `CROSS_BORDER` appears in transaction properties, labeling every international transfer as "from High-Risk Jurisdiction".
- **Impact:** Standard legitimate international wire transfers are misclassified as high-risk jurisdiction activity without referencing a dated, configurable list of high-risk jurisdictions.
- **Remediation:** Separate general cross-border wire activity (`IND_CROSS_BORDER_TRANSFER`) from designated high-risk jurisdiction transactions (`IND_HIGH_RISK_JURISDICTION_TRANSFER`). Reference a dated, configurable FATF jurisdiction list and report when jurisdiction classification cannot be verified from available counterparty metadata.

---

#### Defect 5: Missing Dormant Account Reactivation Rule
- **File & Line Numbers:** `retrieval/risk_analyzer.py`
- **Description:** No rule evaluates account status `DORMANT` or `INACTIVE` followed by sudden transaction activity.
- **Impact:** Fails to cover a primary banking risk pattern (dormant account takeover and sudden re-activation for mule forwarding) required by Section 4.D.
- **Remediation:** Implement `_check_dormant_account_reactivation` checking for active transactions on accounts marked dormant or inactive.

---

#### Defect 6: Missing Customer Comparison Support (Category D)
- **File & Line Numbers:** `retrieval/query_router.py`, Lines 396–404; `retrieval/graph_retriever.py`, Line 741
- **Description:** `_extract_customer_id` extracts only a single customer ID via `re.search`. `execute_unified_query` only accepts a single target customer ID.
- **Impact:** Cross-customer comparative compliance inquiries (e.g., comparing `CUST_SYNTH_101` and `CUST_SYNTH_104`) cannot isolate and compare two customer profiles.
- **Remediation:** Add multi-customer extraction, dual graph retrieval, and a dedicated comparative report generator (`_generate_customer_comparison_answer`).

---

#### Defect 7: Hypothetical Scenarios Presenting Assumptions as Stored Database Facts (Category C)
- **File & Line Numbers:** `retrieval/answer_generator.py`, Lines 60, 244–277
- **Description:** If an inquiry describes a hypothetical situation without a specific customer, the pipeline either falls back to a generic public advisory or binds an arbitrary customer and formats a report with `Verified Facts from Knowledge Graph`.
- **Impact:** Hypothetical assumptions are conflated with verified database facts.
- **Remediation:** Introduce `_generate_hypothetical_scenario_answer` (Category C) clearly marking assumptions as hypothetical, laying out regulatory requirements, risk formulas, and missing parameters.

---

#### Defect 8: Unknown Customer ID Produces Degraded / Malformed Report
- **File & Line Numbers:** `retrieval/answer_generator.py`, Lines 60, 191–196
- **Description:** When an unknown customer ID (e.g. `CUST_SYNTH_999`) is passed, `trace_customer_risk_graph` returns an error dictionary, but `answer_generator` proceeds to render an investigation report for `"Not specified (ID: Not specified)"`.
- **Impact:** Misleading output when a customer lookup fails.
- **Remediation:** Check for graph lookup errors and return a clear, safe response.

---

#### Defect 9: Missing `.gitignore` Exposing Environment Secrets
- **File:** Root directory
- **Description:** No `.gitignore` file existed, putting `.env`, logs, and python caches at risk of being committed.
- **Remediation:** Added `.gitignore` covering `.env`, caches, logs, and virtual environments.

---

### 2. Existing Functionality That Works Correctly

1. **BM25 Document Retrieval & Citation Metadata:**
   - 1,237 chunks indexed across 10 official banking PDFs.
   - Preserves page numbers, section headings, authority levels, and raw text excerpts.
   - Successfully prioritizes RBI KYC Section 68 for money mules and FATF Recommendation 20 / PML Rules Section 3(a)(xviii) for circular fund flows.
2. **Neo4j Subgraph & Closed-Cycle Discovery:**
   - Live Neo4j connection (`bolt://3.237.200.126:7687`) and Cypher queries function properly.
   - Detects 3-hop closed cycle for Vikas Trading Syndicate (`CUST_SYNTH_106`).
   - Reconciles cumulative ledger turnover (₹14,85,000.00), net balance change (₹0.00), and commercial variance (₹14,85,000.00).
3. **Role-Based Access Control Boundaries:**
   - Public sessions cannot query private customer accounts.
   - Customers cannot query other customers' profiles (tenant isolation enforced).
   - Compliance officers can query explicitly authorized profiles.
4. **Acronym Expansion & Heuristic BM25 Scoring:**
   - Expands terms (`pep`, `aml`, `kyc`, `edd`, `str`, `pmla`, `circular`).
   - BM25 score explicitly identified as a heuristic retrieval metric, not a probability.
5. **Deterministic GraphRAG Architecture:**
   - Operates completely without an LLM dependency.
   - Generates grounded, structured 8-section investigation reports.

---

### 3. Proposed Fixes & Implementation Plan

1. **Phase 2 — Critical Fixes:**
   - Update `retrieval/scenario_analyzer.py`: Eliminate implicit customer binding; add `is_hypothetical_scenario` detection.
   - Update `retrieval/query_router.py`: Support multiple customer IDs and intents for hypothetical scenarios and comparisons.
   - Update `retrieval/risk_analyzer.py`:
     - Fix pass-through drain with strict chronological pairs on linked accounts.
     - Fix turnover-to-income ratio to handle zero/missing income explicitly.
     - Distinguish general cross-border from designated high-risk jurisdictions using a dated, configurable FATF list.
     - Implement dormant account reactivation detection.
     - Structure all risk signals with formula, threshold, threshold source, and exact transaction IDs.
   - Update `retrieval/graph_retriever.py`:
     - Disallow implicit customer selection; enforce explicit customer resolution or safe unknown customer error.
     - Handle Category C (hypothetical scenarios) and Category D (cross-customer comparisons).
2. **Phase 3 — Evidence Quality & Answer Generation:**
   - Update `retrieval/answer_generator.py`:
     - Add `_generate_hypothetical_scenario_answer` (Category C).
     - Add `_generate_customer_comparison_answer` (Category D).
     - Ensure unknown customer ID produces a clean, safe notification.
     - Ensure explainable risk calculations appear in the investigation report.
3. **Phase 4 — Comprehensive Regression Tests:**
   - Add tests covering all 18 cases specified in User Requirement 9.
4. **Phase 5 & 6 — Verification & Documentation:**
   - Run full unit test suite.
   - Execute CLI demonstrations for all categories.
   - Update `README.md`.
