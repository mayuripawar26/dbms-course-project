"""
app.py

Streamlit Web UI for GraphRAG Banking Compliance & Risk Intelligence System.
Supports 3 Unified Access Modes:
- Mode A: Public Banking Intelligence Assistant (no authentication, regulatory knowledge only)
- Mode B: Customer Banking Portal (authenticated session, personal accounts, strict tenant isolation)
- Mode C: Compliance Officer Investigation Console (multi-entity tracing, Cypher audits, 8-section reports)
"""

import os
import sys
import json
import streamlit as st
import pandas as pd
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from retrieval.graph_retriever import GraphRetriever
from retrieval.query_router import UserSession, UserRole, QueryIntent

st.set_page_config(
    page_title="Banking Compliance & Risk Intelligence",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .report-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .report-subtitle {
        font-size: 1.05rem;
        color: #4B5563;
        margin-bottom: 1.2rem;
    }
    .badge-critical {
        background-color: #FEE2E2;
        color: #991B1B;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-high {
        background-color: #FFEDD5;
        color: #9A3412;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-medium {
        background-color: #FEF3C7;
        color: #92400E;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-binding {
        background-color: #DBEAFE;
        color: #1E40AF;
        padding: 3px 6px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.75rem;
    }
    .badge-auth {
        background-color: #D1FAE5;
        color: #065F46;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-public {
        background-color: #E0E7FF;
        color: #3730A3;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .chip-btn {
        margin: 2px;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_retriever():
    """Cache the GraphRetriever instance to avoid reloading BM25 and re-connecting Neo4j."""
    return GraphRetriever()


def render_sidebar(retriever: GraphRetriever):
    """Render unified sidebar controls and system health status."""
    with st.sidebar:
        st.header("⚙️ Platform Navigation")

        mode = st.radio(
            "Access Mode:",
            [
                "🌐 Mode A: Public Assistant",
                "👤 Mode B: Customer Portal",
                "🛡️ Mode C: Compliance Officer",
                "🧪 Mode D: Hypothetical Simulation",
            ],
            index=0,
            help="Select access role: Public (open access), Customer (authenticated tenant), Officer (full audit), or Simulation (hypothetical transactions)."
        )

        st.divider()
        st.subheader("System Status")
        neo4j_status = "🟢 Connected (Neo4j Sandbox)" if retriever.driver else "🟠 Offline (Local Index Fallback)"
        st.caption(f"**Knowledge Graph:** {neo4j_status}")
        st.caption(f"**Regulatory Corpus:** {retriever.doc_retriever.total_docs} chunks")
        st.caption(f"**Synthetic Scenarios:** {len(retriever.local_graph.get('customers', {}))} profiles")

        st.divider()
        st.subheader("Retrieval Controls")
        top_k = st.slider("Regulatory Chunks (Top-K):", min_value=1, max_value=8, value=3)

        doc_filter_opts = [
            "All Documents",
            "kyc.pdf",
            "cyber security.pdf",
            "fatf-recommendations last updated june 2026.pdf",
            "credit information.pdf",
            "operational guidelines.pdf",
            "interest rates.pdf",
            "supervisory credit.pdf",
            "Demonitization.pdf",
        ]
        doc_filter_sel = st.selectbox("Document Filter (Optional):", doc_filter_opts)
        doc_filter = None if doc_filter_sel == "All Documents" else doc_filter_sel

        st.divider()
        st.markdown("**Governance & Disclaimer:**")
        st.caption(
            "All customer entities and transactions are fictional synthetic benchmarks. "
            "Risk signals serve as internal inquiry triggers and do not imply criminal guilt."
        )

        return mode, top_k, doc_filter


def render_public_mode(retriever: GraphRetriever, top_k: int, doc_filter: str):
    """Mode A: Public Banking Intelligence Assistant (no authentication, zero customer records)."""
    st.markdown('<span class="badge-public">MODE A: PUBLIC ACCESS (UNAUTHENTICATED)</span>', unsafe_allow_html=True)
    st.markdown("### 🌐 Public Banking Intelligence & Safety Assistant")
    st.write(
        "Ask general questions about banking regulations, digital payment security, fraud prevention, "
        "KYC/AML standards, and consumer rights under RBI guidelines. **No login or profile selection required.**"
    )

    # Preset Educational Question Chips
    st.markdown("**Suggested General Banking & Fraud Inquiries:**")
    suggested_chips = [
        "What is UPI fraud and what precautions should customers take?",
        "What is a money mule under RBI guidelines?",
        "What enhanced due diligence measures apply to non-face-to-face customer onboarding under paragraph 44?",
        "What due diligence, senior-management approval, and monitoring measures apply to PEPs under paragraph 45?",
        "What is customer liability for unauthorized electronic banking transactions?",
        "What are the KYC requirements for opening a bank account in India?",
    ]

    cols = st.columns(3)
    for i, chip in enumerate(suggested_chips):
        col = cols[i % 3]
        if col.button(chip, key=f"chip_pub_{i}", use_container_width=True):
            st.session_state["pub_query"] = chip

    current_val = st.session_state.get("pub_query", "What is UPI fraud and what precautions should customers take?")

    query_input = st.text_area(
        "Enter Your Banking or Regulatory Question:",
        value=current_val,
        height=85,
        key="public_text_input"
    )

    if st.button("🔍 Ask Banking Assistant", type="primary", use_container_width=True):
        if not query_input.strip():
            st.warning("Please enter a question.")
            return

        with st.spinner("Searching regulatory documents and synthesizing verified guidance..."):
            session = UserSession.public_session()
            context = retriever.execute_unified_query(
                query=query_input,
                session=session,
                top_k=top_k,
                document_filter=doc_filter,
            )

        tab_ans, tab_docs = st.tabs(["💡 Verified Advisory", "📚 Regulatory Passages & Citations"])

        with tab_ans:
            if context.get("is_hypothetical_scenario"):
                st.info("🧪 **Hypothetical Compliance Scenario Simulation**: Independent of stored customer facts. No private customer records evaluated or exposed.")
            st.markdown(context.get("answer", ""))

        with tab_docs:
            docs = context.get("document_evidence", [])
            st.subheader(f"Retrieved Regulatory Evidence ({len(docs)} Chunks)")
            for idx, chunk in enumerate(docs, 1):
                citation = chunk.get("citation", "Citation unavailable")
                score = chunk.get("score", 0.0)
                auth = chunk.get("authority_level", "INFORMATIONAL")
                doc_type = chunk.get("document_type", "Banking Regulation")

                with st.expander(f"[{idx}] {citation} (Score: {score:.2f})", expanded=True):
                    st.markdown(f"<span class='badge-binding'>{auth}</span> &nbsp; **{doc_type}**", unsafe_allow_html=True)
                    st.markdown(f"> {chunk.get('text', '')}")


def render_customer_mode(retriever: GraphRetriever, top_k: int, doc_filter: str):
    """Mode B: Customer Banking Portal (authenticated session, personal accounts, strict tenant isolation)."""
    st.markdown('<span class="badge-auth">MODE B: AUTHENTICATED CUSTOMER PORTAL</span>', unsafe_allow_html=True)
    st.markdown("### 👤 Personal Customer Banking Assistant")
    st.write(
        "Access your personal accounts, review transaction statements, and receive plain-language "
        "explanations of flagged activities under authenticated tenant isolation."
    )

    # Synthetic Customer Profile Selector
    customers = retriever.local_graph.get("customers", {})
    customer_options = {
        f"{c.get('full_name')} ({cid})": cid
        for cid, c in customers.items()
    }

    col_prof, col_status = st.columns([2, 1])
    with col_prof:
        selected_label = st.selectbox(
            "Simulated Customer Login:",
            list(customer_options.keys()),
            index=0
        )
        active_cid = customer_options[selected_label]
        active_cust = customers.get(active_cid, {})

    with col_status:
        st.markdown(
            f"<div style='margin-top:25px;'>"
            f"<span class='badge-auth'>🟢 Session Authenticated</span><br>"
            f"<strong>Tenant ID:</strong> <code>{active_cid}</code>"
            f"</div>",
            unsafe_allow_html=True
        )

    # Customer Overview Card
    with st.expander("📊 Account Summary & Active Records", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Account Holder", active_cust.get("full_name", "N/A"))
        c2.metric("KYC Status", active_cust.get("kyc_status", "N/A"))
        c3.metric("Customer Type", active_cust.get("customer_type", "N/A"))
        inc = active_cust.get("declared_annual_income_inr")
        c4.metric("Declared Income", f"INR {inc:,.2f}" if inc else "Not declared")

        # Linked Accounts
        trace = retriever.trace_customer_risk_graph(active_cid)
        accs = trace.get("accounts", [])
        txs = trace.get("transactions", [])
        calc_risks = trace.get("calculated_risks", [])

        if accs:
            st.markdown(f"**Linked Accounts ({len(accs)}):**")
            acc_df = pd.DataFrame([
                {
                    "Account Number": a.get("account_number"),
                    "Type": a.get("type", a.get("account_type")),
                    "Status": a.get("status"),
                    "Balance (INR)": f"{a.get('balance_inr', 0.0):,.2f}"
                }
                for a in accs
            ])
            st.dataframe(acc_df, use_container_width=True)

        if txs:
            st.markdown(f"**Recent Recorded Transactions ({len(txs)}):**")
            tx_df = pd.DataFrame([
                {
                    "Tx ID": t.get("tx_id"),
                    "Amount (INR)": f"{t.get('amount_inr', t.get('amount', 0)):,.2f}",
                    "Channel": t.get("channel"),
                    "Direction": t.get("direction", t.get("type")),
                    "Timestamp": t.get("timestamp")
                }
                for t in txs
            ])
            st.dataframe(tx_df, use_container_width=True)

        if calc_risks:
            st.warning(f"⚠️ Your account has {len(calc_risks)} risk signal(s) pending review.")

    st.divider()

    # Customer Inquiries
    st.markdown("**Suggested Customer Inquiries:**")
    cust_chips = [
        "What is my current account balance and recent transaction history?",
        "Why were my recent transactions flagged?",
        "Explain money mule fraud and tell me whether my transactions resemble that pattern.",
        "What are my rights if an electronic transfer on my account was unauthorized?",
    ]

    cols = st.columns(2)
    for i, chip in enumerate(cust_chips):
        col = cols[i % 2]
        if col.button(chip, key=f"chip_cust_{i}", use_container_width=True):
            st.session_state["cust_query"] = chip

    current_val = st.session_state.get(
        "cust_query",
        "What is my current account balance and recent transaction history?"
    )

    query_input = st.text_area(
        "Ask a Question About Your Account or Regulations:",
        value=current_val,
        height=80,
        key="cust_text_input"
    )

    if st.button("💬 Ask Customer Assistant", type="primary", use_container_width=True):
        if not query_input.strip():
            st.warning("Please enter a question.")
            return

        with st.spinner("Verifying credentials, enforcing tenant isolation, and generating response..."):
            session = UserSession.customer_session(
                customer_id=active_cid,
                customer_name=active_cust.get("full_name")
            )
            context = retriever.execute_unified_query(
                query=query_input,
                session=session,
                top_k=top_k,
                document_filter=doc_filter,
            )

        tab_ans, tab_docs = st.tabs(["💬 Customer Response", "📚 Supporting Regulatory Guidance"])

        with tab_ans:
            st.markdown(context.get("answer", ""))

        with tab_docs:
            docs = context.get("document_evidence", [])
            if docs:
                for idx, chunk in enumerate(docs, 1):
                    citation = chunk.get("citation", "Citation unavailable")
                    with st.expander(f"[{idx}] {citation}"):
                        st.markdown(f"> {chunk.get('text', '')}")
            else:
                st.info("No external regulatory documents were required for this inquiry.")


def render_officer_mode(retriever: GraphRetriever, top_k: int, doc_filter: str):
    """Mode C: Compliance Officer Investigation Console (multi-entity tracing, Cypher audit, 8-section report)."""
    st.markdown('<span class="badge-critical">MODE C: COMPLIANCE OFFICER INVESTIGATION CONSOLE</span>', unsafe_allow_html=True)
    st.markdown("### 🛡️ Compliance Officer Investigation & Risk Intelligence Console")
    st.write(
        "Authorized portal for forensic financial intelligence, multi-customer knowledge graph tracing, "
        "dynamic AML rule calculation, and verifiable 8-section regulatory compliance reporting."
    )

    scenario_options = {
        "1. Money Mule / Rapid Dispersal (Arjun Sharma)": "CUST_SYNTH_101",
        "2. Unauthorized UPI Transactions (Priya Patel)": "CUST_SYNTH_102",
        "3. Potential Account Takeover (Vikram Mehta)": "CUST_SYNTH_103",
        "4. Cross-Border Shell Company (Apex Global Consultancy)": "CUST_SYNTH_104",
        "5. Expired KYC Active Credits (Bharat Tech)": "CUST_SYNTH_105",
        "6. Circular Fund Transfers / Round-Tripping (Zenith Global)": "CUST_SYNTH_106",
        "7. Loan Inconsistencies & Diversion (BlueStar Infra)": "CUST_SYNTH_107",
        "Custom (Manual Input)": "",
    }

    col_scen, col_man = st.columns([2, 1])
    with col_scen:
        selected_preset = st.selectbox(
            "Select Benchmark Risk Scenario:",
            list(scenario_options.keys()),
            index=0
        )
        preset_cid = scenario_options[selected_preset]

    with col_man:
        manual_cust = st.text_input(
            "Target Customer ID or Name:",
            value=preset_cid if preset_cid else "Arjun Sharma"
        )

    default_queries = {
        "CUST_SYNTH_101": "Explain why this account may be a money mule, show the transaction calculations, identify the supporting evidence, and distinguish suspicious activity from proof of fraud.",
        "CUST_SYNTH_102": "What customer protection and reporting steps apply to unauthorized electronic banking transactions?",
        "CUST_SYNTH_103": "What risk indicators suggest digital account takeover and what RBI cybersecurity rules apply?",
        "CUST_SYNTH_104": "Which transactions require enhanced due diligence and what are the CDD requirements for overseas remittances?",
        "CUST_SYNTH_105": "What regulatory actions are required when active transactions continue on an account with expired KYC?",
        "CUST_SYNTH_106": "What transaction patterns indicate circular routing or round-tripping under AML standards?",
        "CUST_SYNTH_107": "What supervisory credit rules govern loan document inconsistencies and fund diversion?",
    }

    preset_default_q = default_queries.get(
        preset_cid,
        "Which transactions require enhanced due diligence under applicable rules?"
    )

    query_input = st.text_area(
        "Investigation Query / Directive:",
        value=preset_default_q,
        height=80,
        key="officer_text_input"
    )

    if st.button("🚀 Run Compliance Investigation", type="primary", use_container_width=True):
        if not query_input.strip():
            st.warning("Please enter an investigation query.")
            return

        with st.spinner("Analyzing knowledge graph, executing dynamic risk calculations, and retrieving regulatory evidence..."):
            session = UserSession.officer_session(
                officer_id="OFF_CONSOLE_01",
                department="Financial Crime Compliance"
            )

            cid_to_use = None
            if manual_cust.strip():
                cid_to_use = retriever.find_customer_by_name(manual_cust.strip())
                if not cid_to_use:
                    st.error(f"Customer '{manual_cust}' could not be resolved safely to a unique customer ID in the graph.")
                    return

            context = retriever.execute_unified_query(
                query=query_input,
                session=session,
                explicit_customer_id=cid_to_use,
                top_k=top_k,
                document_filter=doc_filter,
            )

        tab_report, tab_graph, tab_evidence, tab_prompt = st.tabs([
            "📋 Investigation Report",
            "🕸️ Knowledge Graph & Entities",
            "📚 Regulatory Evidence (BM25)",
            "🔧 Grounding Prompt & Audit Trail"
        ])

        with tab_report:
            st.markdown(context.get("answer", ""))

        with tab_graph:
            graph_data = context.get("graph_context", {})
            cust_info = graph_data.get("customer", {})
            accs = graph_data.get("accounts", [])
            txs = graph_data.get("transactions", [])
            calc_risks = graph_data.get("calculated_risks", [])

            st.subheader(f"Customer Entity: {cust_info.get('full_name', 'N/A')}")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Customer ID", cust_info.get("customer_id", "N/A"))
            col2.metric("Customer Type", cust_info.get("customer_type", "N/A"))
            col3.metric("KYC Status", cust_info.get("kyc_status", "N/A"))
            inc_val = cust_info.get("declared_annual_income_inr")
            col4.metric("Declared Annual Income", f"INR {inc_val:,.2f}" if inc_val else "Not declared")

            st.divider()
            st.subheader(f"Dynamically Calculated Risk Signals ({len(calc_risks)})")
            if calc_risks:
                for sig in calc_risks:
                    sev = sig.get("severity", "HIGH").upper()
                    sev_class = "badge-critical" if sev == "CRITICAL" else ("badge-high" if sev == "HIGH" else "badge-medium")
                    with st.expander(f"[{sev}] {sig.get('name')}", expanded=True):
                        st.markdown(f"<span class='{sev_class}'>{sev} RISK</span> — **{sig.get('indicator_id')}**", unsafe_allow_html=True)
                        st.write(f"**Mathematical / Temporal Detail:** {sig.get('calculation_details')}")
                        st.write(f"**Investigation Guidance:** {sig.get('investigation_guidance')}")
                        st.caption(f"Supporting Transactions: {', '.join(sig.get('supporting_transactions', []))}")
            else:
                st.info("No abnormal velocity, circularity, or KYC breaches detected.")

            st.divider()
            col_acc, col_tx = st.columns([1, 1])
            with col_acc:
                st.subheader(f"Linked Accounts ({len(accs)})")
                if accs:
                    acc_df = pd.DataFrame([
                        {
                            "Account Number": a.get("account_number"),
                            "Type": a.get("type", a.get("account_type")),
                            "Status": a.get("status"),
                            "Balance (INR)": f"{a.get('balance_inr', 0.0):,.2f}"
                        }
                        for a in accs
                    ])
                    st.dataframe(acc_df, use_container_width=True)
                else:
                    st.write("No linked accounts.")

            with col_tx:
                st.subheader(f"Recorded Transactions ({len(txs)})")
                if txs:
                    tx_df = pd.DataFrame([
                        {
                            "Tx ID": t.get("tx_id"),
                            "Amount (INR)": f"{t.get('amount_inr', t.get('amount', 0)):,.2f}",
                            "Channel": t.get("channel"),
                            "Direction": t.get("direction", t.get("type")),
                            "Timestamp": t.get("timestamp")
                        }
                        for t in txs
                    ])
                    st.dataframe(tx_df, use_container_width=True)
                else:
                    st.write("No recorded transactions.")

        with tab_evidence:
            docs = context.get("document_evidence", [])
            st.subheader(f"Verified Regulatory Passages ({len(docs)})")
            for idx, chunk in enumerate(docs, 1):
                citation = chunk.get("citation", "Citation unavailable")
                score = chunk.get("score", 0.0)
                auth = chunk.get("authority_level", "INFORMATIONAL")
                doc_type = chunk.get("document_type", "Banking Regulation")

                with st.expander(f"[{idx}] {citation} (Score: {score:.2f})", expanded=True):
                    st.markdown(f"<span class='badge-binding'>{auth}</span> &nbsp; **{doc_type}**", unsafe_allow_html=True)
                    st.markdown(f"> {chunk.get('text', '')}")
                    st.caption(f"Score Metric: {chunk.get('score_explanation')}")

        with tab_prompt:
            st.subheader("Configured System Prompt & Evidence Payload")
            prompt = retriever.format_llm_prompt(context)
            st.code(prompt, language="markdown")


def render_simulation_mode(retriever: GraphRetriever, top_k: int, doc_filter: str):
    """Mode D: Hypothetical Compliance Scenario Simulation (quarantined from actual customer database records)."""
    st.markdown('<span class="badge-public">MODE D: HYPOTHETICAL AML SCENARIO SIMULATION</span>', unsafe_allow_html=True)
    st.markdown("### 🧪 Hypothetical Scenario & Typology Simulator")
    st.write(
        "Evaluate hypothetical financial transactions, complex AML typologies, and emerging risk patterns "
        "against indexed RBI KYC Directions, PMLA rules, and FATF recommendations. "
        "**Guaranteed Zero Database Contamination**: Simulated facts remain strictly isolated from customer graph records."
    )

    st.markdown("**Select Benchmark Simulation Typology:**")
    sim_chips = [
        "A hypothetical small retail business receives INR 850000 from an overseas account and transfers most of the amount to three unrelated domestic accounts within 30 minutes. The source of funds is unclear. Identify potential AML risk indicators, explain what additional evidence is needed, retrieve applicable RBI KYC and PMLA-related evidence from the indexed knowledge base, and assess whether further investigation or consideration of suspicious transaction reporting may be appropriate. Clearly separate hypothetical facts from actual database records. Do not invent transactions, customers, citations, or legal obligations.",
        "A hypothetical customer conducts multiple cash deposits of INR 49,000 across five branches on the same day to avoid PAN reporting thresholds. Analyze structuring indicators, applicable RBI cash transaction limits, and CTR/STR reporting obligations.",
        "A newly incorporated entity receives high-volume wire transfers from a high-risk jurisdiction and immediately routes them to shell entities with no commercial justification. Assess countermeasures under FATF Recommendation 19 and RBI KYC directions.",
        "A corporate customer requests transactions involving virtual digital assets (VDAs) through an offshore crypto exchange. Analyze regulatory obligations under PMLA reporting entities and FATF guidance."
    ]

    cols = st.columns(2)
    for i, chip in enumerate(sim_chips):
        col = cols[i % 2]
        title = chip[:75] + "..."
        if col.button(f"Typology {i+1}: {title}", key=f"chip_sim_{i}", use_container_width=True):
            st.session_state["sim_query"] = chip

    current_val = st.session_state.get(
        "sim_query",
        sim_chips[0]
    )

    query_input = st.text_area(
        "Hypothetical Scenario Description / Typology Details:",
        value=current_val,
        height=120,
        key="sim_text_input"
    )

    if st.button("⚡ Run Typology Simulation", type="primary", use_container_width=True):
        if not query_input.strip():
            st.warning("Please enter a scenario description.")
            return

        with st.spinner("Analyzing typology, retrieving regulatory provisions, and synthesizing assessment..."):
            session = UserSession.public_session()
            context = retriever.execute_unified_query(
                query=query_input,
                session=session,
                top_k=top_k,
                document_filter=doc_filter,
            )

        st.info("🔒 **Sandbox Active**: Executed in unauthenticated sandbox. Customer database was not queried; no live customer records were accessed, altered, or revealed.")

        tab_ans, tab_breakdown, tab_evidence, tab_prompt = st.tabs([
            "📋 Compliance Assessment",
            "🔍 Risk Signal Breakdown",
            "📚 Statutory Authorities & Evidence",
            "📝 Formatted Prompt Payload"
        ])

        with tab_ans:
            st.markdown(context.get("answer", ""))

        with tab_breakdown:
            scenario = context.get("scenario_analysis")
            st.subheader("Automated Typology & Scenario Extraction")
            col1, col2, col3 = st.columns(3)
            col1.metric("Hypothetical Status", "SIMULATION" if context.get("is_hypothetical_scenario") else "Standard")
            col2.metric("Intent Detected", str(context.get("intent", "UNKNOWN")))
            col3.metric("Database Access", "ZERO (Isolated)")

            if scenario:
                if hasattr(scenario, "calculations") and scenario.calculations:
                    st.markdown("**Deterministic Compliance Calculations:**")
                    for calc in scenario.calculations:
                        st.markdown(f"- **{calc.metric_name}:** `{calc.result_str}`")
                        st.caption(f"Formula: `{calc.formula}` | Status: `{calc.status}` | Notes: {calc.notes}")

                if hasattr(scenario, "missing_information") and scenario.missing_information:
                    st.markdown("**Identified Evidence Gaps & Missing Information:**")
                    for gap in scenario.missing_information:
                        st.markdown(f"- ⚠️ {gap}")

                if hasattr(scenario, "identified_patterns") and scenario.identified_patterns:
                    st.markdown("**Detected Typology Patterns:**")
                    for pat in scenario.identified_patterns:
                        st.markdown(f"- 🚩 `{pat}`")
                if hasattr(scenario, "key_facts") and scenario.key_facts:
                    st.markdown("**Extracted Scenario Facts:**")
                    for k, v in scenario.key_facts.items():
                        st.markdown(f"- **{k}**: {v}")

        with tab_evidence:
            docs = context.get("document_evidence", [])
            st.subheader(f"Retrieved Regulatory Evidence ({len(docs)} Chunks)")
            for idx, chunk in enumerate(docs, 1):
                citation = chunk.get("citation", "Citation unavailable")
                score = chunk.get("score", 0.0)
                auth = chunk.get("authority_level", "INFORMATIONAL")
                doc_type = chunk.get("document_type", "Banking Regulation")

                with st.expander(f"[{idx}] {citation} (Score: {score:.2f})", expanded=True):
                    st.markdown(f"<span class='badge-binding'>{auth}</span> &nbsp; **{doc_type}**", unsafe_allow_html=True)
                    st.markdown(f"> {chunk.get('text', '')}")
                    st.caption(f"Score Metric: {chunk.get('score_explanation')}")

        with tab_prompt:
            st.subheader("Configured System Prompt & Evidence Payload")
            prompt = retriever.format_llm_prompt(context)
            st.code(prompt, language="markdown")


def main():
    retriever = get_retriever()

    st.markdown('<div class="report-title">GraphRAG Banking Compliance & Risk Intelligence</div>', unsafe_allow_html=True)
    st.markdown('<div class="report-subtitle">Multi-Modal Regulatory Reasoning across RBI Directions, FATF Standards, and Customer-Transaction Knowledge Graphs</div>', unsafe_allow_html=True)

    mode, top_k, doc_filter = render_sidebar(retriever)

    if mode == "🌐 Mode A: Public Assistant":
        render_public_mode(retriever, top_k, doc_filter)
    elif mode == "👤 Mode B: Customer Portal":
        render_customer_mode(retriever, top_k, doc_filter)
    elif mode == "🛡️ Mode C: Compliance Officer":
        render_officer_mode(retriever, top_k, doc_filter)
    elif mode == "🧪 Mode D: Hypothetical Simulation":
        render_simulation_mode(retriever, top_k, doc_filter)


if __name__ == "__main__":
    main()

