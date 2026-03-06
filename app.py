import streamlit as st
import anthropic
import json
import pandas as pd
from datetime import datetime

# --- Page Config ---
st.set_page_config(
    page_title="NL-to-SQL Pro",
    page_icon="🧠",
    layout="wide"
)

# --- Constants ---
DIALECTS = ["PostgreSQL", "Snowflake", "BigQuery", "MySQL", "SQL Server", "Redshift"]

SAMPLE_SCHEMA = """customers (id INT PK, name VARCHAR, email VARCHAR [PII], country VARCHAR, created_at TIMESTAMP)
orders (id INT PK, customer_id INT FK, total DECIMAL, status VARCHAR, created_at TIMESTAMP)
order_items (id INT PK, order_id INT FK, product_id INT FK, quantity INT, unit_price DECIMAL)
products (id INT PK, name VARCHAR, category VARCHAR, price DECIMAL, stock INT)
employees (id INT PK, name VARCHAR, email VARCHAR [PII], salary DECIMAL [PII], department VARCHAR)"""

# --- Session State Init ---
if "audit_log" not in st.session_state:
    st.session_state.audit_log = []

# --- Anthropic Client ---
client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])

# --- Core Function ---
def generate_sql(question: str, schema: str, dialect: str) -> dict:
    system_prompt = f"""You are an expert data architect and SQL specialist with 20 years of experience.
Given a database schema and a natural language question, return ONLY valid JSON with this structure:
{{
  "sql": "the generated SQL query for {dialect}",
  "explanation": "plain English explanation of what the query does step by step",
  "optimization_tips": ["tip1", "tip2"],
  "pii_warnings": [{{"field": "fieldname", "table": "tablename", "severity": "high|medium|low", "note": "explanation"}}],
  "governance_warnings": ["any data governance concerns"],
  "complexity": "Simple|Moderate|Complex",
  "estimated_cost": "Low|Medium|High"
}}
Return empty arrays if nothing to report. Tailor SQL syntax strictly to {dialect}."""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system=system_prompt,
        messages=[{"role": "user", "content": f"Schema:\n{schema}\n\nQuestion: {question}"}]
    )

    raw = message.content[0].text.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)

# --- UI ---
st.markdown("# 🧠 NL-to-SQL Pro")
st.markdown("*Schema-aware · Multi-dialect · Governance-ready · Built by a Data Architect*")
st.divider()

tab1, tab2 = st.tabs(["⚡ SQL Generator", "📋 Audit Log"])

with tab1:
    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("⚙️ Configuration")
        dialect = st.selectbox("SQL Dialect", DIALECTS)
        st.subheader("📐 Database Schema")
        use_sample = st.button("Load Sample Schema")
        schema = st.text_area(
            "Paste your schema here",
            value=SAMPLE_SCHEMA if use_sample else "",
            height=300,
            placeholder="customers (id INT PK, name VARCHAR [PII], ...)"
        )
        st.caption("💡 Tip: Tag PII fields with [PII] for governance warnings")

    with col2:
        st.subheader("💬 Ask in Plain English")
        question = st.text_area(
            "Your question",
            height=100,
            placeholder="e.g. Show me the top 10 customers by total order value in the last 90 days"
        )

        if st.button("⚡ Generate SQL", type="primary", use_container_width=True):
            if not question.strip():
                st.warning("Please enter a question.")
            elif not schema.strip():
                st.warning("Please enter your schema.")
            else:
                with st.spinner("Generating SQL..."):
                    try:
                        result = generate_sql(question, schema, dialect)

                        # Badges
                        b1, b2, b3, b4 = st.columns(4)
                        b1.metric("Dialect", dialect)
                        b2.metric("Complexity", result.get("complexity", "N/A"))
                        b3.metric("Est. Cost", result.get("estimated_cost", "N/A"))
                        b4.metric("PII Flags", len(result.get("pii_warnings", [])))

                        st.divider()

                        # SQL Output
                        st.subheader("📝 Generated SQL")
                        st.code(result["sql"], language="sql")

                        # Explanation
                        st.subheader("📖 Plain English Explanation")
                        st.info(result["explanation"])

                        # PII Warnings
                        if result.get("pii_warnings"):
                            st.subheader("🔒 PII & Governance Warnings")
                            for w in result["pii_warnings"]:
                                severity = w.get("severity", "medium")
                                icon = "🔴" if severity == "high" else "🟡" if severity == "medium" else "🔵"
                                st.warning(f"{icon} **[{severity.upper()}]** `{w['table']}.{w['field']}` — {w['note']}")
                            for g in result.get("governance_warnings", []):
                                st.warning(f"⚠️ {g}")

                        # Optimization Tips
                        if result.get("optimization_tips"):
                            st.subheader("⚡ Optimization Tips")
                            for i, tip in enumerate(result["optimization_tips"], 1):
                                st.success(f"**{i}.** {tip}")

                        # Add to audit log
                        st.session_state.audit_log.append({
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "question": question,
                            "dialect": dialect,
                            "sql": result["sql"],
                            "complexity": result.get("complexity"),
                            "pii_hit": len(result.get("pii_warnings", [])) > 0,
                            "cost": result.get("estimated_cost")
                        })

                    except json.JSONDecodeError:
                        st.error("Failed to parse response. Please try again.")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

with tab2:
    st.subheader("📋 Query Audit Log")
    if not st.session_state.audit_log:
        st.info("No queries yet. Generate some SQL to see the audit trail.")
    else:
        col_a, col_b = st.columns([4,1])
        col_a.write(f"**{len(st.session_state.audit_log)} queries logged this session**")
        if col_b.button("🗑️ Clear Log"):
            st.session_state.audit_log = []
            st.rerun()

        df = pd.DataFrame(st.session_state.audit_log)
        st.dataframe(
            df[["timestamp","question","dialect","complexity","cost","pii_hit"]],
            use_container_width=True
        )

        st.subheader("Query Details")
        for i, entry in enumerate(reversed(st.session_state.audit_log)):
            with st.expander(f"#{len(st.session_state.audit_log)-i} — {entry['question'][:60]}..."):
                st.caption(f"🕐 {entry['timestamp']} · {entry['dialect']} · {entry['complexity']}")
                st.code(entry["sql"], language="sql")