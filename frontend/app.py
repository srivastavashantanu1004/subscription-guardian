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

# --- YELLOW / AMBER THEME STYLING ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@500;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        color: #fef08a !important;
    }

    .stApp {
        background: radial-gradient(circle at 50% 10%, #451a03 0%, #1c1917 60%, #0c0a09 100%) !important;
    }

    h1, h2, h3, h4, h5, h6 {
        font-family: 'Outfit', sans-serif !important;
        letter-spacing: -0.02em;
        color: #fbbf24 !important;
    }

    /* Metric Cards */
    div[data-testid="stMetric"] {
        background: rgba(45, 26, 10, 0.55) !important;
        backdrop-filter: blur(16px) !important;
        border: 1px solid rgba(245, 158, 11, 0.3) !important;
        border-radius: 16px !important;
        padding: 18px 24px !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.4) !important;
    }

    div[data-testid="stMetricLabel"] > div {
        color: #fde68a !important;
        font-size: 0.9rem !important;
        font-weight: 600 !important;
        text-transform: uppercase;
    }

    div[data-testid="stMetricValue"] > div {
        color: #fbbf24 !important;
        font-family: 'Outfit', sans-serif !important;
        font-weight: 800 !important;
        font-size: 2.2rem !important;
    }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%) !important;
        color: #0c0a09 !important;
        border: 1px solid rgba(254, 240, 138, 0.4) !important;
        font-weight: 800 !important;
        border-radius: 12px !important;
        padding: 10px 20px !important;
        box-shadow: 0 4px 15px rgba(245, 158, 11, 0.35) !important;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%) !important;
        color: #000000 !important;
    }

    /* Navigation Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background-color: rgba(28, 25, 23, 0.7) !important;
        border-radius: 14px !important;
        padding: 6px !important;
        border: 1px solid rgba(245, 158, 11, 0.2) !important;
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px !important;
        padding: 10px 20px !important;
        color: #fde68a !important;
        font-weight: 600 !important;
    }

    .stTabs [aria-selected="true"] {
        background: rgba(245, 158, 11, 0.25) !important;
        color: #fbbf24 !important;
        border: 1px solid rgba(245, 158, 11, 0.5) !important;
    }

    /* Form Fields */
    input, textarea {
        background-color: rgba(28, 25, 23, 0.7) !important;
        color: #fef08a !important;
        border-radius: 10px !important;
        border: 1px solid rgba(245, 158, 11, 0.25) !important;
    }
</style>
""", unsafe_allow_html=True)

# --- ENVIRONMENT & INITIALIZATION ---
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

# --- FIELD READERS ---
def get_sub_name(sub):
    return sub.get("service_name") or sub.get("name") or sub.get("title") or "Unknown Service"

def get_sub_plan(sub):
    return sub.get("plan_tier") or sub.get("plan") or sub.get("tier") or sub.get("plan_name") or "Standard"

def get_sub_price(sub):
    val = sub.get("price") if "price" in sub else sub.get("amount") if "amount" in sub else sub.get("cost", 0.0)
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0

# --- DATABASE LOGIC ---
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
        # Check actual database columns dynamically
        existing = fetch_subscriptions()
        if existing and isinstance(existing[0], dict):
            sample = existing[0]
            name_k = "service_name" if "service_name" in sample else "name"
            plan_k = "plan" if "plan" in sample else "plan_tier" if "plan_tier" in sample else "tier"
            price_k = "price" if "price" in sample else "amount" if "amount" in sample else "cost"
            payloads = [{name_k: name, plan_k: plan, price_k: price}]
        else:
            payloads = [
                {"service_name": name, "plan": plan, "price": price},
                {"name": name, "plan": plan, "price": price},
                {"service_name": name, "plan_tier": plan, "price": price}
            ]
        
        last_error = ""
        for p in payloads:
            try:
                supabase.table("subscriptions").insert(p).execute()
                return True
            except Exception as e:
                last_error = str(e)
                continue
        
        st.error(f"❌ Database error: {last_error}")
        return False
    else:
        if "subscriptions" not in st.session_state:
            st.session_state.subscriptions = []
        st.session_state.subscriptions.append({"service_name": name, "plan": plan, "price": price})
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

# --- E-RECEIPT INBOX SCANNER ---
def scan_email_receipts(email_user, email_pass):
    receipts = []
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(email_user, email_pass)
        mail.select("inbox")
        
        status, messages = mail.search(None, '(OR SUBJECT "receipt" (OR SUBJECT "subscription" SUBJECT "invoice"))')
        mail_ids = messages[0].split()
        
        for i in mail_ids[-10:]:
            _, msg_data = mail.fetch(i, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject = msg["subject"] or ""
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode(errors="ignore")
                                break
                    else:
                        body = msg.get_payload(decode=True).decode(errors="ignore")
                    
                    price_match = re.search(r'(?:₹|\$|USD|INR)\s*([\d\.]+)', body + subject)
                    cost = float(price_match.group(1)) if price_match else 0.0
                    receipts.append({"subject": subject, "snippet": body[:200], "detected_cost": cost})
        mail.logout()
    except Exception as e:
        st.error(f"IMAP Error: {str(e)}")
    return receipts

# --- HEADER SECTION ---
st.markdown("""
<div style="background: linear-gradient(135deg, rgba(245, 158, 11, 0.2) 0%, rgba(217, 119, 6, 0.1) 100%); backdrop-filter: blur(20px); padding: 28px 36px; border-radius: 20px; border: 1px solid rgba(245, 158, 11, 0.3); margin-bottom: 28px;">
    <div style="display: flex; align-items: center; gap: 16px;">
        <span style="font-size: 2.8rem;">🛡️</span>
        <div>
            <h1 style="margin: 0; font-size: 2.4rem; font-weight: 800; background: linear-gradient(90deg, #fef08a, #fbbf24); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">Subscription Guardian</h1>
            <p style="margin-top: 4px; margin-bottom: 0; font-size: 1.05rem; color: #fde68a; font-weight: 500;">⚡ E-Receipt Mail Tracking & AI Clause Auditor</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

subscriptions = fetch_subscriptions()

# --- METRIC CARDS ---
total_monthly = sum(get_sub_price(sub) for sub in subscriptions)
total_yearly = total_monthly * 12

m1, m2, m3 = st.columns(3)
with m1:
    st.metric("💳 Monthly Spend", f"₹{total_monthly:.2f}")
with m2:
    st.metric("📅 Annual Spend", f"₹{total_yearly:.2f}")
with m3:
    st.metric("📦 Active Subscriptions", len(subscriptions))

st.write("")

# --- APP NAVIGATION ---
tab_dashboard, tab_add, tab_receipts, tab_ai = st.tabs([
    "📊 Portfolio Dashboard", 
    "➕ Register Service", 
    "📧 E-Receipt Scanner",
    "🤖 AI Clause Auditor"
])

# --- DASHBOARD TAB ---
with tab_dashboard:
    if subscriptions:
        col_chart, col_list = st.columns([1.2, 1])
        with col_chart:
            st.markdown("### 📈 Monthly Expenditure Breakdown")
            chart_data = [
                {"Service": get_sub_name(sub), "Cost (₹)": get_sub_price(sub)}
                for sub in subscriptions
            ]
            chart_df = pd.DataFrame(chart_data).set_index("Service")
            st.bar_chart(chart_df, y="Cost (₹)", color="#f59e0b")
            
        with col_list:
            st.markdown("### 🏷️ Active Services")
            search_query = st.text_input("🔍 Search items...", placeholder="Filter list...").strip().lower()
            
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
                <div style="background: rgba(45, 26, 10, 0.4); padding: 16px; border-radius: 12px; border: 1px solid rgba(245, 158, 11, 0.2); margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong style="font-size: 1.1rem; color: #fbbf24; font-family: 'Outfit', sans-serif;">{s_name}</strong>
                        <div style="font-size: 0.85rem; color: #fde68a;">Plan: {s_plan}</div>
                    </div>
                    <div style="font-size: 1.25rem; font-weight: 800; color: #fef08a;">₹{s_price:.2f}<span style="font-size: 0.8rem; color: #fde68a;">/mo</span></div>
                </div>
                """, unsafe_allow_html=True)
                
                btn_c1, btn_c2 = st.columns([1, 1])
                with btn_c1:
                    if st.button("✉️ Draft Cancel Email", key=f"c_{idx}"):
                        st.session_state[f"show_e_{idx}"] = not st.session_state.get(f"show_e_{idx}", False)
                with btn_c2:
                    if st.button("🗑️ Remove Service", key=f"d_{idx}"):
                        if delete_subscription_from_db(sub_id, idx):
                            st.success(f"Removed {s_name}")
                            st.rerun()
                
                if st.session_state.get(f"show_e_{idx}", False):
                    template = f"Subject: Cancellation Notice - {s_name}\n\nTo Whom It May Concern,\n\nPlease terminate my {s_plan} subscription immediately and stop all future charges.\n\nThank you."
                    st.code(template, language="text")
    else:
        st.info("No active subscriptions registered yet.")

# --- REGISTER TAB ---
with tab_add:
    st.markdown("### ➕ Register New Service")
    with st.form("add_sub_form", clear_on_submit=True):
        col_a, col_b, col_c = st.columns([2, 2, 1])
        with col_a:
            name = st.text_input("Service Name", placeholder="e.g. Netflix, Spotify")
        with col_b:
            plan = st.text_input("Plan Tier", placeholder="e.g. Premium, Standard")
        with col_c:
            price = st.number_input("Monthly Cost (₹)", min_value=0.00, step=10.00, value=0.00)
        
        submitted = st.form_submit_button("✨ Save Record")
        if submitted:
            if name and plan and price > 0:
                if add_subscription_to_db(name.strip(), plan.strip(), price):
                    st.success(f"Added {name} successfully!")
                    st.rerun()
            else:
                st.error("Please provide valid information for all fields.")

# --- RECEIPT SCANNER TAB ---
with tab_receipts:
    st.markdown("### 📧 Mail Receipt Scanner")
    st.write("Scan your email inbox for billing receipts, recurring charges, and invoices.")
    
    e_col1, e_col2 = st.columns(2)
    with e_col1:
        email_user = st.text_input("Gmail Address", placeholder="user@gmail.com")
    with e_col2:
        email_pass = st.text_input("App Password", type="password", help="Use a Gmail App Password")
        
    if st.button("🔍 Scan Recent Receipts"):
        if email_user and email_pass:
            with st.spinner("Scanning inbox..."):
                receipts = scan_email_receipts(email_user, email_pass)
                if receipts:
                    for r in receipts:
                        st.markdown(f"**Subject:** {r['subject']}")
                        st.markdown(f"*Detected Cost:* ₹{r['detected_cost']:.2f}")
                        st.text(r['snippet'])
                        st.write("---")
                else:
                    st.info("No subscription receipts found in recent emails.")
        else:
            st.warning("Please enter your email credentials.")

# --- AI AUDITOR TAB ---
with tab_ai:
    st.markdown("### 🧠 AI Redundancy Analyzer")
    if st.button("⚡ Run Redundancy Check"):
        if len(subscriptions) < 2:
            st.warning("Add at least 2 subscriptions first.")
        else:
            with st.spinner("Analyzing subscriptions..."):
                try:
                    sub_summary = "\n".join([f"- {get_sub_name(s)}: {get_sub_plan(s)} (₹{get_sub_price(s)}/mo)" for s in subscriptions])
                    headers = {}
                    if WORKSPACE_ID:
                        headers["anthropic-workspace-id"] = WORKSPACE_ID
                    client = anthropic.Anthropic(api_key=ACTIVE_KEY, default_headers=headers if headers else None)
                    res = client.messages.create(
                        model="claude-3-5-sonnet-20240620",
                        max_tokens=400,
                        messages=[{"role": "user", "content": f"Identify redundant software/services from this list:\n{sub_summary}"}]
                    )
                    st.markdown(res.content[0].text)
                except Exception as e:
                    st.error(f"API Error: {str(e)}")
    
    st.write("---")
    st.markdown("### 📜 AI Fine-Print & Clause Auditor")
    contract_text = st.text_area("📋 Terms of Service Text", height=140, placeholder="Paste agreement text here...")
    
    if st.button("⚖️ Audit Contract Clauses"):
        if contract_text.strip():
            with st.spinner("Auditing contract text..."):
                try:
                    headers = {}
                    if WORKSPACE_ID:
                        headers["anthropic-workspace-id"] = WORKSPACE_ID
                    client = anthropic.Anthropic(api_key=ACTIVE_KEY, default_headers=headers if headers else None)
                    res = client.messages.create(
                        model="claude-3-5-sonnet-20240620",
                        max_tokens=350,
                        messages=[{"role": "user", "content": f"Extract hidden cancellation traps, fee penalties, and auto-renew clauses from:\n{contract_text}"}]
                    )
                    st.markdown(res.content[0].text)
                except Exception as e:
                    st.error(f"Audit Error: {str(e)}")
        else:
            st.warning("Please enter contract text first.")
