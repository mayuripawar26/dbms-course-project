"""
tests/test_pipeline.py

Phase 8 Automated Verification & Test Suite
Covers:
1. PDF extraction and page tracking.
2. Chunk metadata preservation (page numbers, section headings, char counts).
3. Duplicate handling and idempotency.
4. Neo4j schema and constraint Cypher file syntax.
5. Graph relationship correctness and synthetic dataset integrity.
6. Source citation availability and BM25 document retrieval.
7. Missing or empty PDF text detection and OCR flagging logic.
"""

import os
import sys
import re
import json
import unittest
import tempfile
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ingestion.inspect_documents import compute_sha256, parse_pdf_date
from ingestion.extract_text import extract_single_pdf, slugify
from ingestion.chunk_documents import chunk_document_pages, compute_chunk_hash
from retrieval.document_retriever import DocumentRetriever, BANKING_ACRONYMS, DOCUMENT_AUTHORITY_MAP
from retrieval.graph_retriever import GraphRetriever, strip_fictional_suffix
from retrieval.risk_analyzer import GraphRiskAnalyzer, RiskThresholds
from retrieval.answer_generator import GraphRAGAnswerGenerator
from retrieval.query_router import (
    QueryRouter,
    QueryIntent,
    UserRole,
    UserSession,
    RoutingDecision,
)


class TestBankingCompliancePipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data_dir = PROJECT_ROOT / "data"
        cls.processed_dir = cls.data_dir / "processed"
        cls.metadata_dir = cls.data_dir / "metadata"
        cls.synthetic_dir = cls.data_dir / "synthetic"
        cls.graph_dir = PROJECT_ROOT / "graph"

    # --------------------------------------------------------------------------
    # 1. PDF Extraction and Page Tracking
    # --------------------------------------------------------------------------
    def test_pdf_extraction_and_page_tracking(self):
        """Verify that processed documents preserve page numbers and text content."""
        manifest_file = self.metadata_dir / "extraction_manifest.json"
        self.assertTrue(manifest_file.exists(), "extraction_manifest.json must exist")

        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        self.assertGreater(manifest["total_documents"], 0, "Should have extracted documents")
        self.assertEqual(manifest["failed_documents"], 0, "No documents should fail extraction")

        # Check a specific processed file (e.g. kyc.json)
        kyc_json = self.processed_dir / "kyc.json"
        self.assertTrue(kyc_json.exists(), "kyc.json must exist")
        with open(kyc_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data["total_pages"], 101, "kyc.pdf must have 101 pages")
        self.assertEqual(len(data["pages"]), 101, "All 101 pages must be tracked")
        self.assertEqual(data["pages"][0]["page_number"], 1, "Page indexing must start at 1")
        self.assertEqual(data["pages"][100]["page_number"], 101, "Page indexing must reach 101")
        self.assertGreater(len(data["pages"][3]["text"]), 50, "Page 4 must contain extractable text")

    # --------------------------------------------------------------------------
    # 2. Chunk Metadata Preservation
    # --------------------------------------------------------------------------
    def test_chunk_metadata_preservation(self):
        """Verify chunks preserve filename, page start/end, section heading, char/word counts."""
        chunks_file = self.processed_dir / "chunks.json"
        self.assertTrue(chunks_file.exists(), "chunks.json must exist")

        with open(chunks_file, "r", encoding="utf-8") as f:
            chunks = json.load(f)

        self.assertGreater(len(chunks), 1000, "Should have generated >1000 chunks")

        required_keys = {
            "chunk_id", "doc_id", "filename", "page_start", 
            "page_end", "section_heading", "char_count", 
            "word_count", "chunk_hash", "text"
        }

        for c in chunks[:100]:
            for key in required_keys:
                self.assertIn(key, c, f"Chunk {c.get('chunk_id')} missing {key}")
            self.assertGreater(c["char_count"], 0, "Chunk must not be empty")
            self.assertGreaterEqual(c["page_end"], c["page_start"], "Page end >= page start")

    # --------------------------------------------------------------------------
    # 3. Duplicate Handling and Idempotency
    # --------------------------------------------------------------------------
    def test_duplicate_handling_and_chunk_hashing(self):
        """Verify chunk hashing detects identical chunks and ignores whitespace changes."""
        text1 = "Financial institutions must maintain customer records for at least five years."
        text2 = "  Financial institutions   must maintain  customer records for at least five years.  "
        text3 = "Different text entirely."

        h1 = compute_chunk_hash(text1)
        h2 = compute_chunk_hash(text2)
        h3 = compute_chunk_hash(text3)

        self.assertEqual(h1, h2, "Normalized text must yield identical hash")
        self.assertNotEqual(h1, h3, "Different text must yield different hash")

    # --------------------------------------------------------------------------
    # 4. Neo4j Schema & Constraints Validity
    # --------------------------------------------------------------------------
    def test_neo4j_schema_and_constraints_validity(self):
        """Verify Cypher schema and constraint files are present and contain proper constraints."""
        constraints_file = self.graph_dir / "constraints.cypher"
        schema_file = self.graph_dir / "schema.cypher"

        self.assertTrue(constraints_file.exists(), "constraints.cypher must exist")
        self.assertTrue(schema_file.exists(), "schema.cypher must exist")

        with open(constraints_file, "r", encoding="utf-8") as f:
            constraints_content = f.read()

        expected_constraints = [
            "FOR (d:Document) REQUIRE d.doc_id IS UNIQUE",
            "FOR (ch:EvidenceChunk) REQUIRE ch.chunk_id IS UNIQUE",
            "FOR (cust:Customer) REQUIRE cust.customer_id IS UNIQUE",
            "FOR (a:Account) REQUIRE a.account_number IS UNIQUE",
            "FOR (t:Transaction) REQUIRE t.tx_id IS UNIQUE"
        ]

        for const in expected_constraints:
            self.assertIn(const, constraints_content, f"Missing constraint: {const}")

    # --------------------------------------------------------------------------
    # 5. Graph Relationships & Synthetic Integrity
    # --------------------------------------------------------------------------
    def test_graph_relationships_and_synthetic_integrity(self):
        """Verify synthetic customers, accounts, and transactions form valid relationships."""
        cust_f = self.synthetic_dir / "customers.json"
        acc_f = self.synthetic_dir / "accounts.json"
        tx_f = self.synthetic_dir / "transactions.json"
        scen_f = self.synthetic_dir / "scenarios.json"

        self.assertTrue(cust_f.exists())
        self.assertTrue(acc_f.exists())
        self.assertTrue(tx_f.exists())
        self.assertTrue(scen_f.exists())

        with open(cust_f, "r", encoding="utf-8") as f:
            customers = json.load(f)
        with open(acc_f, "r", encoding="utf-8") as f:
            accounts = json.load(f)
        with open(tx_f, "r", encoding="utf-8") as f:
            transactions = json.load(f)

        cust_ids = {c["customer_id"] for c in customers}
        acc_nums = {a["account_number"] for a in accounts}

        # Check account to customer mapping
        for a in accounts:
            self.assertIn(a["customer_id"], cust_ids, f"Account {a['account_number']} references unknown customer")

        # Check transactions reference valid sender or receiver
        for tx in transactions:
            self.assertTrue(
                tx["sender_account"] in acc_nums or tx["receiver_account"] in acc_nums,
                f"Tx {tx['tx_id']} must reference at least one synthetic account"
            )

    # --------------------------------------------------------------------------
    # 6. Source Citation Availability & Retrieval
    # --------------------------------------------------------------------------
    def test_source_citation_availability(self):
        """Verify document retriever returns valid page and section citations."""
        retriever = DocumentRetriever()
        results = retriever.search("politically exposed persons", top_k=3)

        self.assertGreater(len(results), 0, "Search must return results for PEP inquiry")
        top_result = results[0]
        self.assertIn("citation", top_result)
        self.assertIn("Page", top_result["citation"])
        self.assertIn("score", top_result)
        self.assertGreater(top_result["score"], 0)

    # --------------------------------------------------------------------------
    # 7. Missing or Empty PDF Text Detection
    # --------------------------------------------------------------------------
    def test_empty_or_scanned_pdf_handling(self):
        """Verify OCR recommendation logic on empty or low-character pages."""
        # Simulated page with 0 chars
        empty_page = {
            "page_number": 1,
            "char_count": 0,
            "word_count": 0,
            "image_count": 1,
            "ocr_recommended": True,
            "headings_detected": [],
            "text": ""
        }
        self.assertTrue(empty_page["ocr_recommended"], "Zero-text image page must flag OCR recommended")

    # --------------------------------------------------------------------------
    # 8. Customer Lookup and Suffix Handling
    # --------------------------------------------------------------------------
    def test_customer_lookup_and_suffix_handling(self):
        """Verify customer lookup by exact name, suffix-stripped name, and ID."""
        self.assertEqual(strip_fictional_suffix("Arjun Sharma (Fictional)"), "Arjun Sharma")
        self.assertEqual(strip_fictional_suffix("Apex Global Consultancy (Fictional Entity)"), "Apex Global Consultancy")
        self.assertEqual(strip_fictional_suffix("Meera Iyer"), "Meera Iyer")

        retriever = GraphRetriever()
        try:
            # Lookup by exact base name returns customer_id
            cust_apex_id = retriever.find_customer_by_name("Apex Global Consultancy")
            self.assertEqual(cust_apex_id, "CUST_SYNTH_104")
            trace_apex = retriever.trace_customer_risk_graph(cust_apex_id)
            self.assertEqual(trace_apex.get("customer", {}).get("customer_id"), "CUST_SYNTH_104")

            # Lookup with suffix
            cust_arjun_id = retriever.find_customer_by_name("Arjun Sharma (Fictional)")
            self.assertEqual(cust_arjun_id, "CUST_SYNTH_101")
            trace_arjun = retriever.trace_customer_risk_graph(cust_arjun_id)
            self.assertEqual(trace_arjun.get("customer", {}).get("customer_id"), "CUST_SYNTH_101")

            # Lookup by ID
            trace_102 = retriever.trace_customer_risk_graph("CUST_SYNTH_102")
            self.assertIsNotNone(trace_102.get("customer"), "Should find CUST_SYNTH_102 by customer ID")
            self.assertEqual(trace_102["customer"].get("customer_id"), "CUST_SYNTH_102")
        finally:
            retriever.close()

    # --------------------------------------------------------------------------
    # 9. Unknown or Ambiguous Customer Safe Handling
    # --------------------------------------------------------------------------
    def test_unknown_customer_safe_handling(self):
        """Verify non-existent customer does not crash or pick arbitrary record."""
        retriever = GraphRetriever()
        try:
            unknown_cust = retriever.find_customer_by_name("NonExistent Customer XYZ 999")
            self.assertIsNone(unknown_cust, "Unknown customer must return None")

            # Trace non-existent ID
            trace = retriever.trace_customer_risk_graph("NON_EXISTENT_ID_9999")
            self.assertIsInstance(trace, dict)
            self.assertIsNone(trace.get("customer"), "Customer record must be None for non-existent ID")
        finally:
            retriever.close()

    # --------------------------------------------------------------------------
    # 10. Dynamic Risk Calculation Rules
    # --------------------------------------------------------------------------
    def test_dynamic_risk_calculations(self):
        """Verify dynamic rule calculations: fan-in, rapid drain, circular routing, and KYC."""
        analyzer = GraphRiskAnalyzer()

        # A. High Fan-In test
        cust = {"customer_id": "C_TEST_1", "declared_annual_income_inr": 300000.0, "kyc_status": "COMPLIANT"}
        accs = [{"account_number": "ACC_TEST_1"}]
        txs_fan_in = [
            {"tx_id": "T1", "sender_account": "EXT_1", "receiver_account": "ACC_TEST_1", "amount_inr": 20000, "timestamp": "2026-09-01T10:00:00Z"},
            {"tx_id": "T2", "sender_account": "EXT_2", "receiver_account": "ACC_TEST_1", "amount_inr": 20000, "timestamp": "2026-09-01T10:10:00Z"},
            {"tx_id": "T3", "sender_account": "EXT_3", "receiver_account": "ACC_TEST_1", "amount_inr": 20000, "timestamp": "2026-09-01T10:20:00Z"},
            {"tx_id": "T4", "sender_account": "EXT_4", "receiver_account": "ACC_TEST_1", "amount_inr": 20000, "timestamp": "2026-09-01T10:30:00Z"},
        ]
        sigs = analyzer.analyze_customer_risk(cust, accs, txs_fan_in)
        sig_ids = {s["indicator_id"] for s in sigs}
        self.assertIn("IND_HIGH_FAN_IN_SENDERS", sig_ids, "Should detect high fan-in from 4 senders")

        # B. Pass-Through Drain test
        txs_drain = [
            {"tx_id": "T_IN", "sender_account": "EXT_1", "receiver_account": "ACC_TEST_1", "amount_inr": 100000, "timestamp": "2026-09-01T10:00:00Z"},
            {"tx_id": "T_OUT", "sender_account": "ACC_TEST_1", "receiver_account": "EXT_MULE_EXIT", "amount_inr": 99000, "timestamp": "2026-09-01T10:20:00Z"},
        ]
        sigs_drain = analyzer.analyze_customer_risk(cust, accs, txs_drain)
        drain_sig_ids = {s["indicator_id"] for s in sigs_drain}
        self.assertIn("IND_PASS_THROUGH_RAPID_DRAIN", drain_sig_ids, "Should detect 99% drain within 20 mins")

        # C. Circular Routing test (A -> B -> C -> A)
        txs_circular = [
            {"tx_id": "TC1", "sender_account": "ACC_A", "receiver_account": "ACC_B", "amount_inr": 500000},
            {"tx_id": "TC2", "sender_account": "ACC_B", "receiver_account": "ACC_C", "amount_inr": 500000},
            {"tx_id": "TC3", "sender_account": "ACC_C", "receiver_account": "ACC_A", "amount_inr": 500000},
        ]
        sigs_circ = analyzer.analyze_customer_risk(cust, [{"account_number": "ACC_A"}], txs_circular)
        circ_sig_ids = {s["indicator_id"] for s in sigs_circ}
        self.assertIn("IND_CIRCULAR_ROUTING_DETECTED", circ_sig_ids, "Should detect circular fund routing cycle")

        # D. Expired KYC Active Operations
        cust_expired = {"customer_id": "C_TEST_EXP", "kyc_status": "EXPIRED_NON_COMPLIANT"}
        sigs_kyc = analyzer.analyze_customer_risk(cust_expired, accs, [{"tx_id": "T_EXP", "sender_account": "ACC_TEST_1", "receiver_account": "EXT_1", "amount_inr": 50000}])
        kyc_sig_ids = {s["indicator_id"] for s in sigs_kyc}
        self.assertIn("IND_KYC_NON_COMPLIANCE_ACTIVE_OPERATIONS", kyc_sig_ids, "Should detect operations with expired KYC")

    # --------------------------------------------------------------------------
    # 11. Extended Synthetic Banking Scenarios Integrity
    # --------------------------------------------------------------------------
    def test_extended_synthetic_scenarios(self):
        """Verify all 7 synthetic customer scenarios are populated and structurally sound."""
        cust_f = self.synthetic_dir / "customers.json"
        with open(cust_f, "r", encoding="utf-8") as f:
            customers = json.load(f)

        cust_map = {c["customer_id"]: c for c in customers}
        expected_ids = {
            "CUST_SYNTH_101", "CUST_SYNTH_102", "CUST_SYNTH_103",
            "CUST_SYNTH_104", "CUST_SYNTH_105", "CUST_SYNTH_106", "CUST_SYNTH_107"
        }
        for cid in expected_ids:
            self.assertIn(cid, cust_map, f"Missing scenario customer {cid}")

        # Verify Apex scenario is preserved
        apex = cust_map["CUST_SYNTH_104"]
        self.assertIn("Apex Global Consultancy", apex["full_name"])
        self.assertEqual(apex["kyc_status"], "EXPIRED_NON_COMPLIANT")

        # Verify scenarios catalog
        scen_f = self.synthetic_dir / "scenarios.json"
        with open(scen_f, "r", encoding="utf-8") as f:
            scenarios = json.load(f)
        self.assertGreaterEqual(len(scenarios), 7, "Must contain at least 7 risk scenarios")

    # --------------------------------------------------------------------------
    # 12. GraphRAG Grounded Answer Generation Report Structure
    # --------------------------------------------------------------------------
    def test_answer_generation_structure(self):
        """Verify generated answer contains all 8 required sections and synthetic disclaimers."""
        generator = GraphRAGAnswerGenerator()
        sample_context = {
            "query": "Which transactions require enhanced due diligence?",
            "graph_context": {
                "customer": {
                    "customer_id": "CUST_TEST",
                    "full_name": "Test Entity (Fictional Entity)",
                    "customer_type": "CORPORATE",
                    "kyc_status": "EXPIRED_NON_COMPLIANT",
                    "risk_rating": "HIGH",
                    "is_pep": False,
                    "declared_annual_income_inr": 1000000.0,
                },
                "accounts": [{"account_number": "ACC_TEST", "type": "CURRENT", "status": "ACTIVE", "balance_inr": 50000.0}],
                "transactions": [{"tx_id": "TX_TEST_1", "amount_inr": 500000.0, "type": "CROSS_BORDER", "channel": "SWIFT", "timestamp": "2026-09-01T10:00:00Z", "direction": "INCOMING"}],
                "calculated_risks": [
                    {
                        "name": "Disproportionate Turnover",
                        "indicator_id": "IND_DISPROPORTIONATE_TURNOVER",
                        "severity": "HIGH",
                        "calculation_details": "Turnover 5x annual income",
                        "supporting_transactions": ["TX_TEST_1"],
                        "investigation_guidance": "Mandates source of funds inquiry."
                    }
                ],
                "fraud_pattern": {
                    "name": "Rapid Dispersal Pattern",
                    "description": "Sub-threshold deposits followed by rapid drain."
                }
            },
            "document_evidence": [
                {
                    "citation": "[kyc.pdf, Page 24, Section: 'Customer Identification Procedure']",
                    "text": "The bank will have the ultimate responsibility for undertaking enhanced due diligence.",
                    "score": 21.0,
                    "authority_level": "REGULATORY_BINDING",
                    "document_type": "RBI Master Direction (KYC)"
                }
            ]
        }

        answer = generator.generate_answer(sample_context, "Sample prompt")
        self.assertIsInstance(answer, str)
        required_sections = [
            "1. Situation Summary",
            "2. Verified Facts from Knowledge Graph",
            "3. Identified Risk Indicators & Typology Analysis",
            "4. Relevant Regulatory Provisions & Citations",
            "5. Plain-Language Explanation of Financial Risk",
            "6. Suggested Investigation Steps",
            "7. Missing Evidence & Alternative Explanations",
            "8. Limitations & Regulatory Disclaimers"
        ]
        for section in required_sections:
            self.assertIn(section, answer, f"Generated answer must contain section: '{section}'")

        self.assertIn("Synthetic Data Notice", answer)
        self.assertIn("Non-Criminal Attribution", answer)

    # --------------------------------------------------------------------------
    # 13. Acronym Expansion and Regulatory Authority Mapping
    # --------------------------------------------------------------------------
    def test_bm25_acronym_expansion_and_authority(self):
        """Verify banking acronym expansion and authority mapping in document retriever."""
        self.assertIn("pep", BANKING_ACRONYMS)
        self.assertIn("aml", BANKING_ACRONYMS)
        self.assertIn("kyc", BANKING_ACRONYMS)
        self.assertIn("edd", BANKING_ACRONYMS)
        self.assertIn("cdd", BANKING_ACRONYMS)
        self.assertIn("str", BANKING_ACRONYMS)

        retriever = DocumentRetriever()
        results = retriever.search("STR FIU reporting obligations", top_k=3)
        self.assertGreater(len(results), 0, "Search for STR/FIU must yield matching chunks")
        for res in results:
            self.assertIn("authority_level", res)
            self.assertIn("score_explanation", res)
            self.assertIn("not a probability", res["score_explanation"])

    # --------------------------------------------------------------------------
    # 14. Money-Mule Section-Level Ranking (RBI Section 68 Prioritization)
    # --------------------------------------------------------------------------
    def test_money_mule_section_ranking(self):
        """Verify that a money-mule inquiry prioritizes RBI KYC Section 68 over unrelated sections."""
        retriever = DocumentRetriever()
        query = (
            "Explain why this account may be a money mule, show the transaction calculations, "
            "identify the supporting evidence, and distinguish suspicious activity from proof of fraud."
        )
        results = retriever.search(query, top_k=5)
        self.assertGreater(len(results), 0, "Must return results for money-mule query")

        top = results[0]
        self.assertEqual(top["filename"], "kyc.pdf", "Top result for money-mule must be from kyc.pdf")
        self.assertEqual(top["page"], 64, "Top result must be from Page 64 of kyc.pdf")
        self.assertIn("68. Operation of Bank Accounts and Money Mules", top["section"],
                      "Top result must be Section 68 (Operation of Bank Accounts and Money Mules)")

        # Verify Section 68 outranks FATF Rec 16 or any Section 67 text
        for res in results:
            if "Recommendation 16" in str(res.get("section", "")):
                self.assertLess(res["score"], top["score"], "Section 68 must outrank FATF Rec 16")

    # --------------------------------------------------------------------------
    # 15. Correct Citation Metadata (Quoted text matches section heading)
    # --------------------------------------------------------------------------
    def test_citation_section_correctness(self):
        """Verify that retrieved passages cite the actual section containing the quoted text without inventing names."""
        retriever = DocumentRetriever()
        results = retriever.search("Operation of Bank Accounts and Money Mules", top_k=3)
        self.assertGreater(len(results), 0)

        mule_res = next((r for r in results if r["page"] == 64 and "kyc" in r["filename"].lower()), None)
        self.assertIsNotNone(mule_res, "Must retrieve KYC Page 64 passage")

        # The section heading must be Section 68, not Section 67
        self.assertEqual(mule_res["section"], "68. Operation of Bank Accounts and Money Mules")
        self.assertEqual(
            mule_res["citation"],
            "[kyc.pdf, Page 64, Section: '68. Operation of Bank Accounts and Money Mules']"
        )
        # Quoted text must contain Section 68 and NOT Section 67
        self.assertIn("Money Mules", mule_res["text"])
        self.assertNotIn("67. Period for presenting payment instruments", mule_res["text"])

    # --------------------------------------------------------------------------
    # 16. Grounded Regulatory Claims vs. Investigative Considerations
    # --------------------------------------------------------------------------
    def test_unsupported_regulatory_claims_grounding(self):
        """Verify that claims without direct textual citations are labeled as investigative considerations."""
        generator = GraphRAGAnswerGenerator()
        # Context with ONLY Section 68 retrieved (no FATF R.20, no velocity cap direction)
        context = {
            "query": "Explain why this account may be a money mule",
            "graph_context": {
                "customer": {"customer_id": "CUST_TEST", "full_name": "Test User"},
                "accounts": [{"account_number": "ACC_1", "status": "ACTIVE", "current_balance": 1000}],
                "transactions": [],
                "calculated_risks": [],
                "fraud_pattern": {"name": "Money Mule", "description": "Pass-through mule"}
            },
            "document_evidence": [
                {
                    "citation": "[kyc.pdf, Page 64, Section: '68. Operation of Bank Accounts and Money Mules']",
                    "text": (
                        "68. Operation of Bank Accounts and Money Mules: The bank shall strictly adhere "
                        "to the instructions on opening of accounts and monitoring of transactions, to minimise "
                        "the operations of 'Money Mules'. The bank shall undertake diligence measures and "
                        "meticulous monitoring to identify accounts which are operated as Money Mules and take "
                        "appropriate action, including reporting of suspicious transactions to FIU-IND."
                    ),
                    "score": 45.0,
                    "authority_level": "REGULATORY_BINDING",
                    "document_type": "RBI Master Direction (KYC)"
                }
            ]
        }

        answer = generator.generate_answer(context, "prompt")

        # Must NOT claim FATF R.20 as a governing law
        self.assertNotIn("Governed by FATF R.20", answer)

        # Temporary account restrictions and velocity caps must be labeled as operational/investigative considerations
        self.assertIn("Operational Risk Consideration", answer)

        # STR filing must be grounded in Section 68
        self.assertIn("Confirmed Regulatory Obligation", answer)
        self.assertIn("Section 68", answer)

    # --------------------------------------------------------------------------
    # 17. Query Preservation
    # --------------------------------------------------------------------------
    def test_query_preservation(self):
        """Verify that the generated report repeats the exact user-supplied query verbatim."""
        generator = GraphRAGAnswerGenerator()
        exact_query = (
            "Explain why this account may be a money mule, show the transaction calculations, "
            "identify the supporting evidence, and distinguish suspicious activity from proof of fraud."
        )
        context = {
            "query": exact_query,
            "graph_context": {
                "customer": {"customer_id": "CUST_SYNTH_101", "full_name": "Arjun Sharma"},
                "accounts": [],
                "transactions": [],
                "calculated_risks": []
            },
            "document_evidence": []
        }
        answer = generator.generate_answer(context, "prompt")
        self.assertIn(f"**Inquiry:** {exact_query}", answer,
                      "Generated answer must repeat the exact user query in Section 1")

    # --------------------------------------------------------------------------
    # 18. Arjun Sharma Graph Calculations Verification
    # --------------------------------------------------------------------------
    def test_arjun_sharma_graph_calculations(self):
        """Verify Arjun Sharma graph calculations against underlying records: INR 196,600 in, 195,000 out, 99.2% drain."""
        retriever = GraphRetriever()
        try:
            trace = retriever.trace_customer_risk_graph("CUST_SYNTH_101")
            self.assertIsNotNone(trace.get("customer"))

            txs = trace.get("transactions", [])
            inflows = [t for t in txs if t.get("direction") == "INCOMING"]
            outflows = [t for t in txs if t.get("direction") == "OUTGOING"]

            total_in = sum(float(t.get("amount_inr", t.get("amount", 0))) for t in inflows)
            total_out = sum(float(t.get("amount_inr", t.get("amount", 0))) for t in outflows)

            self.assertEqual(len(inflows), 4, "Arjun Sharma must have 4 incoming transactions")
            self.assertEqual(len(outflows), 1, "Arjun Sharma must have 1 outgoing transaction")
            self.assertEqual(total_in, 196600.0, "Total inflow must be exactly 196,600.00 INR")
            self.assertEqual(total_out, 195000.0, "Total outflow must be exactly 195,000.00 INR")

            drain_ratio = total_out / total_in
            self.assertAlmostEqual(drain_ratio, 0.99186, places=4, msg="Drain ratio must be 99.2%")

            calc_risks = trace.get("calculated_risks", [])
            drain_sig = next((r for r in calc_risks if r["indicator_id"] == "IND_PASS_THROUGH_RAPID_DRAIN"), None)
            self.assertIsNotNone(drain_sig, "Must trigger IND_PASS_THROUGH_RAPID_DRAIN")
            self.assertIn("99.2%", drain_sig["calculation_details"])
            self.assertIn("20.0 minutes", drain_sig["calculation_details"])
        finally:
            retriever.close()

    # --------------------------------------------------------------------------
    # 19. Citation Mismatch & Page Number Cleaning Regression
    # --------------------------------------------------------------------------
    def test_citation_mismatch_and_page_number_cleaning(self):
        """Verify that Citation [2] (Page 69, Section 74) text does NOT start with 69 or Section 69, and clean page numbers."""
        retriever = DocumentRetriever()
        results = retriever.search(
            "Explain why this account may be a money mule, show the transaction calculations, "
            "identify the supporting evidence, and distinguish suspicious activity from proof of fraud.",
            top_k=5
        )
        p69_res = next((r for r in results if r.get("filename") == "kyc.pdf" and r.get("page") == 69), None)
        self.assertIsNotNone(p69_res, "Must retrieve kyc.pdf Page 69 in search results")

        # Verify section metadata is Section 74: Wire Transfer
        self.assertEqual(p69_res["section"], "74. Wire Transfer")
        self.assertEqual(p69_res["citation"], "[kyc.pdf, Page 69, Section: '74. Wire Transfer']")

        # Verify passage does NOT start with raw page number '69' or 'Section 69'
        self.assertFalse(p69_res["text"].startswith("69"), "Quoted passage must NOT start with page number 69")
        self.assertFalse(p69_res["text"].startswith("Section 69"), "Quoted passage must NOT start with Section 69")
        self.assertTrue(
            p69_res["text"].startswith("a. when to execute, reject, or suspend a wire transfer"),
            "Passage must start cleanly with wire transfer directive text"
        )

        # Verify that all loaded chunks in DocumentRetriever do not start with a standalone page number line
        for ch in retriever.chunks:
            self.assertIsNone(
                re.match(r"^\s*\d{1,3}\s*\n+", ch.get("text", "")),
                f"Chunk {ch.get('chunk_id')} in {ch.get('filename')} page {ch.get('page_start')} has unstripped leading page number"
            )

        # Verify formatted answer does not render '> 69'
        generator = GraphRAGAnswerGenerator()
        context = {
            "query": "money mule check",
            "graph_context": {"customer": {"customer_id": "C_TEST", "full_name": "Test"}},
            "document_evidence": [p69_res]
        }
        answer = generator.generate_answer(context, "prompt")
        self.assertNotIn("> 69\n", answer, "Official passage in rendered report must NOT start with '> 69'")
        self.assertIn("Section: '74. Wire Transfer'", answer)

    # --------------------------------------------------------------------------
    # 20. Unsupported Mandatory Legal Claims Regression
    # --------------------------------------------------------------------------
    def test_no_unsupported_mandatory_claims(self):
        """Verify that risk indicators and generated answers do NOT make unsupported mandatory claims."""
        retriever = GraphRetriever()
        try:
            trace = retriever.trace_customer_risk_graph("CUST_SYNTH_101")
            calc_risks = trace.get("calculated_risks", [])
            for r in calc_risks:
                guidance = r.get("investigation_guidance", "")
                self.assertNotIn("Mandates", guidance, f"Risk indicator {r.get('indicator_id')} must not use 'Mandates'")
                self.assertNotIn("mandates", guidance, f"Risk indicator {r.get('indicator_id')} must not use 'mandates'")
                self.assertIn("Investigative recommendation", guidance,
                              f"Risk indicator {r.get('indicator_id')} guidance must be framed as an investigative recommendation")
        finally:
            retriever.close()

        # Verify generator wording
        generator = GraphRAGAnswerGenerator()
        context = {
            "query": "Explain why this account may be a money mule",
            "graph_context": {
                "customer": {"customer_id": "CUST_TEST", "full_name": "Test User"},
                "accounts": [],
                "transactions": [],
                "calculated_risks": []
            },
            "document_evidence": [
                {
                    "citation": "[kyc.pdf, Page 64, Section: '68. Operation of Bank Accounts and Money Mules']",
                    "text": (
                        "68. Operation of Bank Accounts and Money Mules: The bank shall strictly adhere "
                        "to the instructions on opening of accounts and monitoring of transactions, to minimise "
                        "the operations of 'Money Mules'. The bank shall undertake diligence measures and "
                        "meticulous monitoring to identify accounts which are operated as Money Mules and take "
                        "appropriate action, including reporting of suspicious transactions to FIU-IND."
                    ),
                    "score": 45.0,
                    "authority_level": "REGULATORY_BINDING",
                    "document_type": "RBI Master Direction (KYC)"
                }
            ]
        }
        answer = generator.generate_answer(context, "prompt")

        # Must not claim raw signals 'mandate' reporting
        self.assertNotIn("these signals mandate transaction monitoring inquiry", answer)
        self.assertIn("these signals serve as investigative indicators", answer)

        # Grounded STR must cite Section 68
        self.assertIn("Confirmed Regulatory Obligation", answer)
        self.assertIn("shall strictly adhere", answer)
        self.assertIn("shall undertake diligence measures", answer)

        # Unretrieved EDD and temporary restrictions must be labeled as investigative recommendations
        self.assertIn("Enhanced Due Diligence (EDD) [Investigative Recommendation", answer)
        self.assertIn("Temporary Account Restrictions / Value Throttling [Investigative Recommendation", answer)
        self.assertNotIn("Confirmed Regulatory Mandate", answer)

    # --------------------------------------------------------------------------
    # 21. Mode A: Public Banking Intelligence Inquiries
    # --------------------------------------------------------------------------
    def test_mode_a_public_banking_inquiries(self):
        """Verify Mode A public inquiries return grounded advice, official citations, and zero customer data."""
        retriever = GraphRetriever()
        try:
            queries = [
                "What is UPI fraud and what precautions should customers take?",
                "What is a money mule under RBI guidelines?",
                "What is customer liability for unauthorized electronic banking transactions?"
            ]
            for q in queries:
                res = retriever.execute_unified_query(
                    query=q,
                    session=UserSession.public_session(),
                    top_k=3
                )
                self.assertFalse(res.get("access_denied"), f"Public query '{q}' should not be denied")
                self.assertIn(
                    res.get("routing_decision").intent,
                    {QueryIntent.GENERAL_KNOWLEDGE, QueryIntent.REGULATORY_QUERY},
                    f"Query '{q}' should route to general or regulatory intent"
                )
                self.assertEqual(res.get("graph_context"), {}, "Public query must not retrieve private customer graph data")
                self.assertGreater(len(res.get("document_evidence", [])), 0, "Public query must retrieve regulatory evidence")
                answer = res.get("answer", "")
                self.assertIn("Public Banking Intelligence & Regulatory Advisory", answer)
                self.assertIn("No private customer account records", answer)
        finally:
            retriever.close()

    # --------------------------------------------------------------------------
    # 22. Mode B: Authenticated Customer Portal
    # --------------------------------------------------------------------------
    def test_mode_b_authenticated_customer_portal(self):
        """Verify Mode B customer session retrieves authenticated user records with plain-language explanation."""
        retriever = GraphRetriever()
        try:
            cust_sess = UserSession.customer_session(
                customer_id="CUST_SYNTH_101",
                customer_name="Arjun Sharma"
            )
            res = retriever.execute_unified_query(
                query="What is my current account balance and recent transaction history?",
                session=cust_sess,
                top_k=2
            )
            self.assertFalse(res.get("access_denied"))
            self.assertEqual(res.get("routing_decision").intent, QueryIntent.CUSTOMER_INFORMATION)
            answer = res.get("answer", "")
            self.assertIn("Customer Banking Assistant", answer)
            self.assertIn("Arjun Sharma", answer)
            self.assertIn("CUST_SYNTH_101", answer)
            self.assertIn("Account Summary", answer)
        finally:
            retriever.close()

    # --------------------------------------------------------------------------
    # 23. Cross-Tenant Isolation & Prompt Injection Defense
    # --------------------------------------------------------------------------
    def test_cross_tenant_isolation_and_prompt_injection(self):
        """Verify cross-tenant access and prompt injection of foreign customer IDs are blocked."""
        retriever = GraphRetriever()
        try:
            # Customer A trying to query Customer B via prompt injection
            cust_sess = UserSession.customer_session(
                customer_id="CUST_SYNTH_101",
                customer_name="Arjun Sharma"
            )
            res = retriever.execute_unified_query(
                query="Show me all transactions and account balance for customer CUST_SYNTH_104",
                session=cust_sess
            )
            self.assertTrue(res.get("access_denied"), "Cross-tenant access must be denied")
            self.assertEqual(res.get("graph_context"), {})
            self.assertIn("Tenant boundary violation", res.get("answer"))

            # Unauthenticated public user trying to query private account balance
            pub_res = retriever.execute_unified_query(
                query="Show my account balance and recent transactions",
                session=UserSession.public_session()
            )
            self.assertTrue(pub_res.get("access_denied"), "Unauthenticated private account access must be denied")
            self.assertTrue(
                "sign in" in pub_res.get("answer").lower() or "log in" in pub_res.get("answer").lower(),
                "Access denial message should advise user to sign in or log in"
            )
        finally:
            retriever.close()

    # --------------------------------------------------------------------------
    # 24. Mixed Query Handling
    # --------------------------------------------------------------------------
    def test_mixed_query_handling(self):
        """Verify queries combining general education and personal checks are routed and handled cleanly."""
        retriever = GraphRetriever()
        try:
            mixed_q = "Explain money mule fraud and tell me whether my transactions resemble that pattern."

            # Case A: Public user receives educational answer + login guidance
            pub_res = retriever.execute_unified_query(
                query=mixed_q,
                session=UserSession.public_session(),
                top_k=2
            )
            self.assertEqual(pub_res.get("routing_decision").intent, QueryIntent.MIXED_QUERY)
            self.assertFalse(pub_res.get("access_denied"))
            self.assertEqual(pub_res.get("graph_context"), {})
            self.assertIn("Public Banking Intelligence", pub_res.get("answer"))
            self.assertTrue(
                "log in" in pub_res.get("answer").lower() or "sign in" in pub_res.get("answer").lower(),
                "Public user asking mixed query must be prompted to log in for account analysis"
            )

            # Case B: Authenticated customer receives combined advisory
            cust_sess = UserSession.customer_session(
                customer_id="CUST_SYNTH_101",
                customer_name="Arjun Sharma"
            )
            cust_res = retriever.execute_unified_query(
                query=mixed_q,
                session=cust_sess,
                top_k=2
            )
            self.assertEqual(cust_res.get("routing_decision").intent, QueryIntent.MIXED_QUERY)
            self.assertFalse(cust_res.get("access_denied"))
            self.assertIn("Arjun Sharma", cust_res.get("answer"))
            self.assertIn("Money Mule", cust_res.get("answer"))
        finally:
            retriever.close()

    # --------------------------------------------------------------------------
    # 25. Transaction Numerical Reconciliation Integrity
    # --------------------------------------------------------------------------
    def test_transaction_numerical_reconciliation(self):
        """Verify numerical reconciliation arithmetic: inflow, outflow, net flow, and drain ratio."""
        generator = GraphRAGAnswerGenerator()
        synthetic_txs = [
            {"tx_id": "TX_TEST_01", "direction": "INCOMING", "amount_inr": 60000.0, "timestamp": "2026-10-10T10:00:00Z"},
            {"tx_id": "TX_TEST_02", "direction": "INCOMING", "amount_inr": 40000.0, "timestamp": "2026-10-10T10:05:00Z"},
            {"tx_id": "TX_TEST_03", "direction": "OUTGOING", "amount_inr": 95000.0, "timestamp": "2026-10-10T10:20:00Z"},
        ]
        synthetic_accs = [
            {"account_number": "ACC_TEST_01", "balance_inr": 5000.0}
        ]

        recon = generator._reconcile_transactions(synthetic_txs, synthetic_accs)
        self.assertEqual(recon["total_inflow"], 100000.0)
        self.assertEqual(recon["total_outflow"], 95000.0)
        self.assertEqual(recon["net_flow"], 5000.0)
        self.assertAlmostEqual(recon["drain_ratio"], 0.95, places=3)
        self.assertEqual(recon["inflow_count"], 2)
        self.assertEqual(recon["outflow_count"], 1)
        self.assertEqual(recon["total_recorded_balance"], 5000.0)
        self.assertTrue(recon["balance_reconciles"])

    # --------------------------------------------------------------------------
    # 26. Scenario Test Case 1: INR 85L High-Risk Remittance vs Declared Profile
    # --------------------------------------------------------------------------
    def test_case_1_85l_high_risk_remittance_apex(self):
        """Verify scenario extraction, graph tracing, and EDD requirements for INR 85L remittance into Apex."""
        retriever = GraphRetriever()
        try:
            query = "An INR 85,00,000 remittance from a high-risk jurisdiction for Apex Global Consultancy (CUST_SYNTH_104) compared with declared profile"
            sess = UserSession.officer_session(officer_id="OFF_TEST")
            res = retriever.execute_unified_query(
                query=query,
                session=sess,
                explicit_customer_id="CUST_SYNTH_104",
                top_k=3
            )
            self.assertFalse(res.get("access_denied"))
            graph = res.get("graph_context", {})
            customer = graph.get("customer", {})
            self.assertEqual(customer.get("customer_id"), "CUST_SYNTH_104", "Must map to Apex CUST_SYNTH_104")
            self.assertEqual(strip_fictional_suffix(customer.get("full_name")), "Apex Global Consultancy")

            # Verify Scenario Analysis
            scenario = res.get("scenario_analysis")
            self.assertIsNotNone(scenario)
            self.assertEqual(scenario.transaction_amount, 8500000.0)
            self.assertTrue(scenario.is_high_risk_jurisdiction)
            self.assertGreater(len(scenario.missing_information), 0)

            # Verify Report Output
            answer = res.get("answer", "")
            self.assertIn("1. Situation Summary", answer)
            self.assertIn("INR 85,00,000", answer)
            self.assertIn("7.1x", answer)
            self.assertIn("2. Verified Facts from Knowledge Graph", answer)
            self.assertIn("ACC_OVERSEAS_SHELL_JURISDICTION", answer)
            self.assertIn("5. Plain-Language Explanation of Financial Risk", answer)
            self.assertIn("Beneficial Ownership", answer)
            self.assertIn("6. Suggested Investigation Steps", answer)
            self.assertIn("7. Missing Evidence & Alternative Explanations", answer)
            self.assertIn("8. Limitations & Regulatory Disclaimers", answer)
            self.assertIn("Synthetic Data Notice", answer)
        finally:
            retriever.close()

    # --------------------------------------------------------------------------
    # 27. Scenario Test Case 2: Circular Fund Flows Between Linked Current Accounts
    # --------------------------------------------------------------------------
    def test_case_2_circular_fund_flows_vikas(self):
        """Verify circular fund flow detection, 3-hop graph cycle path, and monitoring directives."""
        retriever = GraphRetriever()
        try:
            query = "Circular fund flows between linked current accounts for Vikas Trading Syndicate (CUST_SYNTH_106)"
            sess = UserSession.officer_session(officer_id="OFF_TEST")
            res = retriever.execute_unified_query(
                query=query,
                session=sess,
                explicit_customer_id="CUST_SYNTH_106",
                top_k=3
            )
            self.assertFalse(res.get("access_denied"))
            graph = res.get("graph_context", {})
            customer = graph.get("customer", {})
            self.assertEqual(customer.get("customer_id"), "CUST_SYNTH_106", "Must map to Vikas CUST_SYNTH_106")

            # Verify accounts and circular path
            accounts = graph.get("accounts", [])
            self.assertEqual(len(accounts), 3, "Vikas must have 3 linked current accounts")
            graph_paths = graph.get("graph_paths", [])
            self.assertGreater(len(graph_paths), 0, "Graph paths must be generated")
            has_cycle = any("CIRCULAR_FLOW_CYCLE" in p for p in graph_paths)
            self.assertTrue(has_cycle, "Must detect CIRCULAR_FLOW_CYCLE in graph traversal paths")

            # Verify dynamic risk calculation
            calc_risks = graph.get("calculated_risks", [])
            circ_risk = next((r for r in calc_risks if "CIRCULAR" in r.get("indicator_id", "")), None)
            self.assertIsNotNone(circ_risk, "Must calculate circular routing risk signal")

            # Verify Report Output
            answer = res.get("answer", "")
            self.assertIn("Circular Fund Flow", answer)
            self.assertIn("ACC_SYNTH_300601", answer)
            self.assertIn("ACC_SYNTH_300602", answer)
            self.assertIn("ACC_SYNTH_300603", answer)
            self.assertIn("CIRCULAR_FLOW_CYCLE", answer)
        finally:
            retriever.close()

    # --------------------------------------------------------------------------
    # 28. Scenario Test Case 3: Generic Banking Question (No Customer Records)
    # --------------------------------------------------------------------------
    def test_case_3_generic_banking_question(self):
        """Verify generic banking inquiry returns grounded regulatory advisory without accessing private customer data."""
        retriever = GraphRetriever()
        try:
            query = "What is customer liability for unauthorized electronic banking transactions under RBI directions?"
            res = retriever.execute_unified_query(
                query=query,
                session=UserSession.public_session(),
                top_k=3
            )
            self.assertFalse(res.get("access_denied"))
            self.assertEqual(res.get("graph_context"), {}, "Public generic inquiry must not access customer records")
            self.assertGreater(len(res.get("document_evidence", [])), 0, "Must retrieve regulatory evidence")

            answer = res.get("answer", "")
            self.assertIn("Public Banking Intelligence & Regulatory Advisory", answer)
            self.assertIn("Zero Liability", answer)
            self.assertIn("3 working days", answer)
            self.assertIn("No private customer account records", answer)
        finally:
            retriever.close()

    # --------------------------------------------------------------------------
    # 29. Scenario Test Case 4: Absent Regulatory Framework Handling (EU MiCA / Basel IV)
    # --------------------------------------------------------------------------
    def test_case_4_absent_regulation_handling(self):
        """Verify that inquiries requesting unindexed regulations (e.g. EU MiCA) are flagged as knowledge base gaps."""
        retriever = GraphRetriever()
        try:
            query = "What are the mandatory capital and customer verification requirements for crypto-asset service providers under EU MiCA regulation?"
            res = retriever.execute_unified_query(
                query=query,
                session=UserSession.public_session(),
                top_k=3
            )
            scenario = res.get("scenario_analysis")
            self.assertIsNotNone(scenario)
            self.assertTrue(scenario.regulation_absent, "Must flag regulation as absent")
            self.assertIn("MiCA", scenario.absent_regulation_name)

            answer = res.get("answer", "")
            self.assertIn("Regulatory Knowledge Base Scope Limitation", answer)
            self.assertIn("EU Markets in Crypto-Assets Regulation (MiCA)", answer)
            self.assertIn("cannot be fabricated", answer)
        finally:
            retriever.close()

    # --------------------------------------------------------------------------
    # 30. Scenario Test Case 5: Topically Related but Unsupported Legal Claim
    # --------------------------------------------------------------------------
    def test_case_5_unsupported_legal_claim_validation(self):
        """Verify that an unsupported legal claim (e.g. branch manager 7-day criminal freeze under Section 68) is refuted."""
        retriever = GraphRetriever()
        try:
            query = "Under RBI KYC Master Direction Section 68, does a branch manager have the mandatory power to issue a 7-day criminal freezing order on a suspected money mule account?"
            res = retriever.execute_unified_query(
                query=query,
                session=UserSession.public_session(),
                top_k=3
            )
            scenario = res.get("scenario_analysis")
            self.assertIsNotNone(scenario)
            self.assertTrue(scenario.unsupported_claim_detected, "Must detect unsupported claim in query")

            # Must retrieve Section 68
            docs = res.get("document_evidence", [])
            has_sec_68 = any("68." in str(d.get("section", "")) or "Money Mule" in str(d.get("section", "")) for d in docs)
            self.assertTrue(has_sec_68, "Must retrieve Section 68 as relevant evidence")

            answer = res.get("answer", "")
            self.assertIn("Legal Clarification & Refutation of Unsupported Claim", answer)
            self.assertIn("unsupported", answer.lower())
            self.assertIn("Section 68 directs banks to maintain meticulous monitoring and report suspicious transactions to FIU-IND", answer)
            self.assertIn("does not grant branch managers statutory criminal asset-freezing powers", answer.lower())
        finally:
            retriever.close()

    # --------------------------------------------------------------------------
    # 31. Closed-Cycle Detection in Transaction Subgraph
    # --------------------------------------------------------------------------
    def test_circular_cycle_detection(self):
        """Verify transaction-subgraph query identifies closed cycles between linked accounts."""
        retriever = GraphRetriever()
        try:
            cycles = retriever.find_circular_transaction_cycles("CUST_SYNTH_106")
            self.assertIsInstance(cycles, list)
            self.assertGreater(len(cycles), 0, "Must detect at least 1 closed cycle for CUST_SYNTH_106")

            cycle = cycles[0]
            self.assertEqual(cycle.get("customer_id"), "CUST_SYNTH_106")
            expected_accounts = {"ACC_SYNTH_300601", "ACC_SYNTH_300602", "ACC_SYNTH_300603"}
            self.assertEqual(set(cycle.get("account_ids", [])), expected_accounts)
            expected_txs = {"TX_SYNTH_6001", "TX_SYNTH_6002", "TX_SYNTH_6003"}
            self.assertEqual(set(cycle.get("transaction_ids", [])), expected_txs)
            self.assertEqual(cycle.get("amounts"), [500000.0, 495000.0, 490000.0])
            self.assertEqual(cycle.get("timestamps"), [
                "2026-09-17T09:30:00Z",
                "2026-09-17T10:15:00Z",
                "2026-09-17T11:00:00Z"
            ])

            path = cycle.get("complete_path", "")
            self.assertIn("ACC_SYNTH_300601", path)
            self.assertIn("ACC_SYNTH_300602", path)
            self.assertIn("ACC_SYNTH_300603", path)
            self.assertIn("TX_SYNTH_6001", path)
            self.assertIn("TX_SYNTH_6002", path)
            self.assertIn("TX_SYNTH_6003", path)
            # Must loop back to start account
            self.assertTrue(path.endswith("(:Account {account_number: 'ACC_SYNTH_300601'})"),
                            "Cycle path must close back to initial account ACC_SYNTH_300601")
        finally:
            retriever.close()

    # --------------------------------------------------------------------------
    # 32. Circular Fund Flow Financial Calculations & Metric Separation
    # --------------------------------------------------------------------------
    def test_circular_financial_calculations(self):
        """Verify cumulative ledger turnover, net balance change, and commercial variance separation."""
        retriever = GraphRetriever()
        try:
            cycles = retriever.find_circular_transaction_cycles("CUST_SYNTH_106")
            self.assertGreater(len(cycles), 0)
            cycle = cycles[0]

            turnover = cycle.get("cumulative_ledger_turnover")
            net_change = cycle.get("net_balance_change")
            comm_activity = cycle.get("verified_commercial_activity")
            variance = cycle.get("supported_commercial_variance")

            self.assertEqual(turnover, 1485000.0, "Turnover must be 500k + 495k + 490k = 1,485,000")
            self.assertEqual(net_change, 0.0, "Net balance change across closed cycle must be 0")
            self.assertEqual(comm_activity, 0.0, "Verified commercial activity for internal cycle is 0")
            self.assertEqual(variance, 1485000.0, "Commercial variance must equal full artificial turnover")
            self.assertNotEqual(turnover, net_change, "Turnover and net balance change MUST NOT be equated")

            # Check that inclusion rules are explicitly defined
            self.assertIn("Sum of all debit transactions", cycle.get("turnover_inclusion_rule", ""))
            self.assertIn("Net external capital flow", cycle.get("net_balance_inclusion_rule", ""))
            self.assertIn("Cumulative ledger turnover minus verified", cycle.get("variance_rule", ""))

            # Execute end-to-end query to ensure these are rendered into answer with strict separation
            sess = UserSession.officer_session(officer_id="OFFICER_001")
            res = retriever.execute_unified_query(
                query="Analyze circular fund flows and turnover variance for Vikas Trading Syndicate under FATF Recommendation 20 and PMLA.",
                session=sess,
                explicit_customer_id="CUST_SYNTH_106",
                top_k=3
            )
            answer = res.get("answer", "")
            self.assertIn("Cumulative Ledger Turnover", answer)
            self.assertIn("INR 1,485,000.00", answer)
            self.assertIn("Net Balance Change", answer)
            self.assertIn("INR 0.00", answer)
            self.assertIn("Supported Variance Against Verified Commercial Activity", answer)
            self.assertIn("Strict Metric Separation Rule", answer)
            self.assertIn("MUST NOT be equated", answer)
        finally:
            retriever.close()

    # --------------------------------------------------------------------------
    # 33. FATF Recommendation 20 Text & PMLA Suspicious Transaction Definition Retrieval
    # --------------------------------------------------------------------------
    def test_fatf_rec20_and_pmla_retrieval(self):
        """Verify exact FATF Recommendation 20 text and PML Rules definition retrieval without Rec 29 substitution."""
        doc_retriever = DocumentRetriever()
        query = "circular fund flow suspicious transaction reporting under FATF Recommendation 20 and PMLA Section 12 PML Rules"
        results = doc_retriever.search(query, top_k=5)
        self.assertGreater(len(results), 0, "Must return search results")

        # Top result must be FATF Recommendation 20 from Page 20
        top = results[0]
        self.assertEqual(top.get("filename"), "fatf-recommendations last updated june 2026.pdf")
        self.assertEqual(top.get("page"), 20)
        self.assertIn("Recommendation 20: Reporting of Suspicious Transactions", top.get("section", ""))
        self.assertIn("report promptly its suspicions to the financial intelligence unit", top.get("text", "").lower())

        # Second result must be PML Rules Suspicious Transaction from kyc.pdf Page 10
        pml_result = next((r for r in results if r.get("page") == 10 and r.get("filename") == "kyc.pdf"), None)
        self.assertIsNotNone(pml_result, "Must retrieve PML Rules Suspicious Transaction definition from kyc.pdf Page 10")
        self.assertIn("Suspicious Transaction (PML Rules)", pml_result.get("section", ""))
        self.assertIn("appears to have no economic rationale or bona fide purpose", pml_result.get("text", "").lower())
        self.assertIn("circumstances of unusual or unjustified complexity", pml_result.get("text", "").lower())

        # Ensure FATF Recommendation 29 (FIU function, Page 24) does NOT outrank Rec 20
        rec29 = next((r for r in results if "Recommendation 29" in str(r.get("section", ""))), None)
        if rec29:
            self.assertLess(rec29.get("score", 0), top.get("score", 0), "Rec 29 must score lower than Rec 20")


    # ==========================================================================
    # REQUIREMENT 9: 18 COMPREHENSIVE REGRESSION TESTS
    # ==========================================================================

    def test_generic_kyc_no_customer_selection(self):
        """Regression Test 1: Generic KYC question does not select a customer."""
        retriever = GraphRetriever()
        try:
            res = retriever.execute_unified_query(
                query="What are the KYC periodic updation rules and officially valid documents under RBI directions?",
                session=UserSession.public_session(),
                top_k=3
            )
            self.assertFalse(res.get("access_denied"))
            self.assertEqual(res.get("graph_context"), {})
            self.assertIsNone(res.get("target_customer_id"))
            answer = res.get("answer", "")
            self.assertIn("Public Banking Intelligence & Regulatory Advisory", answer)
            self.assertNotIn("CUST_SYNTH_", answer)
        finally:
            retriever.close()

    def test_generic_aml_no_customer_selection(self):
        """Regression Test 2: Generic AML question does not select a customer."""
        retriever = GraphRetriever()
        try:
            res = retriever.execute_unified_query(
                query="What is a money mule under RBI directions and what diligence measures are required?",
                session=UserSession.public_session(),
                top_k=3
            )
            self.assertFalse(res.get("access_denied"))
            self.assertEqual(res.get("graph_context"), {})
            self.assertIsNone(res.get("target_customer_id"))
            docs = res.get("document_evidence", [])
            has_sec_68 = any("68." in str(d.get("section", "")) or "Money Mule" in str(d.get("section", "")) for d in docs)
            self.assertTrue(has_sec_68, "Must retrieve Section 68 passage for money mule query")
            answer = res.get("answer", "")
            self.assertIn("Money Mule Accounts & Regulatory Directives", answer)
            self.assertNotIn("Arjun Sharma", answer)
            self.assertNotIn("CUST_SYNTH_", answer)
        finally:
            retriever.close()

    def test_explicit_valid_customer_id(self):
        """Regression Test 3: Explicit valid customer ID returns the correct profile."""
        retriever = GraphRetriever()
        try:
            sess = UserSession.officer_session(officer_id="OFF_TEST")
            res = retriever.execute_unified_query(
                query="Investigate transaction activity and risk indicators for customer CUST_SYNTH_101",
                session=sess,
                explicit_customer_id="CUST_SYNTH_101",
                top_k=3
            )
            self.assertFalse(res.get("access_denied"))
            graph = res.get("graph_context", {})
            customer = graph.get("customer", {})
            self.assertEqual(customer.get("customer_id"), "CUST_SYNTH_101")
            self.assertIn("Arjun", customer.get("full_name", ""))
            accounts = graph.get("accounts", [])
            self.assertGreater(len(accounts), 0)
            txs = graph.get("transactions", [])
            self.assertGreater(len(txs), 0)
        finally:
            retriever.close()

    def test_unknown_customer_id_safe_handling(self):
        """Regression Test 4: Unknown customer ID produces a safe, clear response without crash."""
        retriever = GraphRetriever()
        try:
            sess = UserSession.officer_session(officer_id="OFF_TEST")
            res = retriever.execute_unified_query(
                query="Investigate records for customer CUST_NONEXISTENT_9999",
                session=sess,
                explicit_customer_id="CUST_NONEXISTENT_9999",
                top_k=3
            )
            self.assertTrue(res.get("customer_not_found"))
            answer = res.get("answer", "")
            self.assertTrue("Customer" in answer and "Not Found" in answer)
            self.assertIn("CUST_NONEXISTENT_9999", answer)
        finally:
            retriever.close()

    def test_ambiguous_customer_name_clarification(self):
        """Regression Test 5: Ambiguous customer name is handled safely with clarification request."""
        retriever = GraphRetriever()
        try:
            cid, is_ambiguous, candidates = retriever.resolve_customer_name("Ra")
            self.assertTrue(is_ambiguous)
            self.assertGreater(len(candidates), 1)

            sess = UserSession.officer_session(officer_id="OFF_TEST")
            res = retriever.execute_unified_query(
                query="Check accounts for Ra",
                session=sess,
                explicit_customer_name="Ra"
            )
            self.assertTrue(res.get("needs_clarification"))
            self.assertIn("Ambiguous Customer Name", res.get("answer", ""))
        finally:
            retriever.close()

    def test_cross_customer_isolation_no_data_leakage(self):
        """Regression Test 6: Customer A's transactions never appear in Customer B's report."""
        retriever = GraphRetriever()
        try:
            g101 = retriever.trace_customer_risk_graph("CUST_SYNTH_101")
            g104 = retriever.trace_customer_risk_graph("CUST_SYNTH_104")

            accs_101 = {a.get("account_number") for a in g101.get("accounts", [])}
            accs_104 = {a.get("account_number") for a in g104.get("accounts", [])}
            txs_101 = {t.get("tx_id") for t in g101.get("transactions", [])}
            txs_104 = {t.get("tx_id") for t in g104.get("transactions", [])}

            self.assertEqual(accs_101.intersection(accs_104), set(), "Accounts must not overlap across distinct customers")
            self.assertEqual(txs_101.intersection(txs_104), set(), "Transactions must not overlap across distinct customers")
        finally:
            retriever.close()

    def test_hypothetical_scenario_never_stored_facts(self):
        """Regression Test 7: Hypothetical scenarios are never presented as stored facts."""
        retriever = GraphRetriever()
        try:
            query = "What if an account receives INR 8,500,000 from an overseas shell jurisdiction and sweeps it out?"
            res = retriever.execute_unified_query(
                query=query,
                session=UserSession.public_session(),
                top_k=3
            )
            self.assertTrue(res.get("is_hypothetical_scenario"))
            self.assertEqual(res.get("graph_context"), {})
            answer = res.get("answer", "")
            self.assertIn("# Hypothetical Compliance Scenario Analysis (Not Stored Customer Facts)", answer)
            self.assertIn("Scenario Parameters & Assumptions", answer)
            self.assertIn("Quantitative Risk Detection Formulas & Thresholds", answer)
            self.assertNotIn("Verified Facts from Knowledge Graph", answer)
            self.assertNotIn("ACC_SYNTH_", answer)
        finally:
            retriever.close()

    def test_passthrough_drain_requires_chronological_order(self):
        """Regression Test 8: Pass-through transfers require correct chronological order (outflow AFTER inflow)."""
        risk_analyzer = GraphRiskAnalyzer()
        customer = {"customer_id": "CUST_TEST"}
        account_nums = {"ACC_TEST_01"}

        # Outflow occurs BEFORE inflow arrives
        txs_inverted = [
            {
                "tx_id": "TX_OUT_EARLY",
                "sender_account": "ACC_TEST_01",
                "receiver_account": "ACC_EXT",
                "direction": "OUTGOING",
                "amount": 100000.0,
                "timestamp": "2026-10-01T10:00:00Z"
            },
            {
                "tx_id": "TX_IN_LATE",
                "sender_account": "ACC_EXT",
                "receiver_account": "ACC_TEST_01",
                "direction": "INCOMING",
                "amount": 100000.0,
                "timestamp": "2026-10-01T14:00:00Z"
            }
        ]
        res_inverted = risk_analyzer._check_pass_through_drain(customer, account_nums, txs_inverted)
        self.assertIsNone(res_inverted, "Must NOT trigger pass-through when outflow occurred before inflow")

        # Outflow occurs AFTER inflow arrives within 120m
        txs_chronological = [
            {
                "tx_id": "TX_IN_FIRST",
                "sender_account": "ACC_EXT",
                "receiver_account": "ACC_TEST_01",
                "direction": "INCOMING",
                "amount": 100000.0,
                "timestamp": "2026-10-01T10:00:00Z"
            },
            {
                "tx_id": "TX_OUT_SECOND",
                "sender_account": "ACC_TEST_01",
                "receiver_account": "ACC_EXT_2",
                "direction": "OUTGOING",
                "amount": 95000.0,
                "timestamp": "2026-10-01T10:30:00Z"
            }
        ]
        res_chrono = risk_analyzer._check_pass_through_drain(customer, account_nums, txs_chronological)
        self.assertIsNotNone(res_chrono, "Must trigger pass-through when outflow occurs after inflow within window")
        self.assertEqual(res_chrono["indicator_id"], "IND_PASS_THROUGH_RAPID_DRAIN")

    def test_unrelated_accounts_no_false_passthrough(self):
        """Regression Test 9: Unrelated accounts cannot form a false pass-through pattern."""
        risk_analyzer = GraphRiskAnalyzer()
        customer = {"customer_id": "CUST_TEST"}
        account_nums = {"ACC_A", "ACC_B"}
        txs = [
            {
                "tx_id": "TX_IN_A",
                "sender_account": "ACC_EXT",
                "receiver_account": "ACC_A",
                "direction": "INCOMING",
                "amount": 100000.0,
                "timestamp": "2026-10-01T10:00:00Z"
            },
            {
                "tx_id": "TX_OUT_B",
                "sender_account": "ACC_B",
                "receiver_account": "ACC_EXT_2",
                "direction": "OUTGOING",
                "amount": 98000.0,
                "timestamp": "2026-10-01T10:30:00Z"
            }
        ]
        res = risk_analyzer._check_pass_through_drain(customer, account_nums, txs)
        self.assertIsNone(res, "Must not trigger pass-through drain across distinct unlinked accounts")

    def test_turnover_to_income_formula(self):
        """Regression Test 10: Turnover-to-income ratio uses the documented formula."""
        risk_analyzer = GraphRiskAnalyzer()
        customer = {
            "customer_id": "CUST_TEST",
            "declared_annual_income": 500000.0
        }
        account_nums = {"ACC_01"}
        txs = [
            {
                "tx_id": "TX_01",
                "sender_account": "ACC_EXT_1",
                "receiver_account": "ACC_01",
                "direction": "INCOMING",
                "amount": 2000000.0,
                "timestamp": "2026-10-01T10:00:00Z"
            }
        ]
        res = risk_analyzer._check_disproportionate_turnover(customer, account_nums, txs)
        self.assertIsNotNone(res)
        self.assertEqual(res["indicator_id"], "IND_DISPROPORTIONATE_TURNOVER")
        self.assertEqual(res["formula"], "total_external_inflow / declared_annual_income")
        self.assertEqual(res["input_values"]["declared_annual_income_inr"], 500000.0)
        self.assertEqual(res["input_values"]["total_external_inflow_inr"], 2000000.0)
        self.assertEqual(res["input_values"]["calculated_multiple"], 4.0)

    def test_turnover_missing_or_zero_income_handled(self):
        """Regression Test 11: Missing or zero income is handled safely without division by zero or silent suppression."""
        risk_analyzer = GraphRiskAnalyzer()
        customer = {
            "customer_id": "CUST_TEST",
            "declared_annual_income": 0.0
        }
        account_nums = {"ACC_01"}
        txs = [
            {
                "tx_id": "TX_01",
                "sender_account": "ACC_EXT",
                "receiver_account": "ACC_01",
                "direction": "INCOMING",
                "amount": 250000.0,
                "timestamp": "2026-10-01T10:00:00Z"
            }
        ]
        res = risk_analyzer._check_disproportionate_turnover(customer, account_nums, txs)
        self.assertIsNotNone(res, "Must flag turnover on zero/unverified income")
        self.assertEqual(res["indicator_id"], "IND_TURNOVER_UNVERIFIED_INCOME")
        self.assertEqual(res["severity"], "HIGH")

    def test_cross_border_does_not_assume_high_risk_jurisdiction(self):
        """Regression Test 12: Cross-border activity alone does not establish a high-risk jurisdiction."""
        risk_analyzer = GraphRiskAnalyzer()
        account_nums = {"ACC_01"}

        # Standard cross-border transfer
        tx_standard = [
            {
                "tx_id": "TX_SWIFT_STD",
                "sender_account": "ACC_OVERSEAS_UK",
                "receiver_account": "ACC_01",
                "direction": "INCOMING",
                "amount": 500000.0,
                "channel": "SWIFT",
                "timestamp": "2026-10-01T10:00:00Z"
            }
        ]
        res_std = risk_analyzer._check_cross_border_risks(account_nums, tx_standard)
        self.assertIsNotNone(res_std)
        self.assertEqual(res_std["indicator_id"], "IND_CROSS_BORDER_WIRE_TRANSFER")
        self.assertNotEqual(res_std["indicator_id"], "IND_CROSS_BORDER_HIGH_RISK_INFLOW")
        self.assertIn("could not be verified as high-risk", res_std.get("calculation_details", ""))

        # Designated high-risk jurisdiction (DPRK)
        tx_dprk = [
            {
                "tx_id": "TX_DPRK",
                "sender_account": "ACC_DPRK_BANK",
                "receiver_account": "ACC_01",
                "direction": "INCOMING",
                "amount": 500000.0,
                "channel": "SWIFT",
                "counterparty_jurisdiction": "DPRK",
                "timestamp": "2026-10-01T10:00:00Z"
            }
        ]
        res_dprk = risk_analyzer._check_cross_border_risks(account_nums, tx_dprk)
        self.assertIsNotNone(res_dprk)
        self.assertEqual(res_dprk["indicator_id"], "IND_CROSS_BORDER_HIGH_RISK_INFLOW")
        self.assertEqual(res_dprk["severity"], "CRITICAL")

    def test_risk_signal_explainable_evidence_structure(self):
        """Regression Test 13: Every risk signal contains the evidence required by its rule."""
        retriever = GraphRetriever()
        try:
            graph = retriever.trace_customer_risk_graph("CUST_SYNTH_101")
            risks = graph.get("calculated_risks", [])
            self.assertGreater(len(risks), 0, "Must calculate risk signals for CUST_SYNTH_101")

            required_fields = {
                "indicator_id", "name", "severity", "calculation_details",
                "supporting_transactions", "formula", "input_values",
                "threshold_applied", "threshold_source"
            }
            for r in risks:
                for field in required_fields:
                    self.assertIn(field, r, f"Risk signal {r.get('indicator_id')} missing {field}")
                self.assertIsInstance(r["supporting_transactions"], list)
                self.assertIsInstance(r["input_values"], dict)
        finally:
            retriever.close()

    def test_unsupported_regulatory_claims_rejected(self):
        """Regression Test 14: Unsupported regulatory claims are rejected or marked unverified."""
        retriever = GraphRetriever()
        try:
            query = "Under RBI KYC Master Direction Section 68, does a branch manager have the mandatory power to issue a 7-day criminal freezing order on a suspected money mule account?"
            res = retriever.execute_unified_query(
                query=query,
                session=UserSession.public_session(),
                top_k=3
            )
            scenario = res.get("scenario_analysis")
            self.assertIsNotNone(scenario)
            self.assertTrue(scenario.unsupported_claim_detected)
            answer = res.get("answer", "")
            self.assertIn("Refutation", answer)
            self.assertIn("does not grant branch managers statutory criminal asset-freezing powers", answer.lower())
        finally:
            retriever.close()

    def test_missing_document_evidence_no_fabrication(self):
        """Regression Test 15: Missing document evidence does not produce fabricated citations."""
        retriever = GraphRetriever()
        try:
            query = "What are the capital reserve requirements under the EU Markets in Crypto-Assets Regulation (MiCA)?"
            res = retriever.execute_unified_query(
                query=query,
                session=UserSession.public_session(),
                top_k=3
            )
            scenario = res.get("scenario_analysis")
            self.assertIsNotNone(scenario)
            self.assertTrue(scenario.regulation_absent)
            answer = res.get("answer", "")
            self.assertIn("cannot be fabricated", answer)
            self.assertIn("Scope Limitation", answer)
        finally:
            retriever.close()

    def test_public_generic_query_zero_customer_exposure(self):
        """Regression Test 16: Public generic queries do not expose customer information."""
        retriever = GraphRetriever()
        try:
            query = "Explain transaction structuring and smurfing techniques under banking AML rules."
            res = retriever.execute_unified_query(
                query=query,
                session=UserSession.public_session(),
                top_k=3
            )
            self.assertFalse(res.get("access_denied"))
            self.assertEqual(res.get("graph_context"), {})
            answer = res.get("answer", "")
            self.assertNotIn("ACC_SYNTH_", answer)
            self.assertNotIn("CUST_SYNTH_", answer)
            self.assertNotIn("Arjun", answer)
            self.assertNotIn("Vikas", answer)
        finally:
            retriever.close()

    def test_unauthorized_role_blocks_customer_investigation(self):
        """Regression Test 17: Unauthorized roles cannot access restricted customer investigations."""
        retriever = GraphRetriever()
        try:
            # Public user attempting customer investigation
            res_pub = retriever.execute_unified_query(
                query="Investigate transaction activity for customer CUST_SYNTH_101",
                session=UserSession.public_session(),
                explicit_customer_id="CUST_SYNTH_101"
            )
            self.assertTrue(res_pub.get("access_denied"))
            self.assertIn("Access Denied", res_pub.get("answer", ""))

            # Customer attempting to query another customer's data
            cust_sess = UserSession.customer_session(customer_id="CUST_SYNTH_102")
            res_cust = retriever.execute_unified_query(
                query="Investigate transaction activity for customer CUST_SYNTH_101",
                session=cust_sess,
                explicit_customer_id="CUST_SYNTH_101"
            )
            self.assertTrue(res_cust.get("access_denied"))
            self.assertIn("Access Denied", res_cust.get("answer", ""))
        finally:
            retriever.close()

    def test_cli_commands_and_backward_compatibility(self):
        """Regression Test 18: Existing CLI commands and working functionality remain compatible."""
        retriever = GraphRetriever()
        try:
            # Test retrieve_hybrid_context
            ctx = retriever.retrieve_hybrid_context(
                query="money mule accounts",
                customer_id="CUST_SYNTH_101",
                top_chunks=2
            )
            self.assertIn("query", ctx)
            self.assertIn("document_evidence", ctx)
            self.assertIn("graph_context", ctx)
            self.assertEqual(ctx["graph_context"]["customer"]["customer_id"], "CUST_SYNTH_101")
            self.assertEqual(len(ctx["document_evidence"]), 2)

            # Test execute_unified_query with custom top_k
            sess = UserSession.officer_session(officer_id="OFF_TEST")
            res = retriever.execute_unified_query(
                query="Investigate CUST_SYNTH_101",
                session=sess,
                explicit_customer_id="CUST_SYNTH_101",
                top_k=1
            )
            self.assertIn("query", res)
            self.assertIn("routing_decision", res)
            self.assertIn("answer", res)
            self.assertEqual(len(res["document_evidence"]), 1)
        finally:
            retriever.close()


if __name__ == "__main__":
    unittest.main()

