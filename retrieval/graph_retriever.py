
"""
GraphRAG Banking Compliance & Risk Intelligence System
Retrieves regulatory evidence using BM25 and customer risk data from Neo4j.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from retrieval.document_retriever import DocumentRetriever
from retrieval.risk_analyzer import GraphRiskAnalyzer
from retrieval.answer_generator import GraphRAGAnswerGenerator
from retrieval.scenario_analyzer import ScenarioAnalyzer, ScenarioAnalysis
from retrieval.evidence_validator import EvidenceValidator, ClaimValidationResult
from retrieval.query_router import (
    QueryRouter,
    QueryIntent,
    UserRole,
    UserSession,
    RoutingDecision,
)

try:
    from neo4j import GraphDatabase
except ImportError:
    GraphDatabase = None


def normalize(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()


def get_value(properties: Dict[str, Any], *keys: str,
              default: str = "") -> str:
    for key in keys:
        value = properties.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return default


def strip_fictional_suffix(name: str) -> str:
    """Strip (Fictional), (Fictional Entity), etc. for user-friendly name matching."""
    return re.sub(
        r"\s*\((?:fictional(?:\s+entity)?|fictional)\)\s*$",
        "",
        str(name or ""),
        flags=re.IGNORECASE
    ).strip()


def _build_graph_paths(customer: Dict[str, Any], accounts: list, transactions: list) -> list:
    """Format readable graph traversal paths from customer, accounts and transactions."""
    paths = []
    cid = get_value(customer, "customer_id", "id", default="CUSTOMER")
    acc_map = {get_value(a, "account_number", "account_id"): a for a in accounts}

    # 1. Ownership paths
    for acc_num in acc_map:
        paths.append(f"(:Customer {{customer_id: '{cid}'}})-[:OWNS_ACCOUNT]->(:Account {{account_number: '{acc_num}'}})")

    # 2. Multi-hop circular cycle detection (Round-tripping loop)
    tx_by_sender = {}
    for tx in transactions:
        s = get_value(tx, "sender_account", "from_account")
        if s:
            tx_by_sender[s] = tx

    visited = set()
    for s_acc, tx1 in tx_by_sender.items():
        dst1 = get_value(tx1, "receiver_account", "to_account")
        if dst1 in tx_by_sender:
            tx2 = tx_by_sender[dst1]
            dst2 = get_value(tx2, "receiver_account", "to_account")
            if dst2 in tx_by_sender:
                tx3 = tx_by_sender[dst2]
                dst3 = get_value(tx3, "receiver_account", "to_account")
                if dst3 == s_acc and s_acc not in visited:
                    visited.add(s_acc)
                    visited.add(dst1)
                    visited.add(dst2)
                    paths.insert(
                        0,
                        f"[CIRCULAR_FLOW_CYCLE]: (:Account {{account_number: '{s_acc}'}})-[:SENT_TRANSACTION]->"
                        f"(:Transaction {{tx_id: '{get_value(tx1, 'tx_id')}'}})->(:Account {{account_number: '{dst1}'}})-[:SENT_TRANSACTION]->"
                        f"(:Transaction {{tx_id: '{get_value(tx2, 'tx_id')}'}})->(:Account {{account_number: '{dst2}'}})-[:SENT_TRANSACTION]->"
                        f"(:Transaction {{tx_id: '{get_value(tx3, 'tx_id')}'}})->(:Account {{account_number: '{s_acc}'}})"
                    )

    # 3. Individual transaction hop paths
    for tx in transactions:
        tx_id = get_value(tx, "tx_id", "transaction_id", default="TX")
        sender = get_value(tx, "sender_account", "from_account", default="UNKNOWN_SRC")
        receiver = get_value(tx, "receiver_account", "to_account", default="UNKNOWN_DST")
        amt = get_value(tx, "amount_inr", "amount", default="0")
        try:
            amt_str = f"INR {float(amt):,.2f}"
        except Exception:
            amt_str = str(amt)
        channel = get_value(tx, "channel", default="ONLINE")
        paths.append(
            f"(:Account {{account_number: '{sender}'}})-[:SENT_TRANSACTION]->"
            f"(:Transaction {{tx_id: '{tx_id}', amount: '{amt_str}', channel: '{channel}'}})-[:TO_ACCOUNT]->"
            f"(:Account {{account_number: '{receiver}'}})"
        )

    return paths


class GraphRetriever:
    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = Path(project_root or PROJECT_ROOT)
        chunks_path = (
            self.project_root / "data" / "processed" / "chunks.json"
        )
        self.doc_retriever = DocumentRetriever(chunks_path)
        self.risk_analyzer = GraphRiskAnalyzer()
        self.answer_generator = GraphRAGAnswerGenerator()
        self.scenario_analyzer = ScenarioAnalyzer()
        self.evidence_validator = EvidenceValidator()
        self.database = "neo4j"
        self.driver = self._init_neo4j()
        self.local_graph = self._load_local_graph()
        self.query_router = QueryRouter(
            known_customer_ids=set(self.local_graph.get("customers", {}).keys())
        )

    def _init_neo4j(self):
        if GraphDatabase is None:
            print("[!] Neo4j driver missing; local fallback enabled.")
            return None

        env_file = self.project_root / ".env"
        load_dotenv(
            env_file if env_file.exists() else None,
            override=False
        )

        uri = os.getenv("NEO4J_URI", "").strip()
        username = os.getenv("NEO4J_USER", "neo4j").strip()
        password = os.getenv("NEO4J_PASSWORD", "")
        self.database = (
            os.getenv("NEO4J_DATABASE", "neo4j").strip() or "neo4j"
        )

        if not uri or not password:
            print("[!] Neo4j configuration missing; local fallback enabled.")
            return None

        try:
            driver = GraphDatabase.driver(
                uri, auth=(username, password)
            )
            driver.verify_connectivity()
            print("[+] Connected to Neo4j.")
            return driver
        except Exception as exc:
            print(f"[!] Neo4j connection failed: {exc}")
            return None

    def close(self):
        if self.driver is not None:
            self.driver.close()
            self.driver = None

    def _load_local_graph(self):
        folder = self.project_root / "data" / "synthetic"
        specs = {
            "customers": ("customers.json", ("customer_id", "id")),
            "accounts": (
                "accounts.json",
                ("account_number", "account_id", "id")
            ),
            "transactions": (
                "transactions.json",
                ("tx_id", "transaction_id", "id")
            ),
            "scenarios": (
                "scenarios.json",
                ("scenario_id", "id")
            ),
        }
        graph = {key: {} for key in specs}

        for key, (filename, id_keys) in specs.items():
            path = folder / filename
            if not path.exists():
                print(f"[!] Local file not found: {path}")
                continue

            try:
                with path.open("r", encoding="utf-8") as file:
                    rows = json.load(file)

                if not isinstance(rows, list):
                    print(f"[!] Expected a list in {filename}.")
                    continue

                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    record_id = get_value(row, *id_keys)
                    if record_id:
                        graph[key][record_id] = row

            except (OSError, json.JSONDecodeError, TypeError) as exc:
                print(f"[!] Could not load {filename}: {exc}")

        print(
            f"[+] Loaded {len(graph['customers'])} local synthetic customers."
        )
        return graph

    @staticmethod
    def customer_name(customer):
        return get_value(customer, "full_name", default="")

    def find_name_in_query(self, query: str) -> Optional[str]:
        """Find a known customer name explicitly mentioned in a query."""
        query_norm = normalize(query)
        customer_candidates = {}

        # 1. Local synthetic data
        for cid, cust in self.local_graph["customers"].items():
            raw_name = self.customer_name(cust)
            if raw_name:
                customer_candidates[cid] = raw_name

        # 2. Neo4j graph - only query existing full_name property
        if self.driver is not None:
            cypher = """
            MATCH (c:Customer)
            WHERE c.full_name IS NOT NULL
            RETURN c.customer_id AS customer_id, c.full_name AS name
            """
            try:
                with self.driver.session(database=self.database) as session:
                    for record in session.run(cypher):
                        cid = record.get("customer_id")
                        name = record.get("name")
                        if cid and name:
                            customer_candidates[str(cid)] = str(name).strip()
            except Exception as exc:
                print(f"[!] Customer-name search failed: {exc}")

        # Check for matches
        matched_cids = []
        for cid, full_name in customer_candidates.items():
            fn_norm = normalize(full_name)
            clean_norm = normalize(strip_fictional_suffix(full_name))
            if (fn_norm and fn_norm in query_norm) or (clean_norm and clean_norm in query_norm):
                matched_cids.append(cid)

        matched_cids = list(dict.fromkeys(matched_cids))

        if len(matched_cids) == 1:
            return customer_candidates[matched_cids[0]]

        if len(matched_cids) > 1:
            names = [customer_candidates[cid] for cid in matched_cids]
            print(f"[!] Multiple customer names found in query: {', '.join(names)}")

        return None

    def _neo4j_customer_exists(self, customer_id: str) -> bool:
        """Check if customer exists in Neo4j graph database."""
        if self.driver is None:
            return False
        cypher = "MATCH (c:Customer {customer_id: $customer_id}) RETURN count(c) AS cnt"
        try:
            with self.driver.session(database=self.database) as session:
                res = session.run(cypher, customer_id=customer_id).single()
                return bool(res and res["cnt"] > 0)
        except Exception:
            return False

    def resolve_customer_name(self, customer_name: str) -> Tuple[Optional[str], bool, List[str]]:
        """
        Resolve a customer name or ID safely to (customer_id, is_ambiguous, candidate_names).
        """
        target_raw = str(customer_name or "").strip()
        target_norm = normalize(target_raw)
        target_clean = normalize(strip_fictional_suffix(target_raw))

        if not target_norm:
            return None, False, []

        # Build combined candidate map: customer_id -> full_name
        customer_map = {}
        for cid, cust in self.local_graph["customers"].items():
            name = self.customer_name(cust)
            if name:
                customer_map[str(cid)] = str(name).strip()

        if self.driver is not None:
            cypher = """
            MATCH (c:Customer)
            WHERE c.full_name IS NOT NULL
            RETURN c.customer_id AS customer_id, c.full_name AS full_name
            """
            try:
                with self.driver.session(database=self.database) as session:
                    for record in session.run(cypher):
                        cid = record.get("customer_id")
                        fn = record.get("full_name")
                        if cid and fn:
                            customer_map[str(cid)] = str(fn).strip()
            except Exception as exc:
                print(f"[!] Neo4j customer lookup failed: {exc}")

        # 1. Direct ID match
        for cid in customer_map:
            if normalize(cid) == target_norm:
                return cid, False, [customer_map[cid]]

        # 2. Exact and normalized name match
        matched_cids = []
        for cid, full_name in customer_map.items():
            fn_norm = normalize(full_name)
            fn_clean = normalize(strip_fictional_suffix(full_name))

            if target_norm == fn_norm or target_clean == fn_clean or target_norm == fn_clean:
                matched_cids.append(cid)

        # 3. Fallback substring match if no exact match
        if not matched_cids:
            for cid, full_name in customer_map.items():
                fn_clean = normalize(strip_fictional_suffix(full_name))
                if target_clean and (target_clean in fn_clean or fn_clean in target_clean):
                    matched_cids.append(cid)

        matched_cids = list(dict.fromkeys(matched_cids))

        if len(matched_cids) == 1:
            return matched_cids[0], False, [customer_map[matched_cids[0]]]

        if len(matched_cids) > 1:
            names = [f"{customer_map[c]} ({c})" for c in matched_cids]
            return None, True, names

        return None, False, []

    def find_customer_by_name(self, customer_name: str) -> Optional[str]:
        """Resolve a customer name or ID safely to a unique customer ID."""
        cid, is_ambiguous, _ = self.resolve_customer_name(customer_name)
        return cid

    def find_circular_transaction_cycles(
        self, customer_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute transaction-subgraph query to detect closed cycles between linked accounts.
        Returns account IDs, transaction IDs, amounts, timestamps, and complete canonical paths.
        Calculates:
        - Cumulative Ledger Turnover (gross debit volume across cycle)
        - Net Balance Change (sum of inflows minus sum of outflows)
        - Supported Variance Against Verified Commercial Activity (turnover minus verified commercial activity)
        """
        cycles = []
        seen_keys = set()

        # 1. Live Neo4j Query
        if self.driver is not None:
            cypher = """
            MATCH (c:Customer)-[:OWNS_ACCOUNT]->(a1:Account)
            WHERE ($customer_id IS NULL OR c.customer_id = $customer_id)
            MATCH (a1)-[:SENT_TRANSACTION]->(tx1:Transaction)-[:TO_ACCOUNT]->(a2:Account)
            MATCH (a2)-[:SENT_TRANSACTION]->(tx2:Transaction)-[:TO_ACCOUNT]->(a3:Account)
            MATCH (a3)-[:SENT_TRANSACTION]->(tx3:Transaction)-[:TO_ACCOUNT]->(a1)
            WHERE a1 <> a2 AND a2 <> a3 AND a1 <> a3
            RETURN c.customer_id AS customer_id,
                   c.full_name AS customer_name,
                   a1.account_number AS acc1, a1.account_type AS acc1_type,
                   tx1.tx_id AS tx1_id, coalesce(tx1.amount, 0.0) AS tx1_amt, tx1.timestamp AS tx1_ts, tx1.channel AS tx1_channel, tx1.type AS tx1_type,
                   a2.account_number AS acc2, a2.account_type AS acc2_type,
                   tx2.tx_id AS tx2_id, coalesce(tx2.amount, 0.0) AS tx2_amt, tx2.timestamp AS tx2_ts, tx2.channel AS tx2_channel, tx2.type AS tx2_type,
                   a3.account_number AS acc3, a3.account_type AS acc3_type,
                   tx3.tx_id AS tx3_id, coalesce(tx3.amount, 0.0) AS tx3_amt, tx3.timestamp AS tx3_ts, tx3.channel AS tx3_channel, tx3.type AS tx3_type
            ORDER BY tx1.timestamp
            """
            try:
                with self.driver.session(database=self.database) as session:
                    records = session.run(cypher, customer_id=customer_id).data()

                for r in records:
                    accs = [r["acc1"], r["acc2"], r["acc3"]]
                    cycle_key = tuple(sorted(accs))
                    if cycle_key in seen_keys:
                        continue
                    # Canonical rotation: anchor at minimum account number
                    if r["acc1"] != min(accs):
                        continue
                    seen_keys.add(cycle_key)

                    amounts = [float(r["tx1_amt"]), float(r["tx2_amt"]), float(r["tx3_amt"])]
                    turnover = sum(amounts)
                    net_c1 = float(r["tx3_amt"]) - float(r["tx1_amt"])
                    net_c2 = float(r["tx1_amt"]) - float(r["tx2_amt"])
                    net_c3 = float(r["tx2_amt"]) - float(r["tx3_amt"])
                    net_total = net_c1 + net_c2 + net_c3

                    verified_comm = 0.0
                    variance = turnover - verified_comm

                    canonical_path = (
                        f"(:Account {{account_number: '{r['acc1']}'}})-[:SENT_TRANSACTION]->"
                        f"(:Transaction {{tx_id: '{r['tx1_id']}', amount: 'INR {amounts[0]:,.2f}', timestamp: '{r['tx1_ts']}'}})-[:TO_ACCOUNT]->"
                        f"(:Account {{account_number: '{r['acc2']}'}})-[:SENT_TRANSACTION]->"
                        f"(:Transaction {{tx_id: '{r['tx2_id']}', amount: 'INR {amounts[1]:,.2f}', timestamp: '{r['tx2_ts']}'}})-[:TO_ACCOUNT]->"
                        f"(:Account {{account_number: '{r['acc3']}'}})-[:SENT_TRANSACTION]->"
                        f"(:Transaction {{tx_id: '{r['tx3_id']}', amount: 'INR {amounts[2]:,.2f}', timestamp: '{r['tx3_ts']}'}})-[:TO_ACCOUNT]->"
                        f"(:Account {{account_number: '{r['acc1']}'}})"
                    )

                    cycles.append({
                        "cycle_id": f"CYCLE_{len(cycles)+1}",
                        "customer_id": r["customer_id"],
                        "customer_name": r["customer_name"],
                        "account_ids": accs,
                        "account_types": [r["acc1_type"], r["acc2_type"], r["acc3_type"]],
                        "transaction_ids": [r["tx1_id"], r["tx2_id"], r["tx3_id"]],
                        "amounts": amounts,
                        "timestamps": [r["tx1_ts"], r["tx2_ts"], r["tx3_ts"]],
                        "channels": [r["tx1_channel"], r["tx2_channel"], r["tx3_channel"]],
                        "complete_path": canonical_path,
                        "cumulative_ledger_turnover": turnover,
                        "turnover_inclusion_rule": "Sum of all debit transactions (outgoing fund movements) across participating linked accounts within the closed circular subgraph.",
                        "net_balance_change": net_total,
                        "per_account_net_change": {
                            r["acc1"]: net_c1,
                            r["acc2"]: net_c2,
                            r["acc3"]: net_c3,
                        },
                        "net_balance_inclusion_rule": "Net external capital flow into or out of the participating linked accounts combined (sum of external inflows minus sum of external outflows across the cycle).",
                        "verified_commercial_activity": verified_comm,
                        "verified_commercial_activity_rule": "Sum of transactions supported by verified third-party commercial documentation, legitimate trade invoices, or independent counterparty settlements (zero for internal circular shuffling).",
                        "supported_commercial_variance": variance,
                        "variance_rule": "Cumulative ledger turnover minus verified external commercial activity, reflecting the volume of unverified artificial velocity.",
                        "metrics_distinction_statement": (
                            f"Cumulative Ledger Turnover (INR {turnover:,.2f}), Net Balance Change (INR {net_total:,.2f}), "
                            f"and Supported Commercial Variance (INR {variance:,.2f}) represent distinct accounting dimensions and must not be equated."
                        )
                    })
                if cycles:
                    return cycles
            except Exception as exc:
                print(f"[!] Neo4j cycle detection failed: {exc}")

        # 2. Local Fallback Detection
        local_custs = [customer_id] if customer_id else list(self.local_graph.get("customers", {}).keys())
        for cid in local_custs:
            cust = self.local_graph.get("customers", {}).get(cid, {})
            c_name = cust.get("full_name", cid)
            cust_accs = {
                acc_num: acc
                for acc_num, acc in self.local_graph.get("accounts", {}).items()
                if acc.get("customer_id") == cid
            }
            if len(cust_accs) < 2:
                continue

            txs = [
                tx for tx in self.local_graph.get("transactions", {}).values()
                if tx.get("sender_account") in cust_accs and tx.get("receiver_account") in cust_accs
            ]
            tx_by_sender = {t.get("sender_account"): t for t in txs if t.get("sender_account")}

            for s1, tx1 in tx_by_sender.items():
                d1 = tx1.get("receiver_account")
                if d1 in tx_by_sender and d1 != s1:
                    tx2 = tx_by_sender[d1]
                    d2 = tx2.get("receiver_account")
                    if d2 in tx_by_sender and d2 not in (s1, d1):
                        tx3 = tx_by_sender[d2]
                        d3 = tx3.get("receiver_account")
                        if d3 == s1:
                            accs = [s1, d1, d2]
                            cycle_key = tuple(sorted(accs))
                            if cycle_key in seen_keys:
                                continue
                            seen_keys.add(cycle_key)

                            amt1 = float(tx1.get("amount_inr", tx1.get("amount", 0.0)))
                            amt2 = float(tx2.get("amount_inr", tx2.get("amount", 0.0)))
                            amt3 = float(tx3.get("amount_inr", tx3.get("amount", 0.0)))
                            amounts = [amt1, amt2, amt3]
                            turnover = sum(amounts)
                            net_c1 = amt3 - amt1
                            net_c2 = amt1 - amt2
                            net_c3 = amt2 - amt3
                            net_total = net_c1 + net_c2 + net_c3
                            variance = turnover

                            path_str = (
                                f"(:Account {{account_number: '{s1}'}})-[:SENT_TRANSACTION]->"
                                f"(:Transaction {{tx_id: '{tx1.get('tx_id')}', amount: 'INR {amt1:,.2f}', timestamp: '{tx1.get('timestamp')}'}})-[:TO_ACCOUNT]->"
                                f"(:Account {{account_number: '{d1}'}})-[:SENT_TRANSACTION]->"
                                f"(:Transaction {{tx_id: '{tx2.get('tx_id')}', amount: 'INR {amt2:,.2f}', timestamp: '{tx2.get('timestamp')}'}})-[:TO_ACCOUNT]->"
                                f"(:Account {{account_number: '{d2}'}})-[:SENT_TRANSACTION]->"
                                f"(:Transaction {{tx_id: '{tx3.get('tx_id')}', amount: 'INR {amt3:,.2f}', timestamp: '{tx3.get('timestamp')}'}})-[:TO_ACCOUNT]->"
                                f"(:Account {{account_number: '{s1}'}})"
                            )

                            cycles.append({
                                "cycle_id": f"CYCLE_{len(cycles)+1}",
                                "customer_id": cid,
                                "customer_name": c_name,
                                "account_ids": accs,
                                "account_types": [
                                    cust_accs.get(s1, {}).get("account_type", "CURRENT"),
                                    cust_accs.get(d1, {}).get("account_type", "CURRENT"),
                                    cust_accs.get(d2, {}).get("account_type", "CURRENT")
                                ],
                                "transaction_ids": [tx1.get("tx_id"), tx2.get("tx_id"), tx3.get("tx_id")],
                                "amounts": amounts,
                                "timestamps": [tx1.get("timestamp"), tx2.get("timestamp"), tx3.get("timestamp")],
                                "channels": [tx1.get("channel", "RTGS"), tx2.get("channel", "RTGS"), tx3.get("channel", "RTGS")],
                                "complete_path": path_str,
                                "cumulative_ledger_turnover": turnover,
                                "turnover_inclusion_rule": "Sum of all debit transactions (outgoing fund movements) across participating linked accounts within the closed circular subgraph.",
                                "net_balance_change": net_total,
                                "per_account_net_change": {s1: net_c1, d1: net_c2, d2: net_c3},
                                "net_balance_inclusion_rule": "Net external capital flow into or out of the participating linked accounts combined (sum of external inflows minus sum of external outflows across the cycle).",
                                "verified_commercial_activity": 0.0,
                                "verified_commercial_activity_rule": "Sum of transactions supported by verified third-party commercial documentation, legitimate trade invoices, or independent counterparty settlements (zero for internal circular shuffling).",
                                "supported_commercial_variance": variance,
                                "variance_rule": "Cumulative ledger turnover minus verified external commercial activity, reflecting the volume of unverified artificial velocity.",
                                "metrics_distinction_statement": (
                                    f"Cumulative Ledger Turnover (INR {turnover:,.2f}), Net Balance Change (INR {net_total:,.2f}), "
                                    f"and Supported Commercial Variance (INR {variance:,.2f}) represent distinct accounting dimensions and must not be equated."
                                )
                            })
        return cycles

    def trace_customer_risk_graph(
        self, customer_id: str
    ) -> Dict[str, Any]:
        """Retrieve customer, accounts, transactions and risk patterns."""
        if self.driver is not None:
            cypher = """
            MATCH (c:Customer {customer_id: $customer_id})
            OPTIONAL MATCH (c)-[:OWNS_ACCOUNT]->(a:Account)
            OPTIONAL MATCH (src:Account)-[:SENT_TRANSACTION]->(tx:Transaction)-[:TO_ACCOUNT]->(dst:Account)
            WHERE (c)-[:OWNS_ACCOUNT]->(src) OR (c)-[:OWNS_ACCOUNT]->(dst)
            OPTIONAL MATCH (tx)-[:TRIGGERS_INDICATOR]->(r:RiskIndicator)
            OPTIONAL MATCH (c)-[:EXHIBITS_PATTERN]->(f:FraudPattern)
            RETURN c,
                   collect(DISTINCT a) AS accounts,
                   collect(DISTINCT {
                       tx: tx,
                       sender_account: src.account_number,
                       receiver_account: dst.account_number
                   }) AS tx_records,
                   collect(DISTINCT r) AS indicators,
                   collect(DISTINCT f) AS patterns
            """

            try:
                with self.driver.session(
                    database=self.database
                ) as session:
                    record = session.run(
                        cypher, customer_id=customer_id
                    ).single()

                if record is not None and record["c"] is not None:
                    def unique_properties(items, keys):
                        result = {}
                        for item in items:
                            if item is None:
                                continue
                            properties = dict(item)
                            key = get_value(
                                properties, *keys,
                                default=str(properties)
                            )
                            result[key] = properties
                        return list(result.values())

                    accounts = unique_properties(
                        record["accounts"],
                        ("account_number", "account_id")
                    )
                    cust_account_nums = {
                        get_value(acc, "account_number", "account_id")
                        for acc in accounts
                    } - {""}

                    # Parse transactions with explicit sender/receiver relationships
                    tx_map = {}
                    for item in record["tx_records"]:
                        if not item or not item.get("tx"):
                            continue
                        tx_props = dict(item["tx"])
                        tx_id = get_value(tx_props, "tx_id", "transaction_id", default=str(tx_props))
                        tx_props["sender_account"] = item.get("sender_account") or get_value(tx_props, "sender_account", default="not available")
                        tx_props["receiver_account"] = item.get("receiver_account") or get_value(tx_props, "receiver_account", default="not available")
                        
                        if tx_props["sender_account"] in cust_account_nums:
                            tx_props["direction"] = "OUTGOING"
                        elif tx_props["receiver_account"] in cust_account_nums:
                            tx_props["direction"] = "INCOMING"
                        else:
                            tx_props["direction"] = tx_props.get("type", "UNKNOWN")

                        tx_map[tx_id] = tx_props

                    cust_dict = dict(record["c"])
                    tx_list = list(tx_map.values())
                    calc_risks = self.risk_analyzer.analyze_customer_risk(
                        cust_dict, accounts, tx_list
                    )
                    patterns = unique_properties(
                        record["patterns"],
                        ("pattern_id", "name")
                    )

                    graph_paths = _build_graph_paths(cust_dict, accounts, tx_list)
                    cycles = self.find_circular_transaction_cycles(customer_id)
                    for c in cycles:
                        if c.get("complete_path"):
                            cycle_entry = f"[CIRCULAR_FLOW_CYCLE]: {c['complete_path']}"
                            if cycle_entry not in graph_paths:
                                graph_paths.insert(0, cycle_entry)
                    return {
                        "source": "Neo4j_Live_Graph",
                        "customer": cust_dict,
                        "accounts": accounts,
                        "transactions": tx_list,
                        "graph_paths": graph_paths,
                        "circular_cycles": cycles,
                        "risk_indicators": unique_properties(
                            record["indicators"],
                            ("indicator_id", "name")
                        ),
                        "calculated_risks": calc_risks,
                        "fraud_pattern": (
                            patterns[0] if patterns else None
                        ),
                        "fraud_patterns": patterns,
                    }

                print(
                    f"[!] Customer {customer_id} not found in Neo4j; "
                    "trying local data."
                )

            except Exception as exc:
                print(f"[!] Neo4j graph query failed: {exc}")
                print("[!] Trying local synthetic data.")

        customer = self.local_graph["customers"].get(customer_id)

        if customer is None:
            return {
                "source": "Local_Graph_Index",
                "customer": None,
                "error": (
                    f"Customer '{customer_id}' was not found in "
                    "Neo4j or local synthetic data."
                ),
            }

        accounts = [
            account
            for account in self.local_graph["accounts"].values()
            if get_value(
                account, "customer_id", "owner_customer_id"
            ) == customer_id
        ]

        account_ids = {
            get_value(
                account, "account_number", "account_id", "account_no"
            )
            for account in accounts
        } - {""}

        transactions = []
        for transaction in self.local_graph["transactions"].values():
            sender = get_value(
                transaction, "sender_account", "from_account",
                "source_account"
            )
            receiver = get_value(
                transaction, "receiver_account", "to_account",
                "target_account"
            )
            if sender in account_ids or receiver in account_ids:
                tx_copy = dict(transaction)
                if sender in account_ids:
                    tx_copy["direction"] = "OUTGOING"
                elif receiver in account_ids:
                    tx_copy["direction"] = "INCOMING"
                else:
                    tx_copy["direction"] = tx_copy.get("type", "UNKNOWN")
                transactions.append(tx_copy)

        indicators = list(dict.fromkeys(
            transaction["risk_indicator"]
            for transaction in transactions
            if transaction.get("risk_indicator")
        ))

        scenario_id = get_value(
            customer, "flagged_scenario", "scenario_id"
        )
        scenario = self.local_graph["scenarios"].get(scenario_id)

        calc_risks = self.risk_analyzer.analyze_customer_risk(
            customer, accounts, transactions
        )
        graph_paths = _build_graph_paths(customer, accounts, transactions)
        cycles = self.find_circular_transaction_cycles(customer_id)
        for c in cycles:
            if c.get("complete_path"):
                cycle_entry = f"[CIRCULAR_FLOW_CYCLE]: {c['complete_path']}"
                if cycle_entry not in graph_paths:
                    graph_paths.insert(0, cycle_entry)

        return {
            "source": "Local_Graph_Index",
            "customer": customer,
            "accounts": accounts,
            "transactions": transactions,
            "graph_paths": graph_paths,
            "circular_cycles": cycles,
            "risk_indicators": indicators,
            "calculated_risks": calc_risks,
            "fraud_pattern": scenario,
            "fraud_patterns": [scenario] if scenario else [],
        }

    def generate_answer(self, context: Dict[str, Any]) -> str:
        """Generate a grounded, verifiable GraphRAG compliance intelligence answer."""
        prompt = self.format_llm_prompt(context)
        return self.answer_generator.generate_answer(context, prompt)

    def execute_unified_query(
        self,
        query: str,
        session: Optional[UserSession] = None,
        explicit_customer_id: Optional[str] = None,
        explicit_customer_name: Optional[str] = None,
        top_k: int = 3,
        document_filter: Optional[str] = None,
        section_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Unified multi-modal query execution engine.
        Enforces access control (Mode A: Public, Mode B: Customer, Mode C: Officer),
        tenant boundary isolation, dynamic graph tracing, and grounded synthesis.
        Guarantees:
        - Generic queries never select arbitrary customers.
        - Hypothetical scenarios never present assumptions as database facts.
        - Unknown customer IDs return safe, clear notifications.
        - Ambiguous customer names prompt for clarification.
        - Cross-customer comparisons retrieve both profiles independently.
        """
        user_sess = session or UserSession.public_session()
        resolved_cust_id = None

        # 1. Explicit Customer ID Validation
        if explicit_customer_id:
            target_id = explicit_customer_id.strip()
            exists = (target_id in self.local_graph.get("customers", {}))
            if not exists and self.driver is not None:
                exists = self._neo4j_customer_exists(target_id)
            if not exists:
                docs = self.doc_retriever.search(query, top_k=top_k)
                return {
                    "query": query,
                    "session": user_sess,
                    "customer_not_found": True,
                    "customer_id": target_id,
                    "access_denied": False,
                    "answer": (
                        f"### ⚠️ Customer Profile Not Found\n\n"
                        f"Customer ID `{target_id}` was not found in knowledge graph records or synthetic customer profiles.\n\n"
                        "**Investigative Guidance:**\n"
                        "- Verify the customer identifier (e.g. `CUST_SYNTH_101` through `CUST_SYNTH_107`).\n"
                        "- Confirm whether the account has been onboarded and ingested into the Neo4j database.\n"
                        "- Check for typographical errors in the entity identifier."
                    ),
                    "document_evidence": docs,
                    "graph_context": {"error": f"Customer '{target_id}' was not found in Neo4j or local synthetic data."},
                }
            resolved_cust_id = target_id

        # 2. Explicit Customer Name Validation & Resolution
        elif explicit_customer_name:
            cid, is_ambiguous, candidates = self.resolve_customer_name(explicit_customer_name)
            if is_ambiguous:
                return {
                    "query": query,
                    "session": user_sess,
                    "needs_clarification": True,
                    "access_denied": False,
                    "answer": (
                        f"### ℹ️ Ambiguous Customer Name\n\n"
                        f"Multiple customer records match '{explicit_customer_name}':\n" +
                        "\n".join([f"- {c}" for c in candidates]) +
                        "\n\nPlease specify the unique Customer ID (e.g. `CUST_SYNTH_101`) to inspect records."
                    ),
                    "document_evidence": [],
                    "graph_context": {},
                }
            elif not cid:
                docs = self.doc_retriever.search(query, top_k=top_k)
                return {
                    "query": query,
                    "session": user_sess,
                    "customer_not_found": True,
                    "customer_name": explicit_customer_name,
                    "access_denied": False,
                    "answer": (
                        f"### ⚠️ Customer Not Found\n\n"
                        f"No customer profile matching '{explicit_customer_name}' was found in knowledge graph records."
                    ),
                    "document_evidence": docs,
                    "graph_context": {"error": f"Customer '{explicit_customer_name}' was not found."},
                }
            resolved_cust_id = cid

        # 3. Pre-analyze scenario for parameter extraction
        pre_analysis = self.scenario_analyzer.analyze(query, context={"customer_id": resolved_cust_id})
        decision = self.query_router.route(
            query=query,
            session=user_sess,
            explicit_customer_id=resolved_cust_id,
        )

        # 4. Access Denial Enforcement
        if not decision.access_granted:
            return {
                "query": query,
                "session": user_sess,
                "routing_decision": decision,
                "access_denied": True,
                "answer": f"### ⛔ Access Denied\n\n{decision.denial_reason}",
                "document_evidence": [],
                "graph_context": {},
            }

        # 5. Clarification Handling
        if decision.needs_clarification and decision.clarification_message:
            return {
                "query": query,
                "session": user_sess,
                "routing_decision": decision,
                "access_denied": False,
                "needs_clarification": True,
                "answer": f"### ℹ️ Clarification Needed\n\n{decision.clarification_message}",
                "document_evidence": [],
                "graph_context": {},
            }

        # 6. Category D: Cross-Customer Comparison Dispatch
        if decision.intent == QueryIntent.CROSS_CUSTOMER_COMPARISON or pre_analysis.is_comparison:
            cids = decision.comparison_customer_ids or pre_analysis.comparison_customer_ids
            comparison_graphs = {}
            for cid in cids:
                comparison_graphs[cid] = self.trace_customer_risk_graph(cid)

            docs = self.doc_retriever.search(query, top_k=top_k, document_filter=document_filter, section_filter=section_filter)
            context = {
                "query": query,
                "session": user_sess,
                "routing_decision": decision,
                "intent": QueryIntent.CROSS_CUSTOMER_COMPARISON,
                "comparison_customer_ids": cids,
                "comparison_graphs": comparison_graphs,
                "document_evidence": docs,
                "graph_context": comparison_graphs.get(cids[0], {}) if cids else {},
                "scenario_analysis": pre_analysis,
                "access_denied": False,
            }
            answer = self.generate_answer(context)
            context["answer"] = answer
            return context

        # 7. Category C: Hypothetical Scenario Dispatch
        if decision.intent == QueryIntent.HYPOTHETICAL_SCENARIO or pre_analysis.is_hypothetical_scenario:
            docs = self.doc_retriever.search(query, top_k=top_k, document_filter=document_filter, section_filter=section_filter)
            context = {
                "query": query,
                "session": user_sess,
                "routing_decision": decision,
                "intent": QueryIntent.HYPOTHETICAL_SCENARIO,
                "is_hypothetical_scenario": True,
                "document_evidence": docs,
                "graph_context": {},
                "scenario_analysis": pre_analysis,
                "claim_validations": self.evidence_validator.validate_scenario_claims(query, docs, pre_analysis),
                "access_denied": False,
            }
            answer = self.generate_answer(context)
            context["answer"] = answer
            return context

        # 8. Determine Target Customer Graph Scope (Single-Customer Path)
        target_cust_id = None
        if decision.intent in {QueryIntent.CUSTOMER_INFORMATION, QueryIntent.RISK_INVESTIGATION}:
            target_cust_id = decision.target_customer_id or resolved_cust_id
            if not target_cust_id and user_sess.role in (UserRole.OFFICER, UserRole.COMPLIANCE_OFFICER):
                detected_name = self.find_name_in_query(query)
                if detected_name:
                    target_cust_id = self.find_customer_by_name(detected_name)
                elif pre_analysis.customer_id and (
                    pre_analysis.customer_id in query or
                    (pre_analysis.customer_name and pre_analysis.customer_name.lower() in query.lower())
                ):
                    target_cust_id = pre_analysis.customer_id
        elif decision.intent == QueryIntent.MIXED_QUERY:
            if user_sess.is_authenticated:
                target_cust_id = decision.target_customer_id or resolved_cust_id
            else:
                target_cust_id = None
        elif decision.intent in {QueryIntent.GENERAL_KNOWLEDGE, QueryIntent.REGULATORY_QUERY}:
            target_cust_id = None

        # 9. Search and Evidence Retrieval
        search_query = decision.public_subquery if (decision.intent == QueryIntent.MIXED_QUERY and decision.public_subquery) else query
        context = self.retrieve_hybrid_context(
            query=search_query,
            customer_id=target_cust_id,
            top_chunks=top_k,
            document_filter=document_filter,
            section_filter=section_filter,
        )

        context["query"] = query  # Preserve exact original query
        context["session"] = user_sess
        context["routing_decision"] = decision
        context["intent"] = decision.intent
        context["access_denied"] = False
        if "scenario_analysis" not in context or not context["scenario_analysis"]:
            context["scenario_analysis"] = pre_analysis

        # 10. Generate Grounded Synthesis
        answer = self.generate_answer(context)
        context["answer"] = answer
        return context

    def retrieve_hybrid_context(
        self,
        query: str,
        customer_id: Optional[str] = None,
        top_chunks: int = 3,
        top_k: Optional[int] = None,
        document_filter: Optional[str] = None,
        section_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        k = top_k if top_k is not None else top_chunks
        clean_query = str(query or "").strip()
        documents = self.doc_retriever.search(
            clean_query,
            top_k=max(1, k),
            document_filter=document_filter,
            section_filter=section_filter
        )
        graph = (
            self.trace_customer_risk_graph(customer_id)
            if customer_id else {}
        )
        scenario_analysis = self.scenario_analyzer.analyze(
            clean_query,
            context={"customer_id": customer_id, "graph_context": graph}
        )
        claim_validations = self.evidence_validator.validate_scenario_claims(
            query=clean_query,
            retrieved_documents=documents,
            scenario_analysis=scenario_analysis
        )
        return {
            "query": clean_query,
            "retrieval_mode": "Hybrid_GraphRAG",
            "document_evidence": documents,
            "graph_context": graph,
            "scenario_analysis": scenario_analysis,
            "claim_validations": claim_validations,
        }

    # Aliases for UI and test compatibility
    build_query_context = retrieve_hybrid_context

    def format_llm_prompt(self, context: Dict[str, Any]) -> str:
        """Prepare grounded evidence for an LLM; no LLM call is made."""
        query = context.get("query", "")
        documents = context.get("document_evidence", [])
        graph = context.get("graph_context", {})

        lines = [
            "=" * 80,
            "SYSTEM PROMPT: GraphRAG Banking Compliance & Risk Intelligence",
            "=" * 80,
            "You are a Banking Compliance and Risk Intelligence Assistant.",
            "Instructions:",
            "1. Ground regulatory claims only in supplied evidence.",
            "2. Label customer graph records as synthetic test data.",
            "3. Cite document name, section and page when available.",
            "4. Risk indicators are signals for investigation, not proof of fraud.",
            "5. Separate stored facts, regulations and inferences.",
            "6. State clearly when information is missing.",
            "",
            f"USER INQUIRY: {query}",
            "",
            "--- PART A: REGULATORY DOCUMENT EVIDENCE ---",
        ]

        if not documents:
            lines.append("No regulatory document chunks were retrieved.")

        for index, document in enumerate(documents, start=1):
            lines.extend([
                f"[{index}] Citation: {document.get('citation', 'Unknown')}",
                "BM25 score (not a confidence probability): "
                + str(document.get("score", "not provided")),
                "Evidence: "
                + str(document.get("text", document.get("snippet", ""))),
                "",
            ])

        lines.append(
            "--- PART B: CUSTOMER GRAPH EVIDENCE (SYNTHETIC TEST DATA) ---"
        )

        if not graph:
            lines.append("No customer-specific graph evidence was retrieved.")
        elif graph.get("error"):
            lines.append("Graph retrieval issue: " + graph["error"])
        else:
            customer = graph.get("customer") or {}
            pattern = graph.get("fraud_pattern") or {}

            lines.extend([
                f"Graph source: {graph.get('source', 'unknown')}",
                "Customer ID: "
                + get_value(customer, "customer_id", default="unknown"),
                "Customer name: "
                + (self.customer_name(customer) or "unknown"),
                "KYC / CDD status: "
                + get_value(
                    customer, "kyc_status", "kyc_status_label",
                    default="unknown"
                ),
                "Recorded risk rating: "
                + get_value(
                    customer, "risk_rating", "risk_level",
                    default="unknown"
                ),
                "Recorded typology: "
                + get_value(
                    pattern, "name", "typology",
                    default="none retrieved"
                ),
                "Typology description: "
                + get_value(
                    pattern, "description", "details",
                    default="not available"
                ),
            ])

            calc_risks = graph.get("calculated_risks") or []
            if calc_risks:
                lines.append(f"Dynamically calculated risk signals ({len(calc_risks)}):")
                for r in calc_risks:
                    lines.append(
                        f" - [{r.get('severity')}] {r.get('name')}: {r.get('calculation_details')} "
                        f"(Supporting tx: {', '.join(r.get('supporting_transactions', []))})"
                    )

            lines.extend([
                "Risk indicators: "
                + json.dumps(
                    graph.get("risk_indicators", []),
                    ensure_ascii=False,
                    default=str
                ),
                f"Linked accounts ({len(graph.get('accounts', []))}):",
            ])

            for account in graph.get("accounts", [])[:20]:
                lines.append(
                    " - Account: "
                    + get_value(
                        account, "account_number", "account_id",
                        "account_no", default="unknown"
                    )
                    + " | Type: "
                    + get_value(
                        account, "account_type", "type",
                        default="unknown"
                    )
                    + " | Status: "
                    + get_value(
                        account, "status", "account_status",
                        default="unknown"
                    )
                )

            lines.append(
                f"Associated transactions "
                f"({len(graph.get('transactions', []))}):"
            )

            for transaction in graph.get("transactions", [])[:20]:
                lines.append(
                    " - Transaction: "
                    + get_value(
                        transaction, "tx_id", "transaction_id",
                        default="unknown"
                    )
                    + " | Amount: "
                    + get_value(
                        transaction, "amount_inr", "amount",
                        default="unknown"
                    )
                    + " "
                    + get_value(transaction, "currency", default="INR")
                    + " | Channel: "
                    + get_value(transaction, "channel", default="unknown")
                    + " | Type/direction: "
                    + get_value(
                        transaction, "type", "direction",
                        "transaction_type", default="unknown"
                    )
                    + " | Timestamp: "
                    + get_value(
                        transaction, "timestamp", "transaction_date",
                        default="unknown"
                    )
                    + " | Sender: "
                    + get_value(
                        transaction, "sender_account", "from_account",
                        default="not available"
                    )
                    + " | Receiver: "
                    + get_value(
                        transaction, "receiver_account", "to_account",
                        default="not available"
                    )
                )

        lines.extend([
            "",
            "=" * 80,
            "SYNTHESIS OBJECTIVE",
            "Answer using only supplied evidence. Explain risks plainly, cite sources,",
            "identify missing information, and do not invent facts or infer guilt.",
            "=" * 80,
        ])
        return "\n".join(lines)

    build_investigation_prompt = format_llm_prompt


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Hybrid GraphRAG banking compliance retriever."
    )
    parser.add_argument("--query", type=str, default=(
        "Which transactions require enhanced due diligence under applicable rules?"
    ))
    parser.add_argument(
        "--customer-id", type=str, default=None,
        help="Explicit customer ID to trace"
    )
    parser.add_argument(
        "--customer-name", type=str, default=None,
        help="Explicit customer name to resolve"
    )
    parser.add_argument(
        "--prompt-only", action="store_true",
        help="Print evidence prompt; does not call an LLM"
    )
    parser.add_argument(
        "--top-k", type=int, default=3,
        help="Number of regulatory chunks to retrieve"
    )
    parser.add_argument(
        "--document-filter", type=str, default=None,
        help="Filter chunks by document filename"
    )
    parser.add_argument(
        "--section-filter", type=str, default=None,
        help="Filter chunks by section heading"
    )
    parser.add_argument(
        "--role", type=str, choices=["public", "customer", "officer"], default=None,
        help="Access role: public (Mode A), customer (Mode B), or officer (Mode C). Inferred if omitted."
    )
    parser.add_argument(
        "--summary-only", action="store_true",
        help="Display metrics and evidence summary only without generating final report"
    )
    args = parser.parse_args()

    if args.top_k < 1:
        parser.error("--top-k must be at least 1")

    retriever = GraphRetriever()

    try:
        customer_id = args.customer_id
        customer_name = args.customer_name

        if not customer_id and not customer_name:
            customer_name = retriever.find_name_in_query(args.query)
            if customer_name:
                print(
                    "[+] Customer name detected in query: "
                    + customer_name
                )

        if not customer_id and customer_name:
            customer_id = retriever.find_customer_by_name(customer_name)
            if not customer_id:
                print(
                    f"[!] Could not uniquely find customer: {customer_name}"
                )
                print(
                    "[!] Check customer names and IDs in "
                    "data/synthetic/customers.json and Neo4j."
                )
            else:
                print(f"[+] Customer matched: {customer_id}")

        # Resolve User Session Role
        if args.role == "public":
            session = UserSession.public_session()
        elif args.role == "customer":
            session = UserSession.customer_session(
                customer_id=customer_id or "CUST_SYNTH_101",
                customer_name=customer_name or "Arjun Sharma"
            )
        elif args.role == "officer":
            session = UserSession.officer_session(
                officer_id="OFF_CLI_01",
                department="Financial Crime Compliance"
            )
        else:
            # Inferred role: officer if customer is targeted, else public
            if customer_id or customer_name:
                session = UserSession.officer_session(officer_id="OFF_CLI_01")
            else:
                session = UserSession.public_session()

        context = retriever.execute_unified_query(
            query=args.query,
            session=session,
            explicit_customer_id=customer_id,
            explicit_customer_name=customer_name,
            top_k=args.top_k,
            document_filter=args.document_filter,
            section_filter=args.section_filter,
        )

        if args.prompt_only:
            print(retriever.format_llm_prompt(context))
            return 0

        print(f"\n[*] Query: {args.query}")
        print(f"[*] Access Role: {session.role.name} | Intent: {context.get('routing_decision').intent.name if context.get('routing_decision') else 'N/A'}")
        documents = context.get("document_evidence", [])
        print(f"[*] Retrieved {len(documents)} regulatory chunks.")

        for document in documents:
            print(
                " - "
                + document.get("citation", "Source metadata unavailable")
            )

        graph = context.get("graph_context", {})

        if not graph:
            print("[*] No customer-specific graph context selected.")
            if session.role == UserRole.OFFICER:
                print(
                    "[*] Include a customer name or use "
                    "--customer-name/--customer-id."
                )
        elif graph.get("error"):
            print("[!] Graph retrieval: " + graph["error"])
            return 1
        else:
            customer = graph.get("customer") or {}
            pattern = graph.get("fraud_pattern") or {}
            calc_risks = graph.get("calculated_risks") or []

            print("[*] Graph source: " + graph.get("source", "unknown"))
            print(
                "    Customer: "
                + (retriever.customer_name(customer) or "unknown")
            )
            print(
                "    Risk rating: "
                + get_value(
                    customer, "risk_rating", "risk_level",
                    default="unknown"
                )
            )
            print("    Accounts: " + str(len(graph.get("accounts", []))))
            print(
                "    Transactions: "
                + str(len(graph.get("transactions", [])))
            )
            print(
                "    Recorded typology: "
                + get_value(
                    pattern, "name", "typology",
                    default="none retrieved"
                )
            )
            print(f"    Calculated risk signals ({len(calc_risks)}):")
            for r in calc_risks:
                print(f"      * [{r.get('severity')}] {r.get('name')}: {r.get('calculation_details')}")

        if args.summary_only:
            return 0

        print("\n" + "=" * 80)
        report_title = (
            "FINAL GROUNDED COMPLIANCE REPORT (GraphRAG Answer Generation)"
            if session.role == UserRole.OFFICER
            else "BANKING INTELLIGENCE ADVISORY (GraphRAG Public Assistant)"
        )
        print(report_title)
        print("=" * 80 + "\n")
        print(context.get("answer", ""))
        return 0

    finally:
        retriever.close()


if __name__ == "__main__":
    raise SystemExit(main())
