import streamlit as st
import anthropic
import json
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="NL-to-SQL Pro", page_icon="🧠", layout="wide")

# --- BYOK: Bring Your Own Key ---
st.sidebar.title("🔑 API Key Setup")
st.sidebar.markdown("""
**This app uses your own Anthropic API key.**  
Your key is never stored — it lives only in your browser session.

👉 Get a free key at [console.anthropic.com](https://console.anthropic.com)
""")

user_api_key = st.sidebar.text_input(
    "Paste your Anthropic API Key",
    type="password",          # hides the key visually
    placeholder="sk-ant-..."
)

if not user_api_key:
    st.title("🧠 NL-to-SQL Pro")
    st.warning("👈 Please enter your Anthropic API key in the sidebar to get started.")
    st.info("""
    **Why do I need my own API key?**  
    To keep this tool free and open for everyone, each user connects 
    with their own Anthropic account. Anthropic offers free credits 
    to get started — enough to run hundreds of queries.
    
    **Get your key in 2 minutes:**  
    1. Go to [console.anthropic.com](https://console.anthropic.com)  
    2. Sign up (free)  
    3. Click API Keys → Create Key  
    4. Paste it in the sidebar ← 
    """)
    st.stop()   # stops the rest of the app from rendering

# --- Rest of your app runs only if key is provided ---
DIALECTS = ["PostgreSQL", "Snowflake", "BigQuery", "MySQL", "SQL Server", "Redshift"]

SAMPLE_SCHEMA = """customers (id INT PK, name VARCHAR, email VARCHAR [PII], country VARCHAR, created_at TIMESTAMP)
orders (id INT PK, customer_id INT FK, total DECIMAL, status VARCHAR, created_at TIMESTAMP)
order_items (id INT PK, order_id INT FK, product_id INT FK, quantity INT, unit_price DECIMAL)
products (id INT PK, name VARCHAR, category VARCHAR, price DECIMAL, stock INT)
employees (id INT PK, name VARCHAR, email VARCHAR [PII], salary DECIMAL [PII], department VARCHAR)"""

if "audit_log" not in st.session_state:
    st.session_state.audit_log = []

def generate_sql(question: str, schema: str, dialect: str) -> dict:
    # Uses the USER's key — not yours
    client = anthropic.Anthropic(api_key=user_api_key)

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system=f"""You are an expert data architect and SQL specialist with 20 years of experience.
Given a database schema and a natural language question, return ONLY valid JSON:
{{
  "sql": "the generated SQL query for {dialect}",
  "explanation": "plain English explanation step by step",
  "optimization_tips": ["tip1", "tip2"],
  "pii_warnings": [{{"field": "fieldname", "table": "tablename", "severity": "high|medium|low", "note": "explanation"}}],
  "governance_warnings": ["any data governance concerns"],
  "complexity": "Simple|Moderate|Complex",
  "estimated_cost": "Low|Medium|High"
}}
Return empty arrays if nothing to report. Tailor SQL strictly to {dialect}.""",
        messages=[{"role": "user", "content": f"Schema:\n{schema}\n\nQuestion: {question}"}]
    )

    raw = message.content[0].text.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(raw)

# --- UI ---
st.title("🧠 NL-to-SQL Pro")
st.caption("Schema-aware · Multi-dialect · Governance-ready · Built by a Data Architect")
st.success("✅ API key connected — you're ready to generate SQL!")

tab1, tab2 = st.tabs(["⚡ SQL Generator", "📋 Audit Log"])

with tab1:
    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("⚙️ Configuration")
        dialect = st.selectbox("SQL Dialect", DIALECTS)
        st.subheader("📐 Database Schema")
        if st.button("Load Sample Schema"):
            st.session_state.schema = SAMPLE_SCHEMA
        schema = st.text_area("Paste your schema", 
                               value=st.session_state.get("schema", ""),
                               height=280,
                               placeholder="customers (id INT PK, name VARCHAR [PII], ...)")
        st.caption("💡 Tag PII fields with [PII] for governance warnings")

    with col2:
        st.subheader("💬 Ask in Plain English")
        question = st.text_area("Your question", height=100,
                                 placeholder="e.g. Show top 10 customers by revenue in last 90 days")

        if st.button("⚡ Generate SQL", type="primary", use_container_width=True):
            if not question.strip() or not schema.strip():
                st.warning("Please enter both a question and a schema.")
            else:
                with st.spinner("Generating SQL..."):
                    try:
                        result = generate_sql(question, schema, dialect)

                        b1, b2, b3, b4 = st.columns(4)
                        b1.metric("Dialect", dialect)
                        b2.metric("Complexity", result.get("complexity", "N/A"))
                        b3.metric("Est. Cost", result.get("estimated_cost", "N/A"))
                        b4.metric("PII Flags", len(result.get("pii_warnings", [])))
                        st.divider()

                        st.subheader("📝 Generated SQL")
                        st.code(result["sql"], language="sql")

                        st.subheader("📖 Explanation")
                        st.info(result["explanation"])

                        if result.get("pii_warnings"):
                            st.subheader("🔒 PII & Governance Warnings")
                            for w in result["pii_warnings"]:
                                icon = "🔴" if w.get("severity")=="high" else "🟡" if w.get("severity")=="medium" else "🔵"
                                st.warning(f"{icon} **[{w.get('severity','').upper()}]** `{w['table']}.{w['field']}` — {w['note']}")

                        if result.get("optimization_tips"):
                            st.subheader("⚡ Optimization Tips")
                            for i, tip in enumerate(result["optimization_tips"], 1):
                                st.success(f"**{i}.** {tip}")

                        st.session_state.audit_log.append({
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "question": question,
                            "dialect": dialect,
                            "sql": result["sql"],
                            "complexity": result.get("complexity"),
                            "pii_hit": len(result.get("pii_warnings", [])) > 0,
                            "cost": result.get("estimated_cost")
                        })

                    except Exception as e:
                        st.error(f"Error: {str(e)} — double-check your API key is valid.")

with tab2:
    st.subheader("📋 Query Audit Log")
    if not st.session_state.audit_log:
        st.info("No queries yet. Generate some SQL to see the audit trail.")
    else:
        if st.button("🗑️ Clear Log"):
            st.session_state.audit_log = []
            st.rerun()
        df = pd.DataFrame(st.session_state.audit_log)
        st.dataframe(df[["timestamp","question","dialect","complexity","cost","pii_hit"]], 
                     use_container_width=True)