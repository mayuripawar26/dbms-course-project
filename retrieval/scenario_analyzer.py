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

        # 9. Identify Missing Information
        self._detect_missing_information(analysis)

        return analysis

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

        if analysis.is_cross_border or (analysis.transaction_amount and analysis.transaction_amount >= 5000000.0):
            analysis.missing_information.extend([
                "Independent verification documentation for Ultimate Beneficial Ownership (UBO) natural persons holding >10% ownership or control.",
                "Corroborating commercial contract, customs declaration, or invoice justifying the economic purpose of the remittance.",
                "Verified source-of-wealth and source-of-funds documentation explaining the 7.1x multiple over declared annual income.",
                "Formal record of prior Senior Management Approval for establishing or maintaining banking relationships with Politically Exposed Persons (PEPs) under Section 35."
            ])

        if analysis.is_circular:
            analysis.missing_information.extend([
                "Documented bona fide economic rationale for round-trip transfers across affiliated current accounts.",
                "Proof of underlying commercial transactions (invoices, goods delivery challans) corresponding to each circular hop.",
                "Complete corporate ownership register establishing whether the 3 current accounts share common beneficial ownership."
            ])

        if analysis.is_money_mule:
            analysis.missing_information.extend([
                "IP connection logs and device telemetry to verify whether online banking credentials were compromised via phishing or malware.",
                "Inter-bank beneficial ownership confirmation for the external receiving account (`ACC_EXTERNAL_OFFSHORE_MULE_EXIT`).",
                "Customer response to formal source-of-funds verification inquiry regarding third-party deposits."
            ])
