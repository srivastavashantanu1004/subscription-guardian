import os
import re
import imaplib
import email
import streamlit as st
import anthropic
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Subscription Guardian",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- DIRECT CONTAINER OVERRIDE CSS ---
st.markdown("""
<style>
    /* Force background on inner container */
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(rgba(15, 23, 42, 0.85), rgba(15, 23, 42, 0.85)), 
                    url("https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=2000&auto=format&fit=crop") no-repeat center center fixed !important;
        background-size: cover !important;
    }

    [data-testid="stHeader"], [data-testid="stToolbar"] {
        background: transparent !important;
    }

    /* Force text contrast */
    h1, h2, h3, h4, h5, h6, p, label, span, div {
        color: #f8fafc !important;
    }

    /* Glassmorphism Metric Cards */
    div[data-testid="stMetric"] {
        background: rgba(30, 41, 59, 0.75) !important;
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
        padding: 20px 24px !important;
        border-radius: 16px !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.4) !important;
    }

    [data-testid="stMetricValue"] {
        color: #c084fc !important;
        font-weight: 800 !important;
    }

    /* Inputs */
    .stTextInput input, .stNumberInput input, .stTextArea textarea, div[data-baseweb="select"] {
        background-color: rgba(15, 23, 42, 0.8) !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 10px !important;
    }

    /* Action Buttons */
    .stButton>button {
        background: linear-gradient(135deg, #a855f7 0%, #6366f1 100%) !important;
        color: #ffffff !important;
        border: none !important;
        font-weight: 700 !important;
        border-radius: 10px !important;
        box-shadow: 0 4px 14px rgba(168, 85, 247, 0.4) !important;
    }
</style>
""", unsafe_allow_html=True)

# --- SECRETS & ENVIRONMENT ---
load_dotenv(dotenv_path="../.env")

SUPABASE_URL = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")

raw_key = st.secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or ""
ACTIVE_KEY = str(raw_key).strip().strip('"').strip("'").strip()

raw_workspace = st.secrets.get("ANTHROPIC_WORKSPACE_ID") or os.getenv("ANTHROPIC_WORKSPACE_ID") or ""
WORKSPACE_ID = str(raw_workspace).strip().strip('"').strip("'").strip()

supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception:
        pass

# --- DB OPERATIONS ---
def fetch_subscriptions():
    if supabase:
        try:
            res = supabase.table("subscriptions").select("*").execute()
            return res.data or []
        except Exception:
            return []
    return st.session_state.get("subscriptions", [])

def add_subscription_to_db(name, plan, price):
    if supabase:
        try:
            supabase.table("subscriptions").insert({
                "name": name,
                "plan": plan,
                "price": price
            }).execute()
            return True
        except Exception as e:
            st.error(f"Database Error: {str(e)}")
            return False
    else:
        if "subscriptions" not in st.session_state:
            st.session_state.subscriptions = []
        st.session_state.subscriptions.append({"name": name, "plan": plan, "price": price})
        return True

def delete_subscription_from_db(sub_id, index):
    if supabase and sub_id:
        try:
            supabase.table("subscriptions").delete().eq("id", sub_id).execute()
            return True
        except Exception as e:
            st.error(f"Failed to delete: {str(e)}")
            return False
    else:
        if "subscriptions" in st.session_state and index < len(st.session_state.subscriptions):
            st.session_state.subscriptions.pop(index)
            return True
    return False

# --- HEADER BANNER ---
st.markdown("""
<div style="background: linear-gradient(135deg, rgba(168, 85, 247, 0.35) 0%, rgba(99, 102, 241, 0.35) 100%); backdrop-filter: blur(16px); padding: 24px; border-radius: 20px; border: 1px solid rgba(255, 255, 255, 0.2); margin-bottom: 24px;">
    <h1 style="color: #ffffff !important; margin: 0; font-size: 2.2rem; font-weight: 800;">🛡️ Subscription Guardian</h1>
    <p style="color: #cbd5e1 !important; margin-top: 4px; font-size: 1rem;">Smart E-Receipt Analytics & Clause Auditor</p>
</div>
""", unsafe_allow_html=True)

subscriptions = fetch_subscriptions()

# --- METRIC CARDS ---
total_monthly = sum(float(sub["price"]) for sub in subscriptions)
total_yearly = total_monthly * 12

m1, m2, m3 = st.columns(3)
with m1:
    st.metric("Total Monthly Spend", f"₹{total_monthly:.2f}")
with m2:
    st.metric("Annual Commitment", f"₹{total_yearly:.2f}")
with m3:
    st.metric("Active Subscriptions", len(subscriptions))

st.write("")

# --- TABS ---
tab_dashboard, tab_add, tab_ai = st.tabs([
    "📊 Expense Dashboard", 
    "➕ Add Service", 
    "🤖 AI Savings & Clause Audit"
])

# --- DASHBOARD TAB ---
with tab_dashboard:
    if subscriptions:
        col_chart, col_list = st.columns([1.2, 1])
        with col_chart:
            st.markdown("### 📈 Monthly Spend Breakdown")
            chart_df = pd.DataFrame([
                {"Service": sub["name"], "Cost (₹)": float(sub["price"])}
                for sub in subscriptions
            ]).set_index("Service")
            st.bar_chart(chart_df, y="Cost (₹)", color="#a855f7")
            
        with col_list:
            st.markdown("### 💳 Active Subscriptions")
            search_query = st.text_input("🔍 Search active items...", placeholder="Type to filter...").strip().lower()
            
            filtered = [
                (idx, sub) for idx, sub in enumerate(subscriptions)
                if search_query in sub["name"].lower() or search_query in sub["plan"].lower()
            ]
            
            for idx, sub in filtered:
                sub_id = sub.get("id")
                st.markdown(f"""
                <div style="background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(12px); padding: 16px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.12); margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong style="font-size: 1.1rem; color: #ffffff;">{sub['name']}</strong>
                        <div style="color: #94a3b8; font-size: 0.85rem;">{sub['plan']}</div>
                    </div>
                    <div style="font-size: 1.25rem; font-weight: 800; color: #c084fc;">₹{float(sub['price']):.2f}/mo</div>
                </div>
                """, unsafe_allow_html=True)
                
                btn_c1, btn_c2 = st.columns([1, 1])
                with btn_c1:
                    if st.button("Draft Cancel Email", key=f"c_{idx}"):
                        st.session_state[f"show_e_{idx}"] = not st.session_state.get(f"show_e_{idx}", False)
                with btn_c2:
                    if st.button("Delete Service", key=f"d_{idx}"):
                        if delete_subscription_from_db(sub_id, idx):
                            st.success(f"Removed {sub['name']}")
                            st.rerun()
                
                if st.session_state.get(f"show_e_{idx}", False):
                    template = f"Subject: Cancellation Request - {sub['name']}\n\nPlease cancel my {sub['plan']} subscription effective immediately."
                    st.code(template, language="text")
    else:
        st.info("No active subscriptions found.")

# --- ADD SERVICE TAB ---
with tab_add:
    st.markdown("### ➕ Register New Subscription")
    with st.form("add_sub_form", clear_on_submit=True):
        col_a, col_b, col_c = st.columns([2, 2, 1])
        with col_a:
            name = st.text_input("Service Name", placeholder="e.g. Netflix")
        with col_b:
            plan = st.text_input("Plan Tier", placeholder="e.g. Premium")
        with col_c:
            price = st.number_input("Monthly Cost (₹)", min_value=0.00, step=10.00, value=0.00)
        
        submitted = st.form_submit_button("Save Subscription")
        if submitted:
            if name and plan and price > 0:
                if add_subscription_to_db(name.strip(), plan.strip(), price):
                    st.success(f"Added {name}!")
                    st.rerun()

# --- AI TAB ---
with tab_ai:
    st.markdown("### 💡 AI Redundancy Optimizer")
    if st.button("Analyze Savings"):
        if len(subscriptions) < 2:
            st.warning("Add at least 2 subscriptions first.")
        else:
            with st.spinner("Analyzing..."):
                try:
                    sub_summary = "\n".join([f"- {s['name']}: {s['plan']} (₹{s['price']}/mo)" for s in subscriptions])
                    headers = {}
                    if WORKSPACE_ID:
                        headers["anthropic-workspace-id"] = WORKSPACE_ID
                    client = anthropic.Anthropic(api_key=ACTIVE_KEY, default_headers=headers if headers else None)
                    res = client.messages.create(
                        model="claude-3-5-sonnet-20240620",
                        max_tokens=400,
                        messages=[{"role": "user", "content": f"Analyze redundant services in:\n{sub_summary}"}]
                    )
                    st.markdown(res.content[0].text)
                except Exception as e:
                    st.error(str(e))
    
    st.write("---")
    st.markdown("### 📜 AI Contract Auditor")
    contract_text = st.text_area("Agreement Text", height=120)
    if st.button("Audit Contract"):
        if contract_text.strip():
            with st.spinner("Auditing..."):
                try:
                    headers = {}
                    if WORKSPACE_ID:
                        headers["anthropic-workspace-id"] = WORKSPACE_ID
                    client = anthropic.Anthropic(api_key=ACTIVE_KEY, default_headers=headers if headers else None)
                    res = client.messages.create(
                        model="claude-3-5-sonnet-20240620",
                        max_tokens=350,
                        messages=[{"role": "user", "content": f"Identify cancellation restrictions/penalties in:\n{contract_text}"}]
                    )
                    st.markdown(res.content[0].text)
                except Exception as e:
                    st.error(str(e))