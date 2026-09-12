import os
import re
import imaplib
import email
from email.header import decode_header
import streamlit as st
import anthropic
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Subscription Guardian", page_icon="💳", layout="wide")

# --- CUSTOM CSS (Clean Presentation & High Contrast) ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    .stApp {
        background-color: #ffffff !important;
        color: #1e293b !important;
    }
    
    h1, h2, h3, h4, h5, h6, label, p, span, div {
        color: #0f172a !important;
    }

    [data-testid="stMetricValue"] {
        font-size: 2rem !important;
        font-weight: 700 !important;
        color: #0f172a !important;
    }
    
    [data-testid="stMetricLabel"] {
        color: #475569 !important;
        font-weight: 600 !important;
    }

    .stTextInput input, .stNumberInput input, .stTextArea textarea, div[data-baseweb="select"] {
        border-radius: 8px !important;
        border: 1px solid #cbd5e1 !important;
        background-color: #ffffff !important;
        color: #0f172a !important;
    }
    
    .stButton>button {
        border-radius: 8px !important;
        font-weight: 600 !important;
        border: none !important;
        background-color: #0f172a !important;
        color: #ffffff !important;
        padding: 0.5rem 1rem !important;
    }
    .stButton>button:hover {
        background-color: #1e293b !important;
        color: #ffffff !important;
    }
</style>
""", unsafe_allow_html=True)

# --- LOAD ENVIRONMENT & SECRETS ---
load_dotenv(dotenv_path="../.env")

SUPABASE_URL = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")

raw_key = st.secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or ""
ACTIVE_KEY = str(raw_key).strip().strip('"').strip("'").strip()

raw_workspace = st.secrets.get("ANTHROPIC_WORKSPACE_ID") or os.getenv("ANTHROPIC_WORKSPACE_ID") or ""
WORKSPACE_ID = str(raw_workspace).strip().strip('"').strip("'").strip()

# Initialize Supabase client
supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception:
        pass

# --- DATABASE OPERATIONS ---
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
            st.error(f"Failed to delete record: {str(e)}")
            return False
    else:
        if "subscriptions" in st.session_state and index < len(st.session_state.subscriptions):
            st.session_state.subscriptions.pop(index)
            return True
    return False

# --- EMAIL SCANNING (IMAP + AI PARSER) ---
def parse_receipt_with_ai(email_body):
    """Extract vendor name and price using Anthropic Claude."""
    try:
        headers = {}
        if WORKSPACE_ID:
            headers["anthropic-workspace-id"] = WORKSPACE_ID

        client = anthropic.Anthropic(api_key=ACTIVE_KEY, default_headers=headers if headers else None)
        
        prompt = (
            "Extract the subscription service name and monthly price from the following receipt text.\n"
            "Return ONLY a JSON object with keys 'name' (string) and 'price' (numeric float).\n"
            f"Receipt Text:\n{email_body[:1500]}"
        )
        
        response = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}]
        )
        
        raw_res = response.content[0].text
        # Basic extraction fallback
        import json
        match = re.search(r'\{.*\}', raw_res, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception:
        pass
    return None

def scan_inbox_for_receipts(email_address, app_password, imap_server="imap.gmail.com"):
    """Connect to user inbox via IMAP and scan recent receipt emails."""
    scanned_items = []
    try:
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(email_address, app_password)
        mail.select("inbox")
        
        # Search for payment confirmation emails
        status, messages = mail.search(None, '(OR (SUBJECT "Receipt") (SUBJECT "Invoice"))')
        email_ids = messages[0].split()[-5:] # Scan last 5 matching emails
        
        for e_id in email_ids:
            _, msg_data = mail.fetch(e_id, '(RFC822)')
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode(errors="ignore")
                                break
                    else:
                        body = msg.get_payload(decode=True).decode(errors="ignore")
                    
                    if body:
                        parsed = parse_receipt_with_ai(body)
                        if parsed and parsed.get("name") and parsed.get("price"):
                            scanned_items.append(parsed)
        mail.logout()
    except Exception as e:
        st.error(f"Email Connection Error: {str(e)}")
    return scanned_items

# --- HEADER SECTION ---
st.title("Subscription Guardian")
st.write("Track monthly expenses, auto-scan e-receipts from your inboxes, and optimize redundant subscriptions.")

subscriptions = fetch_subscriptions()

st.write("")

# --- METRICS DASHBOARD ---
total_monthly = sum(float(sub["price"]) for sub in subscriptions)
total_yearly = total_monthly * 12

m1, m2, m3 = st.columns(3)
with m1:
    st.metric("Total Monthly Cost", f"₹{total_monthly:.2f}")
with m2:
    st.metric("Annual Commitment", f"₹{total_yearly:.2f}")
with m3:
    st.metric("Active Services", len(subscriptions))

st.write("---")

# --- SPENDING DISTRIBUTION ---
if subscriptions:
    st.subheader("Spending Breakdown")
    chart_df = pd.DataFrame([
        {"Service": sub["name"], "Monthly Cost (₹)": float(sub["price"])}
        for sub in subscriptions
    ]).set_index("Service")
    st.bar_chart(chart_df, y="Monthly Cost (₹)")
    st.write("---")

# --- MULTI-EMAIL E-RECEIPT INGESTION ---
st.subheader("Connect Inbox & Auto-Scan Receipts")
st.write("Link your email account (via App Password) to auto-detect monthly digital receipts and invoices.")

with st.expander("📬 Add & Scan Email Account"):
    e_col1, e_col2, e_col3 = st.columns([2, 2, 1])
    with e_col1:
        user_email = st.text_input("Email Address", placeholder="user@gmail.com")
    with e_col2:
        user_pass = st.text_input("App Password / Secret", type="password", placeholder="xxxx xxxx xxxx xxxx")
    with e_col3:
        imap_host = st.selectbox("Provider", ["imap.gmail.com", "outlook.office365.com", "imap.mail.yahoo.com"])
    
    if st.button("Scan Inbox for Receipts"):
        if user_email and user_pass:
            with st.spinner("Connecting and auditing email receipts..."):
                found_items = scan_inbox_for_receipts(user_email, user_pass, imap_host)
                if found_items:
                    added_count = 0
                    for item in found_items:
                        if add_subscription_to_db(item["name"], "Auto-Detected Email Receipt", float(item["price"])):
                            added_count += 1
                    st.success(f"Successfully imported {added_count} subscriptions from your email!")
                    st.rerun()
                else:
                    st.info("No new subscription receipts detected in recent messages.")
        else:
            st.warning("Please provide both email address and app password.")

st.write("---")

# --- SMART AI RECOMMENDATIONS & CONSOLIDATION ENGINE ---
st.subheader("AI Subscription Optimizer")
st.write("Detect overlapping services and identify potential savings.")

if st.button("Generate Optimization Report"):
    if len(subscriptions) < 2:
        st.warning("Add at least 2 subscriptions to run redundancy analysis.")
    else:
        with st.spinner("Analyzing active subscriptions for redundancy..."):
            try:
                sub_summary = "\n".join([f"- {s['name']}: {s['plan']} (₹{s['price']}/mo)" for s in subscriptions])
                
                headers = {}
                if WORKSPACE_ID:
                    headers["anthropic-workspace-id"] = WORKSPACE_ID
                client = anthropic.Anthropic(api_key=ACTIVE_KEY, default_headers=headers if headers else None)
                
                prompt = (
                    "You are a financial savings advisor. Analyze this list of user subscriptions:\n"
                    f"{sub_summary}\n\n"
                    "1. Identify any overlapping or redundant services (e.g. multiple music streaming, cloud storage, or video platforms).\n"
                    "2. Give actionable advice on which service to consider canceling.\n"
                    "3. Estimate potential monthly and annual savings.\n"
                    "Keep the output clean, structured, and formatted in Markdown."
                )
                
                res = client.messages.create(
                    model="claude-3-5-sonnet-20240620",
                    max_tokens=400,
                    messages=[{"role": "user", "content": prompt}]
                )
                
                st.markdown(res.content[0].text)
            except Exception as e:
                st.error(f"Failed to generate advice: {str(e)}")

st.write("---")

# --- ADD & MANAGE SUBSCRIPTIONS ---
st.subheader("Active Subscriptions & Manual Entry")

with st.form("add_sub_form", clear_on_submit=True):
    col_a, col_b, col_c = st.columns([2, 2, 1])
    with col_a:
        name = st.text_input("Service Name", placeholder="e.g. Spotify, Apple Music")
    with col_b:
        plan = st.text_input("Plan Details", placeholder="e.g. Individual, Family")
    with col_c:
        price = st.number_input("Cost (₹/mo)", min_value=0.00, step=10.00, value=0.00)
    
    submitted = st.form_submit_button("Add Subscription")
    if submitted:
        if name and plan and price > 0:
            if add_subscription_to_db(name.strip(), plan.strip(), price):
                st.success(f"Added {name}.")
                st.rerun()
        else:
            st.error("Please fill out all fields validly.")

search_query = st.text_input("🔍 Search active subscriptions", placeholder="Filter list...").strip().lower()

filtered_subs = [
    (idx, sub) for idx, sub in enumerate(subscriptions)
    if search_query in sub["name"].lower() or search_query in sub["plan"].lower()
]

if filtered_subs:
    for idx, sub in filtered_subs:
        sub_id = sub.get("id")
        with st.container():
            c_info, c_action1, c_action2 = st.columns([3, 1, 1])
            with c_info:
                st.write(f"**{sub['name']}** — {sub['plan']} | **₹{float(sub['price']):.2f}** / month")
            with c_action1:
                if st.button("Cancel Draft", key=f"cancel_{idx}"):
                    st.session_state[f"show_email_{idx}"] = not st.session_state.get(f"show_email_{idx}", False)
            with c_action2:
                if st.button("Delete", key=f"del_{idx}"):
                    if delete_subscription_from_db(sub_id, idx):
                        st.success(f"Removed {sub['name']}")
                        st.rerun()
            
            if st.session_state.get(f"show_email_{idx}", False):
                template = f"""Subject: Request for Immediate Cancellation - {sub['name']}

Hello Support Team,

I am writing to formally request the cancellation of my {sub['name']} subscription ({sub['plan']} plan) effective immediately.

Please turn off auto-renewal for my account and confirm cancellation in writing.

Thank you,
[Your Name]"""
                st.code(template, language="text")
else:
    st.info("No subscriptions found.")