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

# --- REVISED CLEAN & VISIBLE DARK THEME ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    * {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }

    .stApp {
        background-color: #0f172a !important;
        color: #f8fafc !important;
    }

    h1, h2, h3, h4, h5, h6 {
        color: #fbbf24 !important;
        font-weight: 700 !important;
    }

    p, span, label {
        color: #f1f5f9 !important;
    }

    /* Metric Cards */
    div[data-testid="stMetric"] {
        background: #1e293b !important;
        border: 1px solid #334155 !important;
        border-radius: 12px !important;
        padding: 16px 20px !important;
    }

    div[data-testid="stMetricLabel"] > div {
        color: #94a3b8 !important;
        font-size: 0.85rem !important;
        text-transform: uppercase;
    }

    div[data-testid="stMetricValue"] > div {
        color: #fbbf24 !important;
        font-weight: 800 !important;
    }

    /* Input Field Visibility Fix */
    input, textarea, select {
        background-color: #1e293b !important;
        color: #ffffff !important;
        border: 1px solid #475569 !important;
        border-radius: 8px !important;
    }

    input::placeholder {
        color: #94a3b8 !important;
    }

    /* Tab Headers */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #1e293b !important;
        border-radius: 10px !important;
    }

    .stTabs [data-baseweb="tab"] {
        color: #94a3b8 !important;
    }

    .stTabs [aria-selected="true"] {
        background-color: #334155 !important;
        color: #fbbf24 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- ENVIRONMENT & INITIALIZATION ---
load_dotenv(dotenv_path=".env")

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

if "subscriptions" not in st.session_state:
    st.session_state.subscriptions = [
        {"id": 1, "service_name": "Netflix", "plan": "Premium", "price": 649.00},
        {"id": 2, "service_name": "Spotify", "plan": "Individual", "price": 119.00},
        {"id": 3, "service_name": "Amazon Prime", "plan": "Annual", "price": 124.00}
    ]

# --- UNIVERSAL RECORD PARSERS ---
def get_val(item, *keys, default=""):
    for k in keys:
        if k in item and item[k] is not None:
            return item[k]
    return default

def get_name(item):
    return str(get_val(item, "service_name", "name", "title", "service", default="Unknown Service"))

def get_plan(item):
    return str(get_val(item, "plan", "plan_tier", "tier", "plan_name", default="Standard"))

def get_price(item):
    val = get_val(item, "price", "cost", "amount", "monthly_cost", default=0.0)
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0

# --- DATA OPERATIONS ---
def fetch_all():
    if supabase:
        try:
            res = supabase.table("subscriptions").select("*").execute()
            if res.data:
                return res.data
        except Exception:
            pass
    return st.session_state.subscriptions

def insert_record(name, plan, price):
    if supabase:
        payloads = [
            {"service_name": name, "plan": plan, "price": price},
            {"name": name, "plan": plan, "price": price},
            {"service_name": name, "plan_tier": plan, "price": price},
            {"service_name": name, "tier": plan, "price": price},
            {"name": name, "tier": plan, "cost": price}
        ]
        for p in payloads:
            try:
                supabase.table("subscriptions").insert(p).execute()
                return True
            except Exception:
                continue
    
    st.session_state.subscriptions.append({
        "id": len(st.session_state.subscriptions) + 1,
        "service_name": name,
        "plan": plan,
        "price": price
    })
    return True

def delete_record(record_id, index):
    if supabase and record_id:
        try:
            supabase.table("subscriptions").delete().eq("id", record_id).execute()
        except Exception:
            pass
    
    if index < len(st.session_state.subscriptions):
        st.session_state.subscriptions.pop(index)
    return True

# --- UI HEADER ---
st.markdown("""
<div style="background: #1e293b; padding: 24px 32px; border-radius: 16px; border: 1px solid #334155; margin-bottom: 24px;">
    <div style="display: flex; align-items: center; gap: 14px;">
        <span style="font-size: 2.2rem;">🛡️</span>
        <div>
            <h1 style="margin: 0; font-size: 2rem; color: #fbbf24;">Subscription Guardian</h1>
            <p style="margin: 4px 0 0 0; color: #94a3b8; font-size: 0.95rem;">Manage active subscriptions, scan receipts, and audit contract fine print.</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

data = fetch_all()

# --- TOP METRICS ---
total_monthly = sum(get_price(item) for item in data)
total_yearly = total_monthly * 12

m1, m2, m3 = st.columns(3)
with m1:
    st.metric("Monthly Cost", f"₹{total_monthly:,.2f}")
with m2:
    st.metric("Annual Projection", f"₹{total_yearly:,.2f}")
with m3:
    st.metric("Active Subscriptions", len(data))

st.write("")

# --- NAVIGATION TABS ---
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Dashboard", 
    "➕ Register Service", 
    "📧 Receipt Scanner", 
    "🤖 AI Auditor"
])

# --- TAB 1: DASHBOARD ---
with tab1:
    if data:
        c1, c2 = st.columns([1.2, 1])
        with c1:
            st.markdown("### Cost Distribution")
            df = pd.DataFrame([
                {"Service": get_name(x), "Cost (₹)": get_price(x)} for x in data
            ]).set_index("Service")
            st.bar_chart(df, y="Cost (₹)", color="#f59e0b")

        with c2:
            st.markdown("### Managed Subscriptions")
            for idx, item in enumerate(data):
                rec_id = item.get("id")
                s_name = get_name(item)
                s_plan = get_plan(item)
                s_price = get_price(item)

                st.markdown(f"""
                <div style="background: #1e293b; padding: 14px; border-radius: 10px; border: 1px solid #334155; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong style="color: #fbbf24; font-size: 1.05rem;">{s_name}</strong>
                        <div style="font-size: 0.8rem; color: #94a3b8;">Plan: {s_plan}</div>
                    </div>
                    <div style="font-size: 1.15rem; font-weight: 700; color: #f8fafc;">₹{s_price:,.2f}</div>
                </div>
                """, unsafe_allow_html=True)

                b1, b2 = st.columns([1, 1])
                with b1:
                    if st.button("Draft Cancel Email", key=f"draft_{idx}"):
                        st.session_state[f"show_mail_{idx}"] = not st.session_state.get(f"show_mail_{idx}", False)
                with b2:
                    if st.button("Delete Service", key=f"del_{idx}"):
                        delete_record(rec_id, idx)
                        st.rerun()

                if st.session_state.get(f"show_mail_{idx}", False):
                    st.code(
                        f"Subject: Cancel Subscription - {s_name}\n\nDear Support Team,\n\nPlease cancel my {s_name} ({s_plan}) account immediately and send confirmation of termination.\n\nThank you.",
                        language="text"
                    )
    else:
        st.info("No subscriptions added yet.")

# --- TAB 2: REGISTER ---
with tab2:
    st.markdown("### Add New Subscription")
    with st.form("add_form", clear_on_submit=True):
        f1, f2, f3 = st.columns([2, 2, 1])
        with f1:
            in_name = st.text_input("Service Name", placeholder="e.g. Netflix, AWS, GitHub")
        with f2:
            in_plan = st.text_input("Plan Tier", placeholder="e.g. Pro, Premium, Basic")
        with f3:
            in_price = st.number_input("Monthly Cost (₹)", min_value=0.0, step=10.0, value=0.0)

        if st.form_submit_button("Save Subscription"):
            if in_name.strip() and in_price > 0:
                insert_record(in_name.strip(), in_plan.strip() or "Standard", in_price)
                st.success(f"Added {in_name}!")
                st.rerun()
            else:
                st.warning("Please enter a service name and a valid monthly price.")

# --- TAB 3: E-RECEIPT SCANNER ---
with tab3:
    st.markdown("### E-Receipt Inbox Scanner")
    st.write("Connect to Gmail via IMAP to detect incoming invoices and subscription charges.")
    
    e1, e2 = st.columns(2)
    with e1:
        email_user = st.text_input("Email Address", placeholder="user@gmail.com")
    with e2:
        email_pass = st.text_input("App Password", type="password")

    if st.button("Scan Inbox"):
        if email_user and email_pass:
            with st.spinner("Connecting to mail server..."):
                try:
                    mail = imaplib.IMAP4_SSL("imap.gmail.com")
                    mail.login(email_user, email_pass)
                    mail.select("inbox")
                    
                    status, messages = mail.search(None, '(OR SUBJECT "receipt" (OR SUBJECT "subscription" SUBJECT "invoice"))')
                    mail_ids = messages[0].split()
                    
                    if mail_ids:
                        for i in mail_ids[-5:]:
                            _, msg_data = mail.fetch(i, "(RFC822)")
                            for response_part in msg_data:
                                if isinstance(response_part, tuple):
                                    msg = email.message_from_bytes(response_part[1])
                                    subject = msg["subject"] or "No Subject"
                                    st.markdown(f"**Found:** {subject}")
                    else:
                        st.info("No recent receipt emails found.")
                    mail.logout()
                except Exception as ex:
                    st.error(f"Mail Connection Error: {str(ex)}")
        else:
            st.warning("Enter both your email and app password.")

# --- TAB 4: AI AUDITOR ---
with tab4:
    st.markdown("### AI Contract & Fine-Print Auditor")
    contract_text = st.text_area("Paste terms of service or cancellation clauses:", height=150)

    if st.button("Analyze Terms"):
        if contract_text.strip():
            if not ACTIVE_KEY:
                st.error("Missing ANTHROPIC_API_KEY secret/environment variable.")
            else:
                with st.spinner("Analyzing contract text..."):
                    try:
                        headers = {}
                        if WORKSPACE_ID:
                            headers["anthropic-workspace-id"] = WORKSPACE_ID
                        client = anthropic.Anthropic(api_key=ACTIVE_KEY, default_headers=headers if headers else None)
                        res = client.messages.create(
                            model="claude-3-5-sonnet-20240620",
                            max_tokens=400,
                            messages=[{"role": "user", "content": f"Extract hidden cancellation traps, auto-renewal terms, and unexpected fees from:\n{contract_text}"}]
                        )
                        st.markdown(res.content[0].text)
                    except Exception as err:
                        st.error(f"API Error: {str(err)}")
        else:
            st.warning("Paste contract text before running analysis.")
