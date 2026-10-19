import sys
import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

from neo4j import GraphDatabase

uri = os.getenv("NEO4J_URI")
user = os.getenv("NEO4J_USER", "neo4j")
pwd = os.getenv("NEO4J_PASSWORD")

driver = GraphDatabase.driver(uri, auth=(user, pwd))

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
       tx1.tx_id AS tx1_id, coalesce(tx1.amount, tx1.amount_inr, 0.0) AS tx1_amt, tx1.timestamp AS tx1_ts, tx1.channel AS tx1_channel, tx1.type AS tx1_type,
       a2.account_number AS acc2, a2.account_type AS acc2_type,
       tx2.tx_id AS tx2_id, coalesce(tx2.amount, tx2.amount_inr, 0.0) AS tx2_amt, tx2.timestamp AS tx2_ts, tx2.channel AS tx2_channel, tx2.type AS tx2_type,
       a3.account_number AS acc3, a3.account_type AS acc3_type,
       tx3.tx_id AS tx3_id, coalesce(tx3.amount, tx3.amount_inr, 0.0) AS tx3_amt, tx3.timestamp AS tx3_ts, tx3.channel AS tx3_channel, tx3.type AS tx3_type
ORDER BY tx1.timestamp
"""

with driver.session() as s:
    records = s.run(cypher, customer_id="CUST_SYNTH_106").data()

print(f"Returned raw records: {len(records)}")

seen_cycles = set()
canonical_cycles = []

for r in records:
    accs = [r["acc1"], r["acc2"], r["acc3"]]
    cycle_key = tuple(sorted(accs))
    if cycle_key in seen_cycles:
        continue
    # Pick the canonical rotation where acc1 is the minimum account number
    min_acc = min(accs)
    if r["acc1"] != min_acc:
        continue
    seen_cycles.add(cycle_key)

    amounts = [float(r["tx1_amt"]), float(r["tx2_amt"]), float(r["tx3_amt"])]
    turnover = sum(amounts)
    net_change_acc1 = float(r["tx3_amt"]) - float(r["tx1_amt"])
    net_change_acc2 = float(r["tx1_amt"]) - float(r["tx2_amt"])
    net_change_acc3 = float(r["tx2_amt"]) - float(r["tx3_amt"])
    net_change_total = net_change_acc1 + net_change_acc2 + net_change_acc3

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

    cycle_data = {
        "cycle_id": f"CYCLE_{len(canonical_cycles)+1}",
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
        "net_balance_change": net_change_total,
        "per_account_net_change": {
            r["acc1"]: net_change_acc1,
            r["acc2"]: net_change_acc2,
            r["acc3"]: net_change_acc3
        },
        "net_balance_inclusion_rule": "Net external capital flow into or out of the participating linked accounts combined (sum of external inflows minus sum of external outflows across the cycle).",
        "verified_commercial_activity": verified_comm,
        "verified_commercial_activity_rule": "Sum of transactions supported by verified third-party commercial documentation, legitimate trade invoices, or independent counterparty settlements (zero for internal circular shuffling).",
        "supported_commercial_variance": variance,
        "variance_rule": "Cumulative ledger turnover minus verified external commercial activity, reflecting the volume of unverified artificial velocity.",
        "metrics_distinction_statement": f"Cumulative Ledger Turnover (INR {turnover:,.2f}), Net Balance Change (INR {net_change_total:,.2f}), and Supported Commercial Variance (INR {variance:,.2f}) represent distinct accounting dimensions and must not be equated."
    }
    canonical_cycles.append(cycle_data)

print(f"\nCanonical cycles: {len(canonical_cycles)}")
import pprint
pprint.pprint(canonical_cycles[0])

driver.close()
