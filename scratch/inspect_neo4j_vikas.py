import os
import sys
from pathlib import Path
from dotenv import load_dotenv

project_root = Path(r"C:\Users\Shreeya B. Kulkarni\Desktop\DBms_project")
load_dotenv(project_root / ".env")

from neo4j import GraphDatabase

uri = os.getenv("NEO4J_URI")
user = os.getenv("NEO4J_USER", "neo4j")
pwd = os.getenv("NEO4J_PASSWORD")

print(f"Connecting to {uri} as {user}...")
driver = GraphDatabase.driver(uri, auth=(user, pwd))
with driver.session() as s:
    # 1. Inspect Customer 106 and accounts
    q1 = """
    MATCH (c:Customer {customer_id: 'CUST_SYNTH_106'})
    OPTIONAL MATCH (c)-[:OWNS_ACCOUNT]->(a:Account)
    RETURN c.customer_id as cid, c.full_name as name, c.declared_annual_income as inc,
           collect(a.account_number) as accounts, collect(a.account_type) as types, collect(a.current_balance) as balances
    """
    res1 = s.run(q1).data()
    print("Customer 106:", res1)

    # 2. Inspect transactions between these accounts
    q2 = """
    MATCH (c:Customer {customer_id: 'CUST_SYNTH_106'})-[:OWNS_ACCOUNT]->(src:Account)
    MATCH (src)-[:SENT_TRANSACTION]->(tx:Transaction)-[:TO_ACCOUNT]->(dst:Account)
    RETURN src.account_number as src_acc, tx.tx_id as tx_id, tx.amount_inr as amount, tx.timestamp as timestamp,
           tx.channel as channel, tx.risk_indicator as risk_indicator, dst.account_number as dst_acc
    ORDER BY tx.timestamp
    """
    res2 = s.run(q2).data()
    print(f"\nTransactions ({len(res2)}):")
    for r in res2:
        print(r)

    # 3. Test cycle Cypher query
    q_cycle = """
    MATCH (c:Customer {customer_id: 'CUST_SYNTH_106'})-[:OWNS_ACCOUNT]->(a1:Account)
    MATCH path = (a1)-[:SENT_TRANSACTION]->(:Transaction)-[:TO_ACCOUNT]->(:Account)-[:SENT_TRANSACTION]->(:Transaction)-[:TO_ACCOUNT]->(:Account)-[:SENT_TRANSACTION]->(:Transaction)-[:TO_ACCOUNT]->(a1)
    RETURN path
    """
    res_cycle = s.run(q_cycle).data()
    print(f"\nCycle paths count: {len(res_cycle)}")
    for r in res_cycle:
        print(r)

driver.close()
