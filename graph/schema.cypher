// ==============================================================================
// GraphRAG Banking Compliance & Risk Intelligence System
// File: graph/schema.cypher
// Neo4j Graph Schema, Node Labels, Relationships, and Verification Queries
// ==============================================================================

// ------------------------------------------------------------------------------
// 1. NODE LABELS & KEY ATTRIBUTES
// ------------------------------------------------------------------------------
// :Document
//   - doc_id: String (Unique identifier, slug of document name)
//   - title: String (Document title)
//   - filename: String (Original PDF filename)
//   - source: String (Issuing authority e.g., RBI, FATF)
//   - category: String (Regulatory direction, working paper, annual report)
//   - publication_date: String (Date or period of publication)
//   - total_pages: Integer (Page count)
//   - sha256: String (SHA256 checksum)

// :Regulation
//   - reg_id: String (Unique identifier)
//   - name: String (Formal name of regulation/framework)
//   - jurisdiction: String (e.g., India, International)
//   - issuing_body: String (e.g., RBI, FATF)
//   - effective_date: String
//   - status: String (Active, Superseded, Advisory)

// :RegulatorySection
//   - section_id: String (e.g., RBI_KYC_SEC_35, FATF_REC_10)
//   - section_number: String (e.g., "Section 35", "Recommendation 10")
//   - title: String (Section title)
//   - chapter: String (Parent chapter or part)
//   - summary: String (Summary of provisions)

// :ComplianceRequirement
//   - req_id: String (Unique identifier)
//   - requirement_type: String (e.g., CDD, EDD, STR_REPORTING, CYBER_AUDIT)
//   - description: String (Actionable compliance obligation)
//   - mandatory: Boolean (True/False)
//   - penalty_risk: String (High, Medium, Low)

// :RiskIndicator
//   - indicator_id: String (e.g., IND_HIGH_VELOCITY_OUTFLOW, IND_CDD_DEFICIENT)
//   - name: String (Risk Indicator name)
//   - category: String (AML, Fraud, Cyber, Operational, Credit)
//   - severity: String (Critical, High, Medium, Low)
//   - description: String (Trigger condition description)

// :FraudPattern
//   - pattern_id: String (e.g., FP_MULE_RAPID_DISPERSAL, FP_ACCOUNT_TAKEOVER)
//   - name: String (Pattern name)
//   - typology: String (e.g., Layering, Pass-Through Account, Smurfing)
//   - description: String (Investigation signal description)

// :EvidenceChunk
//   - chunk_id: String (e.g., kyc_p45_0012)
//   - doc_id: String (Reference to parent Document)
//   - filename: String (Original file name)
//   - page_start: Integer (Source page start)
//   - page_end: Integer (Source page end)
//   - section_heading: String (Extracted header / section)
//   - char_count: Integer (Character count)
//   - word_count: Integer (Word count)
//   - chunk_hash: String (Deduplication hash)
//   - text: String (Actual chunk text passage)

// :Customer (Synthetic / Test data only)
//   - customer_id: String (e.g., CUST_1001)
//   - full_name: String
//   - kyc_status: String (VERIFIED, EXPIRED, PENDING, NON_COMPLIANT)
//   - risk_rating: String (HIGH, MEDIUM, LOW)
//   - cdd_tier: String (STANDARD, SIMPLIFIED, ENHANCED)
//   - occupation: String

// :Account (Synthetic / Test data only)
//   - account_number: String (e.g., ACC_200101)
//   - account_type: String (SAVINGS, CURRENT, ESCROW)
//   - status: String (ACTIVE, DORMANT, RESTRICTED, FROZEN)
//   - open_date: String
//   - currency: String (INR)

// :Transaction (Synthetic / Test data only)
//   - tx_id: String (e.g., TX_900101)
//   - amount: Float
//   - currency: String (INR)
//   - timestamp: String (ISO8601)
//   - channel: String (IMPS, NEFT, RTGS, UPI, ATM, SWIFT)
//   - type: String (TRANSFER_IN, TRANSFER_OUT, CASH_DEPOSIT, CASH_WITHDRAWAL)
//   - status: String (COMPLETED, PENDING, REVERSED, BLOCKED)
//   - risk_score: Float (0.0 to 1.0)


// ------------------------------------------------------------------------------
// 2. CORE RELATIONSHIPS
// ------------------------------------------------------------------------------
// Regulatory Knowledge Layer:
// (:Document)-[:EMBODIES_REGULATION]->(:Regulation)
// (:Document)-[:CONTAINS_SECTION]->(:RegulatorySection)
// (:RegulatorySection)-[:DEFINES_REQUIREMENT]->(:ComplianceRequirement)
// (:ComplianceRequirement)-[:ADDRESSES_RISK]->(:RiskIndicator)
// (:RiskIndicator)-[:INDICATES_PATTERN]->(:FraudPattern)
// (:EvidenceChunk)-[:CHUNK_FROM_DOCUMENT]->(:Document)
// (:RegulatorySection)-[:SUPPORTED_BY_CHUNK]->(:EvidenceChunk)

// Transaction / Evidence Layer:
// (:Customer)-[:OWNS_ACCOUNT]->(:Account)
// (:Account)-[:SENT_TRANSACTION]->(:Transaction)
// (:Transaction)-[:TO_ACCOUNT]->(:Account)

// Bridging Knowledge to Synthetic Events (Investigation Triggers):
// (:Transaction)-[:TRIGGERS_INDICATOR]->(:RiskIndicator)
// (:Customer)-[:EXHIBITS_PATTERN]->(:FraudPattern)


// ------------------------------------------------------------------------------
// 3. SAMPLE VERIFICATION QUERIES
// ------------------------------------------------------------------------------

// Query 1: Verify total node counts per label
// MATCH (n) RETURN labels(n) AS Label, count(n) AS NodeCount ORDER BY NodeCount DESC;

// Query 2: Find all sections and supporting chunks for a specific regulation
// MATCH (r:Regulation)<-[:EMBODIES_REGULATION]-(d:Document)-[:CONTAINS_SECTION]->(s:RegulatorySection)
// OPTIONAL MATCH (s)-[:SUPPORTED_BY_CHUNK]->(c:EvidenceChunk)
// RETURN r.name, s.section_number, s.title, c.chunk_id, c.page_start LIMIT 20;

// Query 3: Trace a risk indicator from a detected transaction up to the governing regulation
// MATCH (t:Transaction)-[:TRIGGERS_INDICATOR]->(k:RiskIndicator)<-[:ADDRESSES_RISK]-(req:ComplianceRequirement)<-[:DEFINES_REQUIREMENT]-(s:RegulatorySection)<-[:CONTAINS_SECTION]-(d:Document)
// RETURN t.tx_id, t.amount, k.name, req.description, s.section_number, d.filename;

// Query 4: Retrieve Customer Due Diligence gaps and affected accounts
// MATCH (c:Customer)-[:OWNS_ACCOUNT]->(a:Account)-[:SENT_TRANSACTION]->(t:Transaction)-[:TRIGGERS_INDICATOR]->(k:RiskIndicator)
// WHERE c.kyc_status <> 'VERIFIED' OR k.category = 'AML'
// RETURN c.customer_id, c.kyc_status, a.account_number, t.tx_id, t.amount, k.name;
