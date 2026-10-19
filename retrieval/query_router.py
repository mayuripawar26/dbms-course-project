"""
retrieval/query_router.py

Shared Natural-Language Query Router & Access Control Layer
Classifies incoming banking queries into 5 standard intents:
- GENERAL_KNOWLEDGE: Public educational banking, fraud awareness, definitions.
- CUSTOMER_INFORMATION: Authenticated customer balance, transactions, profile.
- RISK_INVESTIGATION: Suspicious activity, flagged transactions, risk signals.
- REGULATORY_QUERY: Official RBI / FATF statutory directions and rules.
- MIXED_QUERY: Combined public knowledge + personal customer investigation.

Enforces server-side tenant isolation:
- Public users cannot access private customer graphs.
- Customers can only query their own verified session data.
- Compliance officers can investigate explicitly authorized customer profiles.
"""

import re
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set, Tuple


class QueryIntent(str, Enum):
    GENERAL_KNOWLEDGE = "GENERAL_KNOWLEDGE"
    CUSTOMER_INFORMATION = "CUSTOMER_INFORMATION"
    RISK_INVESTIGATION = "RISK_INVESTIGATION"
    REGULATORY_QUERY = "REGULATORY_QUERY"
    MIXED_QUERY = "MIXED_QUERY"
    HYPOTHETICAL_SCENARIO = "HYPOTHETICAL_SCENARIO"
    CROSS_CUSTOMER_COMPARISON = "CROSS_CUSTOMER_COMPARISON"


class UserRole(str, Enum):
    PUBLIC = "PUBLIC"
    CUSTOMER = "CUSTOMER"
    COMPLIANCE_OFFICER = "COMPLIANCE_OFFICER"
    OFFICER = "COMPLIANCE_OFFICER"


@dataclass
class UserSession:
    """Represents a validated server-side user session."""
    role: UserRole = UserRole.PUBLIC
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    username: Optional[str] = None
    department: Optional[str] = None
    is_authenticated: bool = False

    @classmethod
    def public_session(cls) -> "UserSession":
        return cls(role=UserRole.PUBLIC, is_authenticated=False)

    @classmethod
    def customer_session(cls, customer_id: str, customer_name: Optional[str] = None) -> "UserSession":
        return cls(
            role=UserRole.CUSTOMER,
            customer_id=customer_id,
            customer_name=customer_name,
            username=customer_name or customer_id,
            is_authenticated=True
        )

    @classmethod
    def officer_session(cls, officer_id: str = "OFF_01", department: str = "Compliance", username: str = "Compliance Officer") -> "UserSession":
        return cls(
            role=UserRole.COMPLIANCE_OFFICER,
            username=username or officer_id,
            department=department,
            is_authenticated=True
        )


@dataclass
class RoutingDecision:
    """Detailed decision produced by the query router."""
    intent: QueryIntent
    original_query: str
    target_customer_id: Optional[str] = None
    requires_auth: bool = False
    access_granted: bool = True
    denial_reason: Optional[str] = None
    needs_clarification: bool = False
    clarification_message: Optional[str] = None
    public_subquery: Optional[str] = None
    private_subquery: Optional[str] = None
    comparison_customer_ids: List[str] = field(default_factory=list)
    search_keywords: List[str] = field(default_factory=list)


class QueryRouter:
    """
    Intelligent Query Router that parses user intent and guarantees
    role-based authorization before dispatching to retrieval engines.
    """

    # Patterns indicating first-person customer inquiries
    CUSTOMER_PRONOUNS = {
        "my", "mine", "me", "i", "myself", "our"
    }

    # Terms indicating personal account / balance queries
    ACCOUNT_INFO_KEYWORDS = {
        "balance", "statement", "transactions", "transaction history",
        "recent transactions", "account number", "account activity",
        "savings account", "current account", "my kyc", "kyc status",
        "kyc details", "my deposits", "my money", "debit", "credit"
    }

    # Terms indicating risk / fraud inquiry on an account
    RISK_INVESTIGATION_KEYWORDS = {
        "flagged", "suspicious", "mule", "risk indicator", "risk rating",
        "frozen", "restricted", "blocked", "fraud pattern", "investigate",
        "trace", "unauthorized", "stolen", "unusual", "drain ratio",
        "round-tripping", "structuring", "velocity", "anomaly"
    }

    # Terms indicating regulatory / legal inquiry
    REGULATORY_KEYWORDS = {
        "rbi", "fatf", "section", "master direction", "pmla", "fiu",
        "fiu-ind", "statutory", "mandate", "guideline", "circular",
        "provision", "recommendation", "compliance obligation"
    }

    # General public educational indicators
    GENERAL_EDUCATIONAL_PATTERNS = [
        r"^what\s+(is|are)\b",
        r"^how\s+(does|do|can)\b",
        r"^define\b",
        r"^explain\b",
        r"^what\s+should\s+(someone|a\s+person|one|i)\s+do\b",
        r"^what\s+are\s+the\s+differences?\b",
        r"^what\s+precautions?\b",
        r"^tips\s+for\b",
        r"^how\s+to\s+prevent\b"
    ]

    def __init__(self, known_customer_ids: Optional[Set[str]] = None):
        self.known_customer_ids = known_customer_ids or set()

    def route(
        self,
        query: str,
        session: Optional[UserSession] = None,
        explicit_customer_id: Optional[str] = None
    ) -> RoutingDecision:
        """
        Evaluate user inquiry, determine intent, and enforce security boundaries.
        """
        clean_q = str(query or "").strip()
        user_sess = session or UserSession.public_session()

        if not clean_q:
            return RoutingDecision(
                intent=QueryIntent.GENERAL_KNOWLEDGE,
                original_query="",
                needs_clarification=True,
                clarification_message="Please enter a question or compliance inquiry to begin."
            )

        q_lower = clean_q.lower()
        words = set(re.findall(r"\b[a-z0-9_-]+\b", q_lower))

        # Check for cross-customer ID injection in query text
        detected_cid = self._extract_customer_id(clean_q)
        all_cids = self._extract_all_customer_ids(clean_q)

        # --- 0A. CROSS-CUSTOMER COMPARISON ENFORCEMENT (Category D) ---
        if len(all_cids) >= 2 or ("compare" in q_lower and len(all_cids) >= 2):
            if user_sess.role == UserRole.CUSTOMER:
                return RoutingDecision(
                    intent=QueryIntent.CROSS_CUSTOMER_COMPARISON,
                    original_query=clean_q,
                    target_customer_id=user_sess.customer_id,
                    access_granted=False,
                    denial_reason=f"Tenant boundary violation: Authenticated customer {user_sess.customer_id} is not authorized to compare external customer profiles {', '.join(all_cids)}."
                )
            elif user_sess.role == UserRole.PUBLIC:
                return RoutingDecision(
                    intent=QueryIntent.CROSS_CUSTOMER_COMPARISON,
                    original_query=clean_q,
                    requires_auth=True,
                    access_granted=False,
                    denial_reason=f"Cross-customer profile comparisons ({', '.join(all_cids)}) require compliance officer authentication. Please log in as a compliance officer."
                )
            else:  # COMPLIANCE_OFFICER
                return RoutingDecision(
                    intent=QueryIntent.CROSS_CUSTOMER_COMPARISON,
                    original_query=clean_q,
                    target_customer_id=all_cids[0],
                    comparison_customer_ids=all_cids,
                    access_granted=True
                )

        # --- 0B. CROSS-TENANT ISOLATION AND ACCESS BOUNDARY ENFORCEMENT ---
        if user_sess.role == UserRole.CUSTOMER:
            if detected_cid and detected_cid != user_sess.customer_id:
                return RoutingDecision(
                    intent=QueryIntent.CUSTOMER_INFORMATION,
                    original_query=clean_q,
                    target_customer_id=user_sess.customer_id,
                    access_granted=False,
                    denial_reason=f"Tenant boundary violation: Authenticated customer {user_sess.customer_id} is not authorized to query or inspect records for customer {detected_cid}."
                )
            if explicit_customer_id and explicit_customer_id != user_sess.customer_id:
                return RoutingDecision(
                    intent=QueryIntent.CUSTOMER_INFORMATION,
                    original_query=clean_q,
                    target_customer_id=user_sess.customer_id,
                    access_granted=False,
                    denial_reason=f"Tenant boundary violation: Authenticated customer {user_sess.customer_id} is not authorized to query or inspect records for customer {explicit_customer_id}."
                )

        if user_sess.role == UserRole.PUBLIC and detected_cid:
            return RoutingDecision(
                intent=QueryIntent.CUSTOMER_INFORMATION,
                original_query=clean_q,
                target_customer_id=detected_cid,
                requires_auth=True,
                access_granted=False,
                denial_reason=f"Private customer records for {detected_cid} cannot be accessed publicly without authentication. Please sign in to view records."
            )

        # --- 0C. HYPOTHETICAL SCENARIO DETECTION (Category C) ---
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
        if is_hypo and not detected_cid and not explicit_customer_id:
            return RoutingDecision(
                intent=QueryIntent.HYPOTHETICAL_SCENARIO,
                original_query=clean_q,
                access_granted=True
            )

        # Check for first-person ownership signals
        has_first_person = bool(words & self.CUSTOMER_PRONOUNS)

        # Check for account info keywords
        has_account_info = any(k in q_lower for k in self.ACCOUNT_INFO_KEYWORDS)

        # Check for risk / investigation terms
        has_risk_investigation = any(k in q_lower for k in self.RISK_INVESTIGATION_KEYWORDS)

        # Check for regulatory terms
        has_regulatory = any(k in q_lower for k in self.REGULATORY_KEYWORDS)

        # Check general educational phrasing
        is_general_phrasing = any(re.search(pat, q_lower) for pat in self.GENERAL_EDUCATIONAL_PATTERNS)

        # --- 1. AMBIGUOUS SHORT QUERY CHECK ---
        if len(clean_q.split()) <= 1 and clean_q.lower() in {"balance", "account", "transactions", "kyc"}:
            if user_sess.role == UserRole.PUBLIC:
                return RoutingDecision(
                    intent=QueryIntent.CUSTOMER_INFORMATION,
                    original_query=clean_q,
                    requires_auth=True,
                    access_granted=False,
                    denial_reason="Please sign in to view your personal account balance and transactions, or ask a general banking question (e.g., 'What is KYC?')."
                )
            else:
                return RoutingDecision(
                    intent=QueryIntent.CUSTOMER_INFORMATION,
                    original_query=clean_q,
                    target_customer_id=user_sess.customer_id,
                    needs_clarification=True,
                    clarification_message=f"Would you like to view your current balance, recent transactions, or KYC details for customer {user_sess.customer_id}?"
                )

        # --- 2. MIXED QUERY DETECTION ---
        # Query combines a general concept explanation with a personal account check
        # e.g., "Explain money mule fraud and tell me whether my transactions resemble that pattern."
        # or "What is UPI fraud and why was my debit flagged?"
        FRAUD_OR_REGULATORY_CONCEPTS = {
            "mule", "upi", "phishing", "takeover", "ato", "round-tripping", "structuring",
            "ponzi", "scam", "fraud", "rbi", "fatf", "section", "master direction",
            "smishing", "vishing", "cybercrime", "money laundering", "due diligence"
        }
        has_general_concept = any(c in q_lower for c in FRAUD_OR_REGULATORY_CONCEPTS) or has_regulatory

        is_mixed = (
            has_general_concept
            and has_first_person
            and (has_account_info or has_risk_investigation)
        )

        if is_mixed:
            # If public user asks a mixed query, answer public part and inform to login for personal part
            if user_sess.role == UserRole.PUBLIC:
                return RoutingDecision(
                    intent=QueryIntent.MIXED_QUERY,
                    original_query=clean_q,
                    requires_auth=True,
                    access_granted=True,  # Partially granted: public portion will be answered!
                    public_subquery=self._extract_public_portion(clean_q),
                    private_subquery=clean_q,
                    denial_reason="The general banking portion has been answered below. To analyze your personal transactions and account records, please sign in or log in with your customer profile."
                )
            elif user_sess.role == UserRole.CUSTOMER:
                return RoutingDecision(
                    intent=QueryIntent.MIXED_QUERY,
                    original_query=clean_q,
                    target_customer_id=user_sess.customer_id,
                    access_granted=True,
                    public_subquery=self._extract_public_portion(clean_q),
                    private_subquery=clean_q
                )
            else: # COMPLIANCE_OFFICER
                target_cid = explicit_customer_id or detected_cid or user_sess.customer_id
                return RoutingDecision(
                    intent=QueryIntent.MIXED_QUERY,
                    original_query=clean_q,
                    target_customer_id=target_cid,
                    access_granted=True,
                    public_subquery=self._extract_public_portion(clean_q),
                    private_subquery=clean_q
                )

        # --- 3. CUSTOMER INFORMATION & RISK INVESTIGATION ---
        # If user explicitly references "my balance", "my transactions", or first-person account questions
        if has_first_person and has_account_info and not has_risk_investigation:
            # Customer Info intent
            if user_sess.role == UserRole.PUBLIC:
                return RoutingDecision(
                    intent=QueryIntent.CUSTOMER_INFORMATION,
                    original_query=clean_q,
                    requires_auth=True,
                    access_granted=False,
                    denial_reason="Viewing personal account balances and transaction histories requires an authenticated customer session. Please sign in or log in to view your records."
                )
            elif user_sess.role == UserRole.CUSTOMER:
                return RoutingDecision(
                    intent=QueryIntent.CUSTOMER_INFORMATION,
                    original_query=clean_q,
                    target_customer_id=user_sess.customer_id,
                    access_granted=True
                )
            else: # Officer
                target_cid = explicit_customer_id or detected_cid or user_sess.customer_id
                if not target_cid:
                    return RoutingDecision(
                        intent=QueryIntent.CUSTOMER_INFORMATION,
                        original_query=clean_q,
                        needs_clarification=True,
                        clarification_message="As a compliance officer, please select or specify the customer profile you wish to inspect."
                    )
                return RoutingDecision(
                    intent=QueryIntent.CUSTOMER_INFORMATION,
                    original_query=clean_q,
                    target_customer_id=target_cid,
                    access_granted=True
                )

        if (has_first_person and has_risk_investigation) or ("flagged" in q_lower and has_first_person):
            # Personal Risk Investigation
            if user_sess.role == UserRole.PUBLIC:
                return RoutingDecision(
                    intent=QueryIntent.RISK_INVESTIGATION,
                    original_query=clean_q,
                    requires_auth=True,
                    access_granted=False,
                    denial_reason="Investigating flagged transactions or risk indicators requires customer authentication. Please log in to inspect your account security."
                )
            elif user_sess.role == UserRole.CUSTOMER:
                return RoutingDecision(
                    intent=QueryIntent.RISK_INVESTIGATION,
                    original_query=clean_q,
                    target_customer_id=user_sess.customer_id,
                    access_granted=True
                )
            else: # Officer
                target_cid = explicit_customer_id or detected_cid or user_sess.customer_id
                return RoutingDecision(
                    intent=QueryIntent.RISK_INVESTIGATION,
                    original_query=clean_q,
                    target_customer_id=target_cid,
                    access_granted=True
                )

        # --- 4. OFFICER / EXPLICIT CUSTOMER INVESTIGATION ---
        # When a customer ID or name is explicitly referenced in an investigative query
        if detected_cid or explicit_customer_id:
            target_cid = explicit_customer_id or detected_cid

            # Security rule: Customer CANNOT investigate other customers via prompt injection
            if user_sess.role == UserRole.CUSTOMER:
                if target_cid != user_sess.customer_id:
                    return RoutingDecision(
                        intent=QueryIntent.CUSTOMER_INFORMATION,
                        original_query=clean_q,
                        target_customer_id=user_sess.customer_id, # Fall back strictly to self!
                        access_granted=False,
                        denial_reason=f"Access Denied: You are authenticated as {user_sess.customer_id}. You are not authorized to access or query records belonging to customer {target_cid}."
                    )
                else:
                    return RoutingDecision(
                        intent=QueryIntent.RISK_INVESTIGATION if has_risk_investigation else QueryIntent.CUSTOMER_INFORMATION,
                        original_query=clean_q,
                        target_customer_id=user_sess.customer_id,
                        access_granted=True
                    )

            elif user_sess.role == UserRole.COMPLIANCE_OFFICER:
                return RoutingDecision(
                    intent=QueryIntent.RISK_INVESTIGATION,
                    original_query=clean_q,
                    target_customer_id=target_cid,
                    access_granted=True
                )

            else: # PUBLIC USER with injected customer ID
                # Public users cannot query customer records even if they type a customer ID
                if has_account_info or has_risk_investigation:
                    return RoutingDecision(
                        intent=QueryIntent.CUSTOMER_INFORMATION,
                        original_query=clean_q,
                        requires_auth=True,
                        access_granted=False,
                        denial_reason=f"Private customer records for {target_cid} cannot be accessed publicly without authentication. Please log in as the account holder or compliance officer."
                    )

        # --- 5. REGULATORY QUERY ---
        # Specific inquiry on statutory frameworks, sections, or compliance directives
        if has_regulatory and not has_first_person:
            return RoutingDecision(
                intent=QueryIntent.REGULATORY_QUERY,
                original_query=clean_q,
                access_granted=True
            )

        # --- 6. GENERAL KNOWLEDGE (DEFAULT PUBLIC PATH) ---
        return RoutingDecision(
            intent=QueryIntent.GENERAL_KNOWLEDGE,
            original_query=clean_q,
            access_granted=True
        )

    def _extract_customer_id(self, query: str) -> Optional[str]:
        """Detect synthetic customer ID pattern CUST_SYNTH_XXX or known IDs."""
        match = re.search(r"\b(CUST_SYNTH_\d{3})\b", query, re.IGNORECASE)
        if match:
            return match.group(1).upper()
        for cid in self.known_customer_ids:
            if re.search(r"\b" + re.escape(cid) + r"\b", query, re.IGNORECASE):
                return cid
        return None

    def _extract_all_customer_ids(self, query: str) -> List[str]:
        """Detect all customer IDs mentioned in query text."""
        matches = list(dict.fromkeys(re.findall(r"\b(CUST_SYNTH_\d{3})\b", query, re.IGNORECASE)))
        res = [m.upper() for m in matches]
        for cid in self.known_customer_ids:
            if re.search(r"\b" + re.escape(cid) + r"\b", query, re.IGNORECASE) and cid not in res:
                res.append(cid)
        return res

    def _extract_public_portion(self, query: str) -> str:
        """Isolate the general/educational part of a mixed question."""
        # e.g., "Explain money mule fraud and tell me whether my transactions resemble that pattern."
        # -> "Explain money mule fraud"
        parts = re.split(r"\b(?:and\s+(?:tell\s+me\s+)?whether|and\s+why|and\s+check\s+if|and\s+show)\b", query, flags=re.IGNORECASE)
        if len(parts) > 1 and len(parts[0].strip()) > 10:
            return parts[0].strip()
        return query
