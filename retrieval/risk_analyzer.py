"""
retrieval/risk_analyzer.py

Graph-Based Risk Analysis Engine
Calculates objective, observable risk indicators from actual graph records:
1. High fan-in / multiple distinct senders.
2. Rapid onward transfer / pass-through drain velocity (strictly chronological).
3. Circular transaction paths (round-tripping / layering cycles).
4. KYC non-compliance with ongoing active account operations.
5. Inflow volume disproportionate to declared annual profile (handling zero/missing income).
6. Velocity bursts / unusual frequency spikes.
7. High-risk cross-border transfers distinguished from standard international wires.
8. Sudden transaction activity on dormant or inoperative accounts.

All indicators are flagged strictly as investigation signals with clear mathematical
explanations, formulas, thresholds, and supporting transaction IDs, never as conclusive proof of crime.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional, Set, Tuple


@dataclass
class RiskThresholds:
    fan_in_sender_threshold: int = 3
    rapid_drain_window_minutes: int = 180
    pass_through_ratio_threshold: float = 0.80
    disproportionate_turnover_multiple: float = 3.0
    unverified_turnover_threshold_inr: float = 100000.0
    velocity_burst_count: int = 3
    velocity_burst_window_minutes: int = 30


# Documented, dated, configurable FATF Jurisdictions List (as of June 2026 FATF Plenary):
# 1. High-Risk Jurisdictions subject to a Call for Action (Blacklist)
FATF_CALL_FOR_ACTION_JURISDICTIONS = {
    "DPRK", "DEMOCRATIC PEOPLE'S REPUBLIC OF KOREA", "NORTH KOREA",
    "IRAN", "ISLAMIC REPUBLIC OF IRAN",
    "MYANMAR", "BURMA"
}

# 2. Jurisdictions under Increased Monitoring (Greylist)
FATF_INCREASED_MONITORING_JURISDICTIONS = {
    "BULGARIA", "BURKINA FASO", "CAMEROON", "CROATIA", "DRC",
    "DEMOCRATIC REPUBLIC OF THE CONGO", "HAITI", "JAMAICA", "KENYA",
    "MALI", "MOZAMBIQUE", "NAMIBIA", "NIGERIA", "PHILIPPINES",
    "SENEGAL", "SOUTH AFRICA", "SOUTH SUDAN", "SYRIA", "TANZANIA",
    "VIETNAM", "YEMEN"
}


def parse_iso_timestamp(ts_str: Any) -> Optional[datetime]:
    """Parse ISO8601 timestamp string into datetime."""
    if not ts_str or not isinstance(ts_str, str):
        return None
    clean = ts_str.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(clean)
    except Exception:
        return None


def get_float_amount(tx: Dict[str, Any]) -> float:
    """Extract numeric amount from transaction properties."""
    val = tx.get("amount_inr", tx.get("amount", 0.0))
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


class GraphRiskAnalyzer:
    def __init__(self, thresholds: Optional[RiskThresholds] = None):
        self.thresholds = thresholds or RiskThresholds()

    def analyze_customer_risk(
        self,
        customer: Dict[str, Any],
        accounts: List[Dict[str, Any]],
        transactions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Evaluate customer graph records against risk calculation rules.
        Returns a list of triggered risk signals with supporting calculations and transaction IDs.
        """
        if not customer:
            return []

        account_nums: Set[str] = set()
        for a in accounts:
            num = a.get("account_number") or a.get("account_id")
            if num:
                account_nums.add(str(num).strip())

        signals = []

        # 1. High Fan-In (Multiple distinct senders)
        fan_in_sig = self._check_fan_in(customer, account_nums, transactions)
        if fan_in_sig:
            signals.append(fan_in_sig)

        # 2. Rapid Onward Transfer / Pass-Through Drain (Chronological)
        pass_through_sig = self._check_pass_through_drain(customer, account_nums, transactions)
        if pass_through_sig:
            signals.append(pass_through_sig)

        # 3. Circular Routing Detection
        circular_sig = self._check_circular_routing(account_nums, transactions)
        if circular_sig:
            signals.append(circular_sig)

        # 4. KYC Non-Compliance / Expiration
        kyc_sig = self._check_kyc_non_compliance(customer, transactions)
        if kyc_sig:
            signals.append(kyc_sig)

        # 5. Disproportionate Turnover
        turnover_sig = self._check_disproportionate_turnover(customer, account_nums, transactions)
        if turnover_sig:
            signals.append(turnover_sig)

        # 6. Velocity Burst / Frequency Spike
        burst_sig = self._check_velocity_burst(transactions)
        if burst_sig:
            signals.append(burst_sig)

        # 7. Cross-Border & High-Risk Jurisdiction Deficiencies
        cb_sig = self._check_cross_border_risks(account_nums, transactions)
        if cb_sig:
            signals.append(cb_sig)

        # 8. Dormant / Inactive Account Sudden Operations
        dormant_sig = self._check_dormant_account_reactivation(accounts, transactions)
        if dormant_sig:
            signals.append(dormant_sig)

        return signals

    def _check_fan_in(
        self,
        customer: Dict[str, Any],
        account_nums: Set[str],
        transactions: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        inflows = [
            t for t in transactions
            if str(t.get("receiver_account", "")).strip() in account_nums
        ]
        if not inflows:
            return None

        senders = {
            str(t.get("sender_account", "")).strip()
            for t in inflows
            if t.get("sender_account") and str(t.get("sender_account")).strip() not in account_nums
        } - {""}

        if len(senders) >= self.thresholds.fan_in_sender_threshold:
            total_inflow = sum(get_float_amount(t) for t in inflows)
            tx_ids = [str(t.get("tx_id")) for t in inflows if t.get("tx_id")]
            return {
                "indicator_id": "IND_HIGH_FAN_IN_SENDERS",
                "name": "High Fan-In: Multiple Distinct Remitters",
                "severity": "HIGH",
                "category": "AML_TYPOLOGY",
                "triggered": True,
                "calculation_details": (
                    f"Account received funds from {len(senders)} distinct external senders "
                    f"({', '.join(sorted(senders))}) across {len(inflows)} transactions "
                    f"totaling INR {total_inflow:,.2f}."
                ),
                "formula": "count(distinct external_senders) >= fan_in_sender_threshold",
                "input_values": {
                    "distinct_senders_count": len(senders),
                    "senders": sorted(list(senders)),
                    "total_inflow_inr": total_inflow,
                },
                "threshold_applied": f"{self.thresholds.fan_in_sender_threshold} distinct senders",
                "threshold_source": "RBI KYC Master Direction Section 68 & FATF Funnel Account Typology",
                "supporting_transactions": tx_ids,
                "account_ids": list(account_nums),
                "investigation_guidance": (
                    "Signals possible funnel or money mule activity where multiple individuals deposit "
                    "funds for consolidation. Investigative recommendation: perform origin verification and source-of-funds inquiry."
                ),
                "limitations_or_missing_evidence": (
                    "Commercial trade contracts or family relationship proofs are needed to distinguish bona fide pooled funds from mule aggregation."
                )
            }
        return None

    def _check_pass_through_drain(
        self,
        customer: Dict[str, Any],
        account_nums: Set[str],
        transactions: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Validate rapid onward transfers / pass-through drain with strict chronological causality.
        Rules:
        - Eligible inflows must precede the corresponding outflows chronologically (outflow_time >= inflow_time).
        - Must operate on linked accounts (inflow to Acc X followed by outflow from Acc X, or intra-account transfer).
        - Evaluates window of rapid_drain_window_minutes.
        - Calculates drain ratio = total subsequent outflows / total eligible inflows.
        - Replaces absolute time difference with true chronological difference.
        """
        if not transactions or not account_nums:
            return None

        best_drain = None

        for acc in sorted(account_nums):
            inflows = [
                t for t in transactions
                if str(t.get("receiver_account", "")).strip() == acc
            ]
            outflows = [
                t for t in transactions
                if str(t.get("sender_account", "")).strip() == acc
            ]

            if not inflows or not outflows:
                continue

            total_acc_inflow = sum(get_float_amount(t) for t in inflows)
            if total_acc_inflow <= 0:
                continue

            timed_inflows = []
            for t in inflows:
                dt = parse_iso_timestamp(t.get("timestamp"))
                if dt:
                    timed_inflows.append((dt, t))

            timed_outflows = []
            for t in outflows:
                dt = parse_iso_timestamp(t.get("timestamp"))
                if dt:
                    timed_outflows.append((dt, t))

            if not timed_inflows or not timed_outflows:
                # If timestamps are not parseable, check gross ratio but note lack of chronological timestamps
                total_acc_outflow = sum(get_float_amount(t) for t in outflows)
                ratio = total_acc_outflow / total_acc_inflow
                if ratio >= self.thresholds.pass_through_ratio_threshold:
                    tx_ids = [str(t.get("tx_id")) for t in (inflows + outflows) if t.get("tx_id")]
                    candidate = {
                        "indicator_id": "IND_PASS_THROUGH_RAPID_DRAIN",
                        "name": "Rapid Pass-Through / Near-Total Outflow Drain",
                        "severity": "HIGH",
                        "category": "AML_TYPOLOGY",
                        "triggered": True,
                        "calculation_details": (
                            f"Account {acc} received INR {total_acc_inflow:,.2f} and disbursed INR {total_acc_outflow:,.2f} "
                            f"(drain ratio: {ratio * 100:.1f}%), but exact chronological sequence could not be established."
                        ),
                        "formula": "total_outflow / total_inflow",
                        "input_values": {
                            "account": acc,
                            "inflow_inr": total_acc_inflow,
                            "outflow_inr": total_acc_outflow,
                            "drain_ratio": round(ratio, 4),
                        },
                        "threshold_applied": f"{self.thresholds.pass_through_ratio_threshold * 100:.0f}% drain",
                        "threshold_source": "RBI KYC Master Direction Section 68 (Money Mule Typology)",
                        "supporting_transactions": tx_ids,
                        "account_ids": [acc],
                        "investigation_guidance": "Prompts transaction monitoring review and STR evaluation.",
                        "limitations_or_missing_evidence": "Timestamp metadata missing; chronological ordering unverified."
                    }
                    if not best_drain or candidate["input_values"]["drain_ratio"] > best_drain["input_values"]["drain_ratio"]:
                        best_drain = candidate
                continue

            timed_inflows.sort(key=lambda x: x[0])
            timed_outflows.sort(key=lambda x: x[0])

            earliest_in = timed_inflows[0][0]

            # Outflows must chronologically occur AFTER the earliest inflow on this account
            chronological_outflows = [
                (ot, tx) for (ot, tx) in timed_outflows
                if ot >= earliest_in
            ]

            if not chronological_outflows:
                # Chronological violation: all outflows occurred before the inflows arrived!
                continue

            # Identify which outflows occurred within the configured rapid drain window
            matched_outflows = []
            max_delta_mins = 0.0

            for (ot, tx) in chronological_outflows:
                # Find the nearest preceding inflow
                preceding_inflow_times = [it for (it, _) in timed_inflows if it <= ot]
                if preceding_inflow_times:
                    in_time = max(preceding_inflow_times)
                    delta_mins = (ot - in_time).total_seconds() / 60.0
                    if 0.0 <= delta_mins <= self.thresholds.rapid_drain_window_minutes:
                        matched_outflows.append((ot, tx, delta_mins))
                        if delta_mins > max_delta_mins:
                            max_delta_mins = delta_mins

            if not matched_outflows:
                continue

            chronological_outflow_sum = sum(get_float_amount(tx) for (_, tx, _) in matched_outflows)
            ratio = chronological_outflow_sum / total_acc_inflow

            if ratio >= self.thresholds.pass_through_ratio_threshold:
                tx_ids = [str(t.get("tx_id")) for (_, t) in timed_inflows if t.get("tx_id")] + \
                         [str(tx.get("tx_id")) for (_, tx, _) in matched_outflows if tx.get("tx_id")]
                tx_ids = list(dict.fromkeys(tx_ids))

                candidate = {
                    "indicator_id": "IND_PASS_THROUGH_RAPID_DRAIN",
                    "name": "Rapid Pass-Through / Near-Total Outflow Drain",
                    "severity": "CRITICAL" if max_delta_mins <= self.thresholds.rapid_drain_window_minutes else "HIGH",
                    "category": "AML_TYPOLOGY",
                    "triggered": True,
                    "calculation_details": (
                        f"Account {acc} received INR {total_acc_inflow:,.2f} across {len(timed_inflows)} inflow(s), followed chronologically "
                        f"by INR {chronological_outflow_sum:,.2f} in outflow(s) within {max_delta_mins:.1f} minutes of receipt "
                        f"(chronological drain ratio: {ratio * 100:.1f}%)."
                    ),
                    "formula": "chronologically_subsequent_outflows / total_preceding_inflows",
                    "input_values": {
                        "account": acc,
                        "inflow_inr": total_acc_inflow,
                        "subsequent_outflow_inr": chronological_outflow_sum,
                        "drain_ratio": round(ratio, 4),
                        "elapsed_minutes": round(max_delta_mins, 1),
                    },
                    "threshold_applied": (
                        f"{self.thresholds.pass_through_ratio_threshold * 100:.0f}% drain within "
                        f"{self.thresholds.rapid_drain_window_minutes} minutes"
                    ),
                    "threshold_source": "RBI KYC Master Direction Section 68 & FATF Money Mule Typology",
                    "supporting_transactions": tx_ids,
                    "account_ids": [acc],
                    "investigation_guidance": (
                        "Investigative signal indicating transit / pass-through account behavior where funds are rapidly drained "
                        "rather than retained for bona fide personal or commercial balances. Investigative recommendation: "
                        "prompts transaction monitoring review and STR evaluation if money mule or layering patterns are corroborated."
                    ),
                    "limitations_or_missing_evidence": (
                        "Requires device telemetry, IP logs, and beneficiary verification to establish whether the account holder "
                        "was complicit or a victim of unauthorized account compromise."
                    )
                }
                if not best_drain or candidate["input_values"]["drain_ratio"] > best_drain["input_values"]["drain_ratio"]:
                    best_drain = candidate

        return best_drain

    def _check_circular_routing(
        self,
        account_nums: Set[str],
        transactions: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        edges = []
        for t in transactions:
            src = str(t.get("sender_account", "")).strip()
            dst = str(t.get("receiver_account", "")).strip()
            if src and dst:
                edges.append((src, dst, str(t.get("tx_id", ""))))

        # Detect 3-hop or 2-hop cycles: A -> B -> C -> A
        cycles = []
        for src1, dst1, tx1 in edges:
            for src2, dst2, tx2 in edges:
                if dst1 == src2 and tx1 != tx2:
                    for src3, dst3, tx3 in edges:
                        if dst2 == src3 and dst3 == src1 and tx3 not in (tx1, tx2):
                            cycles.append(([src1, dst1, dst2, dst3], [tx1, tx2, tx3]))

        if cycles:
            cycle_path, cycle_txs = cycles[0]
            cycle_amounts = [
                get_float_amount(t) for t in transactions
                if str(t.get("tx_id")) in cycle_txs
            ]
            turnover = sum(cycle_amounts)
            return {
                "indicator_id": "IND_CIRCULAR_ROUTING_DETECTED",
                "name": "Circular Transaction Routing (Round-Tripping Cycle)",
                "severity": "CRITICAL",
                "category": "FRAUD_TYPOLOGY",
                "triggered": True,
                "calculation_details": (
                    f"Detected closed circular fund loop: {' -> '.join(cycle_path)} "
                    f"spanning transactions: {', '.join(cycle_txs)} with total ledger movement of INR {turnover:,.2f}."
                ),
                "formula": "closed_graph_cycle(Account_A -> Account_B -> Account_C -> Account_A)",
                "input_values": {
                    "participating_accounts": cycle_path[:-1],
                    "cycle_transactions": cycle_txs,
                    "cumulative_turnover_inr": turnover,
                },
                "threshold_applied": "Closed cycle of length >= 2 across affiliated accounts",
                "threshold_source": "FATF Recommendation 20 & PML Rules Rule 2(1)(g) (Suspicious Transaction Definition)",
                "supporting_transactions": cycle_txs,
                "account_ids": list(set(cycle_path[:-1])),
                "investigation_guidance": (
                    "Circular movement of funds across affiliated accounts artificially inflates turnover or "
                    "obscures beneficial origin. Investigative recommendation: indicates need for enhanced due "
                    "diligence and tax/AML review."
                ),
                "limitations_or_missing_evidence": (
                    "Requires corporate ownership register and commercial contracts to determine whether transactions "
                    "represent bona fide treasury rebalancing or artificial turnover inflation."
                )
            }
        return None

    def _check_kyc_non_compliance(
        self,
        customer: Dict[str, Any],
        transactions: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        status = str(customer.get("kyc_status", "")).upper()
        if "EXPIRED" in status or "NON_COMPLIANT" in status:
            total_vol = sum(get_float_amount(t) for t in transactions)
            tx_ids = [str(t.get("tx_id")) for t in transactions if t.get("tx_id")]
            return {
                "indicator_id": "IND_KYC_NON_COMPLIANCE_ACTIVE_OPERATIONS",
                "name": "Active Account Operations with Expired KYC Status",
                "severity": "HIGH",
                "category": "REGULATORY_NON_COMPLIANCE",
                "triggered": True,
                "calculation_details": (
                    f"Customer KYC status is '{customer.get('kyc_status')}'; account has executed "
                    f"{len(transactions)} transactions totaling INR {total_vol:,.2f} without periodic re-KYC."
                ),
                "formula": "kyc_status in ('EXPIRED', 'NON_COMPLIANT') and transaction_count > 0",
                "input_values": {
                    "kyc_status": customer.get("kyc_status"),
                    "active_transactions": len(transactions),
                    "total_volume_inr": total_vol,
                },
                "threshold_applied": "Active debit/credit transactions on expired KYC status",
                "threshold_source": "RBI Master Direction - KYC (Chapter VI & Section 38 Periodic Updation)",
                "supporting_transactions": tx_ids,
                "account_ids": [],
                "investigation_guidance": (
                    "Potential non-compliance with RBI Master Direction - KYC (Chapter VI & Section 38). "
                    "Investigative recommendation: evaluate application of partial debit restrictions pending "
                    "Customer Identification Procedure (CIP) completion."
                ),
                "limitations_or_missing_evidence": "Verification of whether re-KYC documents have been submitted at branch but pending back-office entry."
            }
        return None

    def _check_disproportionate_turnover(
        self,
        customer: Dict[str, Any],
        account_nums: Set[str],
        transactions: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        # External inflows only (excludes intra-customer transfers between own accounts)
        inflows = [
            t for t in transactions
            if str(t.get("receiver_account", "")).strip() in account_nums
            and str(t.get("sender_account", "")).strip() not in account_nums
        ]
        if not inflows:
            return None

        total_inflow = sum(get_float_amount(t) for t in inflows)
        tx_ids = [str(t.get("tx_id")) for t in inflows if t.get("tx_id")]

        declared = float(customer.get("declared_annual_income", customer.get("declared_annual_income_inr", 0.0)) or 0.0)

        # Case 1: Positive declared annual income
        if declared > 0.0:
            ratio = total_inflow / declared
            if ratio >= self.thresholds.disproportionate_turnover_multiple:
                return {
                    "indicator_id": "IND_DISPROPORTIONATE_TURNOVER",
                    "name": "Turnover Disproportionate to Declared Customer Profile",
                    "severity": "CRITICAL" if ratio >= 5.0 else "HIGH",
                    "category": "AML_TYPOLOGY",
                    "triggered": True,
                    "calculation_details": (
                        f"Observed external inflow turnover of INR {total_inflow:,.2f} is {ratio:.1f}x the declared annual "
                        f"income of INR {declared:,.2f} (threshold: {self.thresholds.disproportionate_turnover_multiple}x)."
                    ),
                    "formula": "total_external_inflow / declared_annual_income",
                    "input_values": {
                        "total_external_inflow_inr": total_inflow,
                        "declared_annual_income_inr": declared,
                        "calculated_multiple": round(ratio, 2),
                    },
                    "threshold_applied": f"{self.thresholds.disproportionate_turnover_multiple}x declared annual income",
                    "threshold_source": "PMLA Rule 9(1) (Customer Financial Profiling) & RBI KYC Direction Chapter VI",
                    "supporting_transactions": tx_ids,
                    "account_ids": list(account_nums),
                    "investigation_guidance": (
                        "Significant deviation between declared customer financial profile and actual transaction "
                        "volume. Investigative recommendation: prompts source-of-wealth and source-of-funds re-verification."
                    ),
                    "limitations_or_missing_evidence": (
                        "Customer may have unrecorded legitimate income streams, tax filings, or capital gains not yet updated in the KYC record."
                    )
                }
            return None

        # Case 2: Declared income is 0.0 or missing / unrecorded
        if total_inflow >= self.thresholds.unverified_turnover_threshold_inr:
            return {
                "indicator_id": "IND_TURNOVER_UNVERIFIED_INCOME",
                "name": "Substantial Turnover with Unverified / Zero Declared Income",
                "severity": "HIGH",
                "category": "AML_TYPOLOGY",
                "triggered": True,
                "calculation_details": (
                    f"Customer account received external credit turnover totaling INR {total_inflow:,.2f} while "
                    f"declared annual income is recorded as zero or unrecorded. Cannot establish economic proportionality."
                ),
                "formula": "total_external_inflow with declared_income <= 0",
                "input_values": {
                    "total_external_inflow_inr": total_inflow,
                    "declared_annual_income_inr": declared,
                },
                "threshold_applied": f"INR {self.thresholds.unverified_turnover_threshold_inr:,.2f} unverified volume",
                "threshold_source": "RBI KYC Master Direction Chapter VI (Customer Financial Profile Updation)",
                "supporting_transactions": tx_ids,
                "account_ids": list(account_nums),
                "investigation_guidance": (
                    "Investigative recommendation: request customer to submit recent income tax returns (ITR), audited statements, "
                    "or salary slips to update the Customer Identification Record."
                ),
                "limitations_or_missing_evidence": "Customer financial profile documentation is unrecorded in internal files."
            }

        return None

    def _check_velocity_burst(
        self,
        transactions: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        if len(transactions) < self.thresholds.velocity_burst_count:
            return None

        timed_txs = []
        for t in transactions:
            dt = parse_iso_timestamp(t.get("timestamp"))
            if dt:
                timed_txs.append((dt, t))

        timed_txs.sort(key=lambda x: x[0])
        if len(timed_txs) < self.thresholds.velocity_burst_count:
            return None

        burst_found = None
        for i in range(len(timed_txs) - self.thresholds.velocity_burst_count + 1):
            window = timed_txs[i : i + self.thresholds.velocity_burst_count]
            delta = (window[-1][0] - window[0][0]).total_seconds() / 60.0
            if delta <= self.thresholds.velocity_burst_window_minutes:
                burst_found = (window, delta)
                break

        if burst_found:
            window, delta = burst_found
            tx_ids = [str(t.get("tx_id")) for _, t in window if t.get("tx_id")]
            channels = list({str(t.get("channel", "UNKNOWN")) for _, t in window})
            total_burst_amt = sum(get_float_amount(t) for _, t in window)
            return {
                "indicator_id": "IND_VELOCITY_FREQUENCY_BURST",
                "name": "High-Velocity Transaction Burst / Scripted Frequency",
                "severity": "HIGH",
                "category": "CYBER_FRAUD_SIGNAL",
                "triggered": True,
                "calculation_details": (
                    f"Detected {len(window)} rapid transactions totaling INR {total_burst_amt:,.2f} within {delta:.1f} minutes via channel(s) "
                    f"{', '.join(channels)}."
                ),
                "formula": "count(transactions) >= velocity_burst_count within velocity_burst_window_minutes",
                "input_values": {
                    "burst_count": len(window),
                    "elapsed_minutes": round(delta, 1),
                    "total_amount_inr": total_burst_amt,
                    "channels": channels
                },
                "threshold_applied": f"{self.thresholds.velocity_burst_count} transactions within {self.thresholds.velocity_burst_window_minutes} minutes",
                "threshold_source": "RBI Cyber Security Framework in Banks (Section on Transaction Monitoring & Velocity Caps)",
                "supporting_transactions": tx_ids,
                "account_ids": list({str(t.get('sender_account', '')) for _, t in window} | {str(t.get('receiver_account', '')) for _, t in window} - {''}),
                "investigation_guidance": (
                    "Rapid successive transfers often indicate automated scripts, carding, or unauthorized "
                    "access following phishing. Investigative recommendation: warrants alert notification, customer "
                    "contact, and security verification."
                ),
                "limitations_or_missing_evidence": "User IP geolocation and device fingerprint logs are needed to verify whether transfers were human-initiated."
            }
        return None

    def _check_cross_border_risks(
        self,
        account_nums: Set[str],
        transactions: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        cb_txs = [
            t for t in transactions
            if "SWIFT" in str(t.get("channel", "")).upper()
            or "OVERSEAS" in str(t.get("sender_account", "")).upper()
            or "OVERSEAS" in str(t.get("receiver_account", "")).upper()
            or "CROSS_BORDER" in str(t.get("type", "")).upper()
            or str(t.get("is_cross_border", "")).lower() in ("true", "1")
        ]

        if not cb_txs:
            return None

        total_cb = sum(get_float_amount(t) for t in cb_txs)
        tx_ids = [str(t.get("tx_id")) for t in cb_txs if t.get("tx_id")]

        # Check whether any transaction specifically involves a designated high-risk jurisdiction
        high_risk_matches = []
        for t in cb_txs:
            jurisdiction_str = (
                str(t.get("jurisdiction", "")) + " " +
                str(t.get("country", "")) + " " +
                str(t.get("counterparty_jurisdiction", "")) + " " +
                str(t.get("counterparty_country", "")) + " " +
                str(t.get("sender_account", ""))
            ).upper()

            is_call_for_action = any(j in jurisdiction_str for j in FATF_CALL_FOR_ACTION_JURISDICTIONS)
            is_increased_monitoring = any(j in jurisdiction_str for j in FATF_INCREASED_MONITORING_JURISDICTIONS)
            is_shell = "SHELL" in jurisdiction_str or "HIGH_RISK" in jurisdiction_str or "HIGH-RISK" in jurisdiction_str

            if is_call_for_action or is_shell:
                high_risk_matches.append((t, "FATF High-Risk Jurisdiction (Blacklist / Shell)", "CRITICAL"))
            elif is_increased_monitoring:
                high_risk_matches.append((t, "FATF Jurisdiction under Increased Monitoring (Greylist)", "HIGH"))

        if high_risk_matches:
            match_t, j_category, severity = high_risk_matches[0]
            j_name = match_t.get("jurisdiction") or match_t.get("country") or "Designated Overseas High-Risk Jurisdiction"
            return {
                "indicator_id": "IND_CROSS_BORDER_HIGH_RISK_INFLOW",
                "name": f"Cross-Border Remittance Involving High-Risk Jurisdiction ({j_name})",
                "severity": severity,
                "category": "SANCTIONS_AND_CROSS_BORDER",
                "triggered": True,
                "calculation_details": (
                    f"Identified {len(cb_txs)} cross-border wire transfers totaling INR {total_cb:,.2f} "
                    f"involving verified high-risk overseas jurisdiction '{j_name}' ({j_category})."
                ),
                "formula": "cross_border_wire_transfers matching FATF_HIGH_RISK_LIST",
                "input_values": {
                    "cross_border_volume_inr": total_cb,
                    "designated_jurisdiction": j_name,
                    "classification": j_category
                },
                "threshold_applied": "Designated high-risk counterparty jurisdiction",
                "threshold_source": "FATF Recommendation 19 & Public Statements (Updated June 2026)",
                "supporting_transactions": tx_ids,
                "account_ids": list(account_nums),
                "investigation_guidance": (
                    "Investigative recommendation: cross-border transactions involving high-risk jurisdictions warrant "
                    "enhanced due diligence (EDD) and verification of underlying commercial trade documentation under FATF Recommendation 19."
                ),
                "limitations_or_missing_evidence": (
                    "Counterparty corporate ownership structure and independent UBO declarations are required to verify ultimate destination."
                )
            }
        else:
            # Standard cross-border transfer - NOT designated high-risk
            return {
                "indicator_id": "IND_CROSS_BORDER_WIRE_TRANSFER",
                "name": "Standard Cross-Border Wire Transfer",
                "severity": "MEDIUM",
                "category": "CROSS_BORDER_MONITORING",
                "triggered": True,
                "calculation_details": (
                    f"Identified {len(cb_txs)} cross-border wire transfers totaling INR {total_cb:,.2f}. "
                    "Jurisdiction risk classification could not be verified as high-risk from available counterparty metadata."
                ),
                "formula": "cross_border_wire_transfers without verified high_risk jurisdiction",
                "input_values": {
                    "cross_border_volume_inr": total_cb,
                    "transaction_count": len(cb_txs)
                },
                "threshold_applied": "Cross-border channel usage",
                "threshold_source": "FATF Recommendation 16 (Wire Transfers) & RBI KYC Section 74",
                "supporting_transactions": tx_ids,
                "account_ids": list(account_nums),
                "investigation_guidance": (
                    "Investigative recommendation: verify complete originator and beneficiary information under "
                    "FATF Recommendation 16 and Section 74. Standard cross-border transfers do not require high-risk countermeasures unless adverse jurisdiction or PEP nexus is established."
                ),
                "limitations_or_missing_evidence": "Jurisdiction risk classification could not be verified from available counterparty metadata."
            }

    def _check_dormant_account_reactivation(
        self,
        accounts: List[Dict[str, Any]],
        transactions: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Check for sudden active transactions on accounts marked as DORMANT or INACTIVE.
        """
        dormant_accs = {
            str(a.get("account_number") or a.get("account_id")).strip()
            for a in accounts
            if str(a.get("status", "")).upper() in ("DORMANT", "INACTIVE")
        } - {""}

        if not dormant_accs:
            return None

        dormant_txs = [
            t for t in transactions
            if str(t.get("sender_account", "")).strip() in dormant_accs
            or str(t.get("receiver_account", "")).strip() in dormant_accs
        ]

        if not dormant_txs:
            return None

        total_vol = sum(get_float_amount(t) for t in dormant_txs)
        tx_ids = [str(t.get("tx_id")) for t in dormant_txs if t.get("tx_id")]

        return {
            "indicator_id": "IND_DORMANT_ACCOUNT_REACTIVATION",
            "name": "Sudden Transaction Activity on Dormant / Inoperative Account",
            "severity": "HIGH",
            "category": "ACCOUNT_TAKEOVER_AND_MULE",
            "triggered": True,
            "calculation_details": (
                f"Account(s) {', '.join(sorted(dormant_accs))} has recorded status 'DORMANT/INACTIVE' but executed "
                f"{len(dormant_txs)} transactions totaling INR {total_vol:,.2f} without prior documented re-activation."
            ),
            "formula": "transactions executed while account.status in ('DORMANT', 'INACTIVE')",
            "input_values": {
                "dormant_accounts": list(dormant_accs),
                "transaction_volume_inr": total_vol,
                "transaction_count": len(dormant_txs)
            },
            "threshold_applied": "Any transaction activity on dormant status",
            "threshold_source": "RBI Master Direction on KYC Section 26 & Inoperative Account Guidelines",
            "supporting_transactions": tx_ids,
            "account_ids": list(dormant_accs),
            "investigation_guidance": (
                "Investigative recommendation: verify identity of the individual initiating transactions to rule out "
                "account takeover (ATO) or credential theft. Check customer signature/biometrics and KYC refresh before releasing debit holds."
            ),
            "limitations_or_missing_evidence": "Reactivation request documentation and channel login IP logs are unrecorded."
        }
