"""
retrieval/scenario_analyzer.py

Scenario Analysis & Parameter Extraction Engine for GraphRAG Compliance.
Extracts transaction parameters, customer profiles, jurisdictions, typologies,
requested legal provisions, and explicitly identifies missing information.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set


@dataclass
class ScenarioCalculation:
    """Deterministic, reproducible calculation of financial/compliance metrics."""
    metric_name: str
    formula: str
    input_values: Dict[str, Any]
    result: Optional[float] = None
    result_str: str = "Not calculable from available information"
    status: str = "NOT_CALCULABLE"  # "CALCULATED", "NOT_CALCULABLE"
    missing_inputs: List[str] = field(default_factory=list)
    heuristic_type: str = "INTERNAL_ANALYTICAL_HEURISTIC"  # Not a statutory legal threshold
    notes: str = ""


@dataclass
class ScenarioAnalysis:
    """Structured extraction of scenario parameters from user inquiries."""
    raw_query: str
    transaction_amount: Optional[float] = None
    amount_str: Optional[str] = None
    currency: str = "INR"
    customer_profile: Optional[str] = None
    customer_type: Optional[str] = None
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    transaction_purpose: Optional[str] = None
    jurisdiction: Optional[str] = None
    is_high_risk_jurisdiction: bool = False
    is_cross_border: bool = False
    is_circular: bool = False
    is_money_mule: bool = False
    is_pep: bool = False
    is_beneficial_ownership_query: bool = False
    risk_indicators: List[str] = field(default_factory=list)
    requested_legal_provisions: List[str] = field(default_factory=list)
    missing_information: List[str] = field(default_factory=list)
    calculations: List[ScenarioCalculation] = field(default_factory=list)
    is_generic_question: bool = False
    is_hypothetical_scenario: bool = False
    hypothetical_details: Optional[str] = None
    is_comparison: bool = False
    comparison_customer_ids: List[str] = field(default_factory=list)
    regulation_absent: bool = False
    absent_regulation_name: Optional[str] = None
    unsupported_claim_detected: bool = False
    unsupported_claim_detail: Optional[str] = None


class ScenarioAnalyzer:
    """
    Analyzes complex, situation-based compliance questions and extracts
    factual parameters, regulatory targets, and missing evidence.
    """

    KNOWN_CUSTOMERS = {
        "CUST_SYNTH_101": ("Arjun Sharma", "INDIVIDUAL", 250000.0, "Student / Freelancer"),
        "CUST_SYNTH_102": ("Priya Verma", "INDIVIDUAL", 720000.0, "Retail Executive"),
        "CUST_SYNTH_103": ("Ramesh Chandra", "INDIVIDUAL_SENIOR", 480000.0, "Retired Government Officer"),
        "CUST_SYNTH_104": ("Apex Global Consultancy", "CORPORATE_SHELL_SUSPECT", 1200000.0, "Consulting Services"),
        "CUST_SYNTH_105": ("Rajesh Gupta", "INDIVIDUAL_BUSINESS", 1500000.0, "Wholesale Trader"),
        "CUST_SYNTH_106": ("Vikas Trading Syndicate", "CORPORATE_ENTREPRENEURIAL", 5000000.0, "Commodities Intermediary"),
        "CUST_SYNTH_107": ("Sunita Enterprises", "MSME_BORROWER", 3600000.0, "Textile Manufacturing"),
    }

    # Regulatory frameworks not present in the indexed corpus
    ABSENT_FRAMEWORKS = [
        ("mica", "EU Markets in Crypto-Assets Regulation (MiCA)"),
        ("crypto-asset service providers", "EU MiCA / International CASP Regulation"),
        ("basel iv", "Basel IV Fundamental Review of the Trading Book (FRTB)"),
        ("dora", "Digital Operational Resilience Act (DORA)"),
        ("gdpr", "General Data Protection Regulation (EU GDPR)"),
        ("sec rule", "US SEC Enforcement Rules"),
    ]

    def analyze(self, query: str, context: Optional[Dict[str, Any]] = None) -> ScenarioAnalysis:
        q = str(query or "").strip()
        q_lower = q.lower()

        analysis = ScenarioAnalysis(raw_query=q)

        # 1. Parse Transaction Amount and Currency
        self._extract_amount_and_currency(q, analysis)

        # 2. Check for Absent Regulatory Frameworks
        for key, name in self.ABSENT_FRAMEWORKS:
            if key in q_lower:
                analysis.regulation_absent = True
                analysis.absent_regulation_name = name
                analysis.missing_information.append(
                    f"The requested framework '{name}' is not part of the indexed knowledge base (corpus covers RBI Master Directions on KYC, Cyber Security, Credit Information, Interest Rates, Operational Guidelines, Supervisory Credit, and FATF Recommendations)."
                )
                break

        # 3. Detect Typologies & Scenarios
        if "circular" in q_lower or "round-tripping" in q_lower or "round tripping" in q_lower or "loop" in q_lower:
            analysis.is_circular = True
            analysis.transaction_purpose = "Intra-group settlement / Circular turnover routing"
            analysis.risk_indicators.append("Circular fund flows between linked accounts (Round-tripping cycle)")

        if "mule" in q_lower or "pass-through" in q_lower or "rapid dispersal" in q_lower:
            analysis.is_money_mule = True
            analysis.transaction_purpose = "Transit account pass-through / Rapid dispersal"
            analysis.risk_indicators.append("Pass-through rapid dispersal pattern (Money Mule)")

        if "high-risk jurisdiction" in q_lower or "high risk jurisdiction" in q_lower or "overseas" in q_lower or "cross-border" in q_lower or "remittance" in q_lower:
            analysis.is_cross_border = True
            if "high-risk" in q_lower or "high risk" in q_lower or "shell" in q_lower:
                analysis.is_high_risk_jurisdiction = True
                analysis.jurisdiction = "High-Risk Overseas Jurisdiction"
                analysis.risk_indicators.append("High-value remittance from high-risk jurisdiction")
            else:
                analysis.jurisdiction = "Cross-Border / Overseas"

        if "beneficial owner" in q_lower or "beneficial ownership" in q_lower or "bo" in q_lower:
            analysis.is_beneficial_ownership_query = True
            analysis.risk_indicators.append("Beneficial ownership identification and verification gap")

        if "pep" in q_lower or "politically exposed" in q_lower:
            analysis.is_pep = True
            analysis.risk_indicators.append("Politically Exposed Person (PEP) involvement")

        # 4. Detect Specific Requested Legal Provisions
        if "paragraph 44" in q_lower or "para 44" in q_lower or "non-face-to-face" in q_lower:
            analysis.requested_legal_provisions.append("RBI KYC Master Direction, Paragraph 44 (Enhanced Due Diligence for Non-Face-to-Face Onboarding)")
        if "paragraph 45" in q_lower or "para 45" in q_lower or "politically exposed" in q_lower or "pep" in q_lower:
            analysis.requested_legal_provisions.append("RBI KYC Master Direction, Paragraph 45 (Accounts of Politically Exposed Persons - PEPs)")
        if "paragraph 39" in q_lower or "section 39" in q_lower or "ongoing due diligence" in q_lower or "ongoing monitoring" in q_lower:
            analysis.requested_legal_provisions.append("RBI KYC Master Direction, Section 39 (Ongoing Due Diligence & Monitoring)")
        if "paragraph 40" in q_lower or "section 40" in q_lower or "unusual pattern" in q_lower or "complex" in q_lower:
            analysis.requested_legal_provisions.append("RBI KYC Master Direction, Section 40 (Complex & Unusually Large Transactions)")
        if "paragraph 50" in q_lower or "section 50" in q_lower or "record management" in q_lower or "record retention" in q_lower:
            analysis.requested_legal_provisions.append("RBI KYC Master Direction, Section 50 (Record Management)")
        if "section 68" in q_lower or "sec 68" in q_lower:
            analysis.requested_legal_provisions.append("RBI KYC Master Direction, Section 68 (Operation of Bank Accounts and Money Mules)")
        if "section 35" in q_lower or "sec 35" in q_lower:
            analysis.requested_legal_provisions.append("RBI KYC Master Direction, Section 35 (Politically Exposed Persons - PEPs)")
        if "section 33" in q_lower or "sec 33" in q_lower:
            analysis.requested_legal_provisions.append("RBI KYC Master Direction, Section 33 (Beneficial Ownership Identification)")
        if "section 37" in q_lower or "section 38" in q_lower:
            analysis.requested_legal_provisions.append("RBI KYC Master Direction, Section 37/38 (Enhanced Due Diligence & Periodic Updation)")
        if "section 74" in q_lower or "wire transfer" in q_lower:
            analysis.requested_legal_provisions.append("RBI KYC Master Direction, Section 74 (Wire Transfer & High-Risk Cross-Border Transfers)")
        if "recommendation 19" in q_lower or "rec 19" in q_lower:
            analysis.requested_legal_provisions.append("FATF Recommendation 19 (Higher-risk countries & countermeasures)")
        if "recommendation 12" in q_lower or "rec 12" in q_lower:
            analysis.requested_legal_provisions.append("FATF Recommendation 12 (Politically Exposed Persons)")
        if "recommendation 10" in q_lower or "rec 10" in q_lower:
            analysis.requested_legal_provisions.append("FATF Recommendation 10 (Customer Due Diligence)")
        if "recommendation 20" in q_lower or "rec 20" in q_lower:
            analysis.requested_legal_provisions.append("FATF Recommendation 20 (Reporting of Suspicious Transactions)")
        if "pmla section 12" in q_lower or "section 12" in q_lower and "pmla" in q_lower:
            analysis.requested_legal_provisions.append("PMLA Section 12 (Reporting entity to maintain records)")
            analysis.missing_information.append("Primary legislative text of PMLA Section 12 is missing from local corpus (statutory mandates operationalized via RBI KYC Master Direction Section 3(a)(xviii), Section 50, and Section 74).")
        elif "pmla" in q_lower or "pml rules" in q_lower:
            analysis.requested_legal_provisions.append("PMLA, 2002 & PML (Maintenance of Records) Rules, 2005 (Rule 2(1)(g): Suspicious Transactions, Rule 9: Client Due Diligence)")

        # 5. Check for Unsupported Legal Claims in Query
        # e.g., query claiming Section 68 mandates a 7-day criminal freeze by branch manager
        if "criminal freeze" in q_lower or "criminal freezing order" in q_lower or "mandatory 7-day freeze" in q_lower:
            analysis.unsupported_claim_detected = True
            analysis.unsupported_claim_detail = (
                "The query asks whether RBI KYC Section 68 mandates a '7-day criminal freezing order by branch managers'. "
                "Official Section 68 text directs banks to monitor accounts meticulously and report suspicious transactions to FIU-IND. "
                "It does NOT grant branch managers statutory criminal asset-freezing powers; criminal freezing requires judicial or statutory agency orders under PMLA Section 17/UAPA Section 51A."
            )

        # 6. Cross-Customer Comparison Detection (Category D)
        all_cids_in_query = list(dict.fromkeys(re.findall(r"\b(CUST_SYNTH_\d{3})\b", q, re.I)))
        all_cids_in_query = [c.upper() for c in all_cids_in_query if c.upper() in self.KNOWN_CUSTOMERS]
        if len(all_cids_in_query) >= 2 or ("compare" in q_lower and len(all_cids_in_query) >= 2):
            analysis.is_comparison = True
            analysis.comparison_customer_ids = all_cids_in_query

        if not analysis.is_comparison:
            matched_names = []
            for cid, (name, ctype, inc, occ) in self.KNOWN_CUSTOMERS.items():
                name_clean = re.sub(r"\s*\(fictional.*?\)", "", name, flags=re.I).strip().lower()
                if name_clean in q_lower:
                    matched_names.append(cid)
            if len(matched_names) >= 2 and ("compare" in q_lower or "versus" in q_lower or " vs " in q_lower or " and " in q_lower):
                analysis.is_comparison = True
                analysis.comparison_customer_ids = list(dict.fromkeys(matched_names))

        # 7. Customer Resolution & Profile Mapping (Category B)
        # STRICT RULE: Never select a customer merely based on generic keywords like mule, circular, cross-border.
        # Only resolve if:
        # a) Graph context explicitly supplies customer record.
        # b) Context explicitly provides a customer_id.
        # c) Query explicitly mentions a specific customer ID (CUST_SYNTH_XXX) or full customer name.
        explicit_cid = (context or {}).get("customer_id")
        graph = (context or {}).get("graph_context") or {}
        cust = graph.get("customer") or {}

        if cust and cust.get("customer_id"):
            analysis.customer_id = cust.get("customer_id")
            analysis.customer_name = cust.get("full_name")
            analysis.customer_type = cust.get("customer_type")
            analysis.customer_profile = f"Customer {analysis.customer_name} ({cust.get('customer_type', 'INDIVIDUAL')}), Declared Annual Income: INR {float(cust.get('declared_annual_income') or cust.get('declared_annual_income_inr') or 0):,.2f}, KYC Status: {cust.get('kyc_status', 'UNKNOWN')}"
        elif explicit_cid and explicit_cid in self.KNOWN_CUSTOMERS:
            name, ctype, inc, occ = self.KNOWN_CUSTOMERS[explicit_cid]
            analysis.customer_id = explicit_cid
            analysis.customer_name = name
            analysis.customer_type = ctype
            analysis.customer_profile = f"{name} ({ctype}), Declared Annual Income: INR {inc:,.2f}, Occupation: {occ}"
        elif not analysis.is_comparison:
            # Check for explicit customer ID in query
            cid_match = re.search(r"\b(CUST_SYNTH_\d{3})\b", q, re.I)
            if cid_match:
                cid = cid_match.group(1).upper()
                if cid in self.KNOWN_CUSTOMERS:
                    name, ctype, inc, occ = self.KNOWN_CUSTOMERS[cid]
                    analysis.customer_id = cid
                    analysis.customer_name = name
                    analysis.customer_type = ctype
                    analysis.customer_profile = f"{name} ({ctype}), Declared Annual Income: INR {inc:,.2f}, Occupation: {occ}"
            else:
                # Check for explicit customer full names
                for cid, (name, ctype, inc, occ) in self.KNOWN_CUSTOMERS.items():
                    name_clean = re.sub(r"\s*\(fictional.*?\)", "", name, flags=re.I).strip().lower()
                    if name_clean and name_clean in q_lower:
                        analysis.customer_id = cid
                        analysis.customer_name = name
                        analysis.customer_type = ctype
                        analysis.customer_profile = f"{name} ({ctype}), Declared Annual Income: INR {inc:,.2f}, Occupation: {occ}"
                        break

        # 8. Check for Hypothetical Scenarios (Category C) vs Generic Questions (Category A)
        # Hypothetical inquiries describe scenario actions without identifying a verified database subject.
        hypothetical_patterns = [
            r"\ba\s+customer\s+(?:sends|transfers|receives|has|deposits|withdraws|opens)\b",
            r"\ba\s+dormant\s+account\b",
            r"\ban\s+account\s+(?:is|has|receives|transfers)\b",
            r"\bsuppose\b",
            r"\bhypothetical\b",
            r"\bif\s+(?:a|an)\s+(?:customer|account|company|individual)\b",
            r"\bwhat\s+if\b",
            r"\bwhat\s+evidence\s+should\s+an\s+investigator\b",
            r"\bwhat\s+risk\s+indicators\s+might\s+be\s+relevant\b",
        ]
        is_hypo = any(re.search(pat, q_lower) for pat in hypothetical_patterns)
        if is_hypo and not analysis.customer_id and not analysis.is_comparison:
            analysis.is_hypothetical_scenario = True
            analysis.is_generic_question = False
            analysis.hypothetical_details = (
                "Hypothetical compliance inquiry describing scenario conditions without identifying a verified database customer."
            )
        elif not analysis.customer_id and not analysis.is_comparison:
            # General regulatory or educational inquiry
            analysis.is_generic_question = True

        # 9. Perform Deterministic Calculations
        self._perform_deterministic_calculations(analysis, context)

        # 10. Identify Missing Information
        self._detect_missing_information(analysis)

        return analysis

    def _perform_deterministic_calculations(self, analysis: ScenarioAnalysis, context: Optional[Dict[str, Any]] = None):
        """
        Perform reproducible, deterministic calculations for compliance metrics.
        Adheres to Phase 2 guidelines:
        - Calculations performed strictly by deterministic Python code.
        - Every metric exposes: formula, input values, provenance, result, missing inputs.
        - Never allow LLM or heuristics to manufacture missing numeric inputs.
        """
        # 1. Turnover-to-Income Multiple
        graph = (context or {}).get("graph_context") or {}
        cust = graph.get("customer") or {}
        declared_income = None
        income_source = None
        if cust and (cust.get("declared_annual_income") or cust.get("declared_annual_income_inr")):
            declared_income = float(cust.get("declared_annual_income") or cust.get("declared_annual_income_inr"))
            income_source = f"Verified customer record in knowledge graph ({analysis.customer_id})"
        elif analysis.customer_id and analysis.customer_id in self.KNOWN_CUSTOMERS:
            declared_income = float(self.KNOWN_CUSTOMERS[analysis.customer_id][2])
            income_source = f"Known test customer profile ({analysis.customer_id})"

        income_calc = ScenarioCalculation(
            metric_name="Turnover-to-Income Multiple",
            formula="Transaction Inflow Amount / Declared Annual Income",
            input_values={
                "transaction_amount": analysis.transaction_amount,
                "declared_annual_income": declared_income,
                "provenance": income_source or "None (not provided in inquiry or database)"
            },
            heuristic_type="INTERNAL_ANALYTICAL_HEURISTIC"
        )
        if analysis.transaction_amount is not None and declared_income is not None and declared_income > 0:
            multiple = round(analysis.transaction_amount / declared_income, 2)
            income_calc.result = multiple
            income_calc.result_str = f"{multiple:.2f}x declared annual income"
            income_calc.status = "CALCULATED"
            income_calc.notes = f"Calculated as INR {analysis.transaction_amount:,.2f} / INR {declared_income:,.2f} = {multiple:.2f}x (Internal analytical heuristic, not a statutory ratio)."
        else:
            income_calc.status = "NOT_CALCULABLE"
            missing = []
            if analysis.transaction_amount is None:
                missing.append("transaction_amount")
            if declared_income is None:
                missing.append("declared_annual_income")
            income_calc.missing_inputs = missing
            income_calc.result_str = "Not calculable from available information (declared annual income is not provided)"
            income_calc.notes = "Annual income was not provided in the scenario prompt or database; no income multiple can be manufactured."
        analysis.calculations.append(income_calc)

        # 2. Fund Drain Ratio (Outflow vs Inflow)
        drain_calc = ScenarioCalculation(
            metric_name="Pass-Through Fund Drain Ratio",
            formula="(Aggregate Outflows within Time Window / Inflow Amount) * 100%",
            input_values={
                "inflow_amount": analysis.transaction_amount,
                "outflow_amount": None,
                "time_window_minutes": 30 if "30 minutes" in analysis.raw_query.lower() else None
            },
            heuristic_type="INTERNAL_ANALYTICAL_HEURISTIC"
        )
        drain_calc.status = "NOT_CALCULABLE"
        drain_calc.missing_inputs = ["precise_outflow_amount"]
        drain_calc.result_str = "Not calculable (exact domestic transfer amounts not quantified in input)"
        drain_calc.notes = "Prompt describes outbound transfer of 'most of the amount' within 30 minutes. While this indicates rapid dispersal velocity, the exact drain percentage cannot be computed without verified outbound ledger values."
        analysis.calculations.append(drain_calc)

    def _extract_amount_and_currency(self, query: str, analysis: ScenarioAnalysis):
        """Parse currency and numerical amounts including Indian numbering."""
        q = query

        # Currency detection
        if re.search(r"\b(?:usd|\$|dollars?)\b", q, re.I):
            analysis.currency = "USD"
        elif re.search(r"\b(?:eur|€|euros?)\b", q, re.I):
            analysis.currency = "EUR"
        else:
            analysis.currency = "INR"

        # Match Indian numbering like "INR 85,00,000", "85,00,000", "₹85,00,000", "85 lakh", "85 lakhs"
        lakh_match = re.search(r"(?:inr|rs\.?|₹)?\s*(\d+(?:\.\d+)?)\s*(?:lakhs?|lac|lacs)\b", q, re.I)
        if lakh_match:
            val = float(lakh_match.group(1)) * 100000.0
            analysis.transaction_amount = val
            analysis.amount_str = f"INR {val:,.2f}"
            return

        crore_match = re.search(r"(?:inr|rs\.?|₹)?\s*(\d+(?:\.\d+)?)\s*(?:crores?|cr)\b", q, re.I)
        if crore_match:
            val = float(crore_match.group(1)) * 10000000.0
            analysis.transaction_amount = val
            analysis.amount_str = f"INR {val:,.2f}"
            return

        # Match formatted numbers: "85,00,000" or "8,500,000" or "196600"
        num_match = re.search(r"(?:inr|rs\.?|₹)?\s*(\d{1,3}(?:,\d{2,3})*(?:\.\d{1,2})?|\d{5,12}(?:\.\d{1,2})?)\b", q, re.I)
        if num_match:
            raw_num = num_match.group(1).replace(",", "")
            try:
                val = float(raw_num)
                if val >= 1000.0:  # Exclude years like 2026 or section numbers like 68
                    analysis.transaction_amount = val
                    analysis.amount_str = f"INR {val:,.2f}"
            except ValueError:
                pass

    def _detect_missing_information(self, analysis: ScenarioAnalysis):
        """Identify critical missing data gaps required for a conclusive compliance decision."""
        if analysis.is_generic_question:
            analysis.missing_information.append(
                "Specific customer profile, transaction timeline, and account context (this is a general regulatory interpretation inquiry)."
            )
            return

        # Check for income multiple availability
        income_calc = next((c for c in analysis.calculations if c.metric_name == "Turnover-to-Income Multiple"), None)
        if income_calc and income_calc.status == "NOT_CALCULABLE":
            analysis.missing_information.append(
                "Customer declared annual income, historical financial profile, and typical business turnover baseline (an income-to-turnover multiple cannot be calculated from available information)."
            )

        if analysis.is_cross_border or (analysis.transaction_amount and analysis.transaction_amount >= 5000000.0):
            analysis.missing_information.extend([
                "Underlying commercial documentation, contracts, or invoices establishing the bona fide commercial rationale for the overseas remittance.",
                "Source-of-funds verification documentation establishing the origin and legality of the transferred funds.",
                "Identity, nature of business, and commercial relationship with the domestic beneficiary accounts.",
                "Country of origin and regulatory risk classification for the overseas originating account.",
            ])

        if analysis.is_circular:
            analysis.missing_information.extend([
                "Documented bona fide economic rationale for round-trip transfers across affiliated current accounts.",
                "Proof of underlying commercial transactions (invoices, goods delivery challans) corresponding to each circular hop.",
                "Complete corporate ownership register establishing whether the participating accounts share common beneficial ownership."
            ])

        if analysis.is_money_mule:
            analysis.missing_information.extend([
                "IP connection logs and device telemetry to verify whether online banking credentials were compromised via phishing or malware.",
                "Inter-bank counterparty verification for the recipient account(s).",
                "Customer response to formal source-of-funds verification inquiry regarding third-party deposits."
            ])
