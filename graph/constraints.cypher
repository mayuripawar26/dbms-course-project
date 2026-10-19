// ==============================================================================
// GraphRAG Banking Compliance & Risk Intelligence System
// File: graph/constraints.cypher
// Uniqueness constraints and performance indexes for Neo4j
// ==============================================================================

// 1. Uniqueness Constraints (Neo4j 5.x / 6.x syntax)
CREATE CONSTRAINT doc_id_unique IF NOT EXISTS
FOR (d:Document) REQUIRE d.doc_id IS UNIQUE;

CREATE CONSTRAINT reg_id_unique IF NOT EXISTS
FOR (r:Regulation) REQUIRE r.reg_id IS UNIQUE;

CREATE CONSTRAINT section_id_unique IF NOT EXISTS
FOR (s:RegulatorySection) REQUIRE s.section_id IS UNIQUE;

CREATE CONSTRAINT req_id_unique IF NOT EXISTS
FOR (c:ComplianceRequirement) REQUIRE c.req_id IS UNIQUE;

CREATE CONSTRAINT indicator_id_unique IF NOT EXISTS
FOR (k:RiskIndicator) REQUIRE k.indicator_id IS UNIQUE;

CREATE CONSTRAINT pattern_id_unique IF NOT EXISTS
FOR (f:FraudPattern) REQUIRE f.pattern_id IS UNIQUE;

CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS
FOR (ch:EvidenceChunk) REQUIRE ch.chunk_id IS UNIQUE;

CREATE CONSTRAINT customer_id_unique IF NOT EXISTS
FOR (cust:Customer) REQUIRE cust.customer_id IS UNIQUE;

CREATE CONSTRAINT account_number_unique IF NOT EXISTS
FOR (a:Account) REQUIRE a.account_number IS UNIQUE;

CREATE CONSTRAINT tx_id_unique IF NOT EXISTS
FOR (t:Transaction) REQUIRE t.tx_id IS UNIQUE;

// 2. Lookup & Performance Indexes
CREATE INDEX doc_filename_idx IF NOT EXISTS
FOR (d:Document) ON (d.filename);

CREATE INDEX section_num_idx IF NOT EXISTS
FOR (s:RegulatorySection) ON (s.section_number);

CREATE INDEX chunk_doc_id_idx IF NOT EXISTS
FOR (ch:EvidenceChunk) ON (ch.doc_id);

CREATE INDEX chunk_page_start_idx IF NOT EXISTS
FOR (ch:EvidenceChunk) ON (ch.page_start);

CREATE INDEX req_type_idx IF NOT EXISTS
FOR (c:ComplianceRequirement) ON (c.requirement_type);

CREATE INDEX risk_category_idx IF NOT EXISTS
FOR (k:RiskIndicator) ON (k.category);

CREATE INDEX tx_timestamp_idx IF NOT EXISTS
FOR (t:Transaction) ON (t.timestamp);

CREATE INDEX tx_type_idx IF NOT EXISTS
FOR (t:Transaction) ON (t.type);
