
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

uri = os.getenv("NEO4J_URI")
user = os.getenv("NEO4J_USER")
password = os.getenv("NEO4J_PASSWORD")
database = os.getenv("NEO4J_DATABASE", "neo4j")

if not all([uri, user, password]):
    raise ValueError(
        "Missing NEO4J_URI, NEO4J_USER, or NEO4J_PASSWORD in .env"
    )

try:
    with GraphDatabase.driver(
        uri, auth=(user, password)
    ) as driver:
        driver.verify_connectivity()
        print("SUCCESS: Connected to Neo4j Sandbox!")

        with driver.session(database=database) as session:
            result = session.run(
                "RETURN 1 AS test, 'Connection working' AS message"
            )
            print(result.single().data())

except Exception as error:
    print("CONNECTION FAILED")
    print(type(error).__name__, str(error))

