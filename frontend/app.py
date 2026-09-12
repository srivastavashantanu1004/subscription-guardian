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

# Safe Field Parsers
def get_sub_name(sub):
    return sub.get("name") or "Unknown Service"

def get_sub_plan(sub):
    return sub.get("plan") or "Standard"

def get_sub_price(sub):
    try:
        return float(sub.get("price", 0.0))
    except (ValueError, TypeError):
        return 0.0

# --- HEADER ---
st.title("🛡️ Subscription Guardian")
st.write("Automated E-Receipt Tracking & Contract Clause Auditing")

subscriptions = fetch_subscriptions()

# --- METRIC CARDS ---
total_monthly = sum(get_sub_price(sub) for sub in subscriptions)
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
            st.subheader("Monthly Spend Breakdown")
            chart_data = [
                {"Service": get_sub_name(sub), "Cost (₹)": get_sub_price(sub)}
                for sub in subscriptions
            ]
            chart_df = pd.DataFrame(chart_data).set_index("Service")
            st.bar_chart(chart_df, y="Cost (₹)")
            
        with col_list:
            st.subheader("Active Subscriptions")
            search_query = st.text_input("Search active items...", placeholder="Type to filter...").strip().lower()
            
            filtered = [
                (idx, sub) for idx, sub in enumerate(subscriptions)
                if search_query in get_sub_name(sub).lower() or search_query in get_sub_plan(sub).lower()
            ]
            
            for idx, sub in filtered:
                sub_id = sub.get("id")
                s_name = get_sub_name(sub)
                s_plan = get_sub_plan(sub)
                s_price = get_sub_price(sub)
                
                st.write(f"**{s_name}** ({s_plan}) — ₹{s_price:.2f}/mo")
                
                btn_c1, btn_c2 = st.columns([1, 1])
                with btn_c1:
                    if st.button("Draft Cancel Email", key=f"c_{idx}"):
                        st.session_state[f"show_e_{idx}"] = not st.session_state.get(f"show_e_{idx}", False)
                with btn_c2:
                    if st.button("Delete Service", key=f"d_{idx}"):
                        if delete_subscription_from_db(sub_id, idx):
                            st.success(f"Removed {s_name}")
                            st.rerun()
                
                if st.session_state.get(f"show_e_{idx}", False):
                    template = f"Subject: Request for Immediate Cancellation - {s_name}\n\nPlease cancel my {s_plan} plan effective immediately."
                    st.code(template, language="text")
    else:
        st.info("No active subscriptions found. Use the tab above to add items.")

# --- ADD SERVICE TAB ---
with tab_add:
    st.subheader("Register New Subscription")
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
                    st.success(f"Added {name} successfully!")
                    st.rerun()
            else:
                st.error("Please enter valid details for all fields.")

# --- AI TAB ---
with tab_ai:
    st.subheader("AI Redundancy Optimizer")
    if st.button("Analyze Savings"):
        if len(subscriptions) < 2:
            st.warning("Add at least 2 subscriptions first.")
        else:
            with st.spinner("Analyzing portfolio..."):
                try:
                    sub_summary = "\n".join([f"- {get_sub_name(s)}: {get_sub_plan(s)} (₹{get_sub_price(s)}/mo)" for s in subscriptions])
                    headers = {}
                    if WORKSPACE_ID:
                        headers["anthropic-workspace-id"] = WORKSPACE_ID
                    client = anthropic.Anthropic(api_key=ACTIVE_KEY, default_headers=headers if headers else None)
                    res = client.messages.create(
                        model="claude-3-5-sonnet-20240620",
                        max_tokens=400,
                        messages=[{"role": "user", "content": f"Analyze redundant services in:\n{sub_summary}"}]
                    )
                    st.write(res.content[0].text)
                except Exception as e:
                    st.error(f"API Error: {str(e)}")
    
    st.write("---")
    st.subheader("AI Contract Auditor")
    contract_text = st.text_area("Agreement Terms", height=120, placeholder="Paste contract text here...")
    if st.button("Audit Fine Print"):
        if contract_text.strip():
            with st.spinner("Auditing contract terms..."):
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
                    st.write(res.content[0].text)
                except Exception as e:
                    st.error(f"Audit Error: {str(e)}")
        else:
            st.warning("Please provide agreement text.")
