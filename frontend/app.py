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

# --- MODERN UI & TYPOGRAPHY STYLING ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@500;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        color: #f8fafc !important;
    }

    /* Gradient Background */
    .stApp {
        background: radial-gradient(circle at 50% 10%, #1e1b4b 0%, #0f172a 60%, #090d16 100%) !important;
    }

    h1, h2, h3, h4, h5, h6 {
        font-family: 'Outfit', sans-serif !important;
        letter-spacing: -0.02em;
    }

    /* Glassmorphism Metric Cards */
    div[data-testid="stMetric"] {
        background: rgba(30, 41, 59, 0.45) !important;
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
        border: 1px solid rgba(168, 85, 247, 0.2) !important;
        border-radius: 16px !important;
        padding: 18px 24px !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37) !important;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        border-color: rgba(168, 85, 247, 0.5) !important;
    }

    div[data-testid="stMetricLabel"] > div {
        color: #94a3b8 !important;
        font-size: 0.9rem !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    div[data-testid="stMetricValue"] > div {
        color: #c084fc !important;
        font-family: 'Outfit', sans-serif !important;
        font-weight: 800 !important;
        font-size: 2.2rem !important;
        text-shadow: 0 0 20px rgba(192, 132, 252, 0.3);
    }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #a855f7 0%, #6366f1 100%) !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        font-weight: 700 !important;
        border-radius: 12px !important;
        padding: 10px 20px !important;
        box-shadow: 0 4px 15px rgba(168, 85, 247, 0.4) !important;
        transition: all 0.2s ease-in-out !important;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #c084fc 0%, #818cf8 100%) !important;
        box-shadow: 0 6px 20px rgba(168, 85, 247, 0.6) !important;
        transform: translateY(-1px);
    }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        background-color: rgba(15, 23, 42, 0.6) !important;
        border-radius: 14px !important;
        padding: 6px !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px !important;
        padding: 10px 20px !important;
        color: #94a3b8 !important;
        font-weight: 600 !important;
    }

    .stTabs [aria-selected="true"] {
        background: rgba(168, 85, 247, 0.2) !important;
        color: #f8fafc !important;
        border: 1px solid rgba(168, 85, 247, 0.4) !important;
    }

    /* Inputs */
    input, textarea {
        background-color: rgba(15, 23, 42, 0.6) !important;
        color: #f8fafc !important;
        border-radius: 10px !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
    }
    
    input:focus, textarea:focus {
        border-color: #a855f7 !important;
        box-shadow: 0 0 10px rgba(168, 85, 247, 0.3) !important;
    }
</style>
""", unsafe_allow_html=True)

# --- ENVIRONMENT & SECRETS ---
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
        payload_options = [
            {"name": name, "plan": plan, "price": price},
            {"service_name": name, "plan": plan, "price": price},
            {"service_name": name, "plan_name": plan, "amount": price},
            {"name": name, "plan": plan, "amount": price},
            {"title": name, "plan": plan, "cost": price}
        ]
        last_error = None
        for payload in payload_options:
            try:
                supabase.table("subscriptions").insert(payload).execute()
                return True
            except Exception as e:
                last_error = e
                continue
        st.error(f"❌ Database Error: {str(last_error)}")
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
            st.error(f"❌ Failed to delete: {str(e)}")
            return False
    else:
        if "subscriptions" in st.session_state and index < len(st.session_state.subscriptions):
            st.session_state.subscriptions.pop(index)
            return True
    return False

# Safe Field Parsers
def get_sub_name(sub):
    return sub.get("name") or sub.get("service_name") or sub.get("title") or "Unknown Service"

def get_sub_plan(sub):
    return sub.get("plan") or sub.get("plan_name") or sub.get("tier") or "Standard"

def get_sub_price(sub):
    val = sub.get("price") if "price" in sub else sub.get("amount") if "amount" in sub else sub.get("cost", 0.0)
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0

# --- HERO HEADER BANNER ---
st.markdown("""
<div style="background: linear-gradient(135deg, rgba(168, 85, 247, 0.25) 0%, rgba(99, 102, 241, 0.15) 100%); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); padding: 28px 36px; border-radius: 20px; border: 1px solid rgba(255, 255, 255, 0.12); margin-bottom: 28px; box-shadow: 0 10px 30px rgba(0,0,0,0.35);">
    <div style="display: flex; align-items: center; gap: 16px;">
        <span style="font-size: 2.8rem;">🛡️</span>
        <div>
            <h1 style="margin: 0; font-size: 2.4rem; font-weight: 800; background: linear-gradient(90deg, #ffffff, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">Subscription Guardian</h1>
            <p style="margin-top: 4px; margin-bottom: 0; font-size: 1.05rem; color: #94a3b8; font-weight: 500;">⚡ Automated E-Receipt Tracking & Contract Clause Auditing</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

subscriptions = fetch_subscriptions()

# --- METRICS DISPLAY ---
total_monthly = sum(get_sub_price(sub) for sub in subscriptions)
total_yearly = total_monthly * 12

m1, m2, m3 = st.columns(3)
with m1:
    st.metric("💳 Monthly Outflow", f"₹{total_monthly:.2f}")
with m2:
    st.metric("📅 Annual Outflow", f"₹{total_yearly:.2f}")
with m3:
    st.metric("📦 Active Services", len(subscriptions))

st.write("")

# --- MAIN TABS ---
tab_dashboard, tab_add, tab_ai = st.tabs([
    "📊 Analytics Dashboard", 
    "➕ Register Service", 
    "✨ AI Intelligence Hub"
])

# --- TAB 1: DASHBOARD ---
with tab_dashboard:
    if subscriptions:
        col_chart, col_list = st.columns([1.2, 1])
        with col_chart:
            st.markdown("### 📈 Monthly Expenditure Overview")
            chart_data = [
                {"Service": get_sub_name(sub), "Cost (₹)": get_sub_price(sub)}
                for sub in subscriptions
            ]
            chart_df = pd.DataFrame(chart_data).set_index("Service")
            st.bar_chart(chart_df, y="Cost (₹)", color="#a855f7")
            
        with col_list:
            st.markdown("### 🏷️ Active Subscriptions")
            search_query = st.text_input("🔍 Search services...", placeholder="Type to filter...").strip().lower()
            
            filtered = [
                (idx, sub) for idx, sub in enumerate(subscriptions)
                if search_query in get_sub_name(sub).lower() or search_query in get_sub_plan(sub).lower()
            ]
            
            for idx, sub in filtered:
                sub_id = sub.get("id")
                s_name = get_sub_name(sub)
                s_plan = get_sub_plan(sub)
                s_price = get_sub_price(sub)
                
                st.markdown(f"""
                <div style="background: rgba(30, 41, 59, 0.4); backdrop-filter: blur(10px); padding: 18px; border-radius: 14px; border: 1px solid rgba(255, 255, 255, 0.08); margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong style="font-size: 1.15rem; color: #f8fafc; font-family: 'Outfit', sans-serif;">{s_name}</strong>
                        <div style="font-size: 0.88rem; color: #94a3b8; margin-top: 2px;">🏷️ {s_plan}</div>
                    </div>
                    <div style="font-size: 1.3rem; font-weight: 800; color: #c084fc; font-family: 'Outfit', sans-serif;">₹{s_price:.2f}<span style="font-size: 0.8rem; color: #94a3b8;">/mo</span></div>
                </div>
                """, unsafe_allow_html=True)
                
                btn_c1, btn_c2 = st.columns([1, 1])
                with btn_c1:
                    if st.button("✉️ Draft Cancellation", key=f"c_{idx}"):
                        st.session_state[f"show_e_{idx}"] = not st.session_state.get(f"show_e_{idx}", False)
                with btn_c2:
                    if st.button("🗑️ Delete Record", key=f"d_{idx}"):
                        if delete_subscription_from_db(sub_id, idx):
                            st.success(f"Removed {s_name}")
                            st.rerun()
                
                if st.session_state.get(f"show_e_{idx}", False):
                    template = f"Subject: Request for Immediate Cancellation - {s_name}\n\nDear Customer Support,\n\nPlease cancel my {s_plan} subscription effective immediately and confirm termination.\n\nThank you."
                    st.code(template, language="text")
    else:
        st.info("ℹ️ No active subscriptions registered. Use the 'Register Service' tab to add your expenses.")

# --- TAB 2: ADD SERVICE ---
with tab_add:
    st.markdown("### ➕ Register New Subscription")
    with st.form("add_sub_form", clear_on_submit=True):
        col_a, col_b, col_c = st.columns([2, 2, 1])
        with col_a:
            name = st.text_input("🏷️ Service Name", placeholder="e.g. Netflix, Spotify, AWS")
        with col_b:
            plan = st.text_input("💎 Plan Tier", placeholder="e.g. Premium, Family, Basic")
        with col_c:
            price = st.number_input("💰 Monthly Cost (₹)", min_value=0.00, step=10.00, value=0.00)
        
        submitted = st.form_submit_button("✨ Save Subscription")
        if submitted:
            if name and plan and price > 0:
                if add_subscription_to_db(name.strip(), plan.strip(), price):
                    st.success(f"✅ Added {name} successfully!")
                    st.rerun()
            else:
                st.error("⚠️ Please fill in all details with a valid price.")

# --- TAB 3: AI HUB ---
with tab_ai:
    st.markdown("### 💡 AI Portfolio Redundancy Audit")
    if st.button("🔍 Run Savings Optimization"):
        if len(subscriptions) < 2:
            st.warning("⚠️ Please register at least 2 subscriptions to run redundancy analysis.")
        else:
            with st.spinner("Analyzing active subscriptions for cost optimization..."):
                try:
                    sub_summary = "\n".join([f"- {get_sub_name(s)}: {get_sub_plan(s)} (₹{get_sub_price(s)}/mo)" for s in subscriptions])
                    headers = {}
                    if WORKSPACE_ID:
                        headers["anthropic-workspace-id"] = WORKSPACE_ID
                    client = anthropic.Anthropic(api_key=ACTIVE_KEY, default_headers=headers if headers else None)
                    res = client.messages.create(
                        model="claude-3-5-sonnet-20240620",
                        max_tokens=400,
                        messages=[{"role": "user", "content": f"Analyze redundant services and provide clear cost savings suggestions for:\n{sub_summary}"}]
                    )
                    st.markdown(f"""
                    <div style="background: rgba(30, 41, 59, 0.5); padding: 20px; border-radius: 12px; border: 1px solid rgba(168, 85, 247, 0.3); margin-top: 10px;">
                        {res.content[0].text}
                    </div>
                    """, unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"❌ API Error: {str(e)}")
    
    st.write("---")
    st.markdown("### 📜 AI Contract Fine-Print Auditor")
    contract_text = st.text_area("📋 Paste Terms of Service / Agreement Clauses", height=140, placeholder="Paste cancellation clauses or contract text here...")
    if st.button("⚖️ Audit Contract Terms"):
        if contract_text.strip():
            with st.spinner("Auditing legal clauses for hidden fees or lock-ins..."):
                try:
                    headers = {}
                    if WORKSPACE_ID:
                        headers["anthropic-workspace-id"] = WORKSPACE_ID
                    client = anthropic.Anthropic(api_key=ACTIVE_KEY, default_headers=headers if headers else None)
                    res = client.messages.create(
                        model="claude-3-5-sonnet-20240620",
                        max_tokens=350,
                        messages=[{"role": "user", "content": f"Identify cancellation penalties, notice periods, or hidden clauses in:\n{contract_text}"}]
                    )
                    st.markdown(f"""
                    <div style="background: rgba(30, 41, 59, 0.5); padding: 20px; border-radius: 12px; border: 1px solid rgba(168, 85, 247, 0.3); margin-top: 10px;">
                        {res.content[0].text}
                    </div>
                    """, unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"❌ Audit Error: {str(e)}")
        else:
            st.warning("⚠️ Please paste terms of service or contract text to audit.")
