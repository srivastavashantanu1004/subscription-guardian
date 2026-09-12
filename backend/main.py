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

# --- INJECT VIBRANT GLASSMORPHISM & BACKGROUND CSS ---
BACKGROUND_IMAGE_URL = "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=2000&auto=format&fit=crop"

st.markdown(f"""
<style>
    /* Hide top Streamlit UI elements */
    #MainMenu {{visibility: hidden;}}
    header {{visibility: hidden;}}
    footer {{visibility: hidden;}}

    /* Global Background with Blur Layer */
    .stApp {{
        background: linear-gradient(rgba(15, 23, 42, 0.75), rgba(15, 23, 42, 0.75)), 
                    url("{BACKGROUND_IMAGE_URL}") no-repeat center center fixed !important;
        background-size: cover !important;
    }}

    /* Typography Visibility */
    h1, h2, h3, h4, h5, h6, p, label, span, div {{
        color: #f8fafc !important;
        font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
    }}

    /* Glassmorphism Metric Cards */
    [data-testid="stMetricValue"] {{
        font-size: 2.2rem !important;
        font-weight: 800 !important;
        color: #a855f7 !important;
    }}
    [data-testid="stMetricLabel"] {{
        font-size: 0.85rem !important;
        font-weight: 700 !important;
        color: #cbd5e1 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
    }}
    div[data-testid="stMetric"] {{
        background: rgba(30, 41, 59, 0.7) !important;
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
        padding: 20px 24px !important;
        border-radius: 18px !important;
        box-shadow: 0 10px 30px -5px rgba(0, 0, 0, 0.3) !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
    }}

    /* Inputs & Textareas */
    .stTextInput input, .stNumberInput input, .stTextArea textarea, div[data-baseweb="select"] {{
        border-radius: 12px !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        background-color: rgba(15, 23, 42, 0.6) !important;
        color: #ffffff !important;
        padding: 10px 14px !important;
        backdrop-filter: blur(10px) !important;
    }}
    .stTextInput input:focus, .stTextArea textarea:focus {{
        border-color: #a855f7 !important;
        box-shadow: 0 0 0 4px rgba(168, 85, 247, 0.25) !important;
    }}

    /* Neon Gradient Buttons */
    .stButton>button {{
        border-radius: 12px !important;
        font-weight: 700 !important;
        border: none !important;
        background: linear-gradient(135deg, #a855f7 0%, #6366f1 100%) !important;
        color: #ffffff !important;
        padding: 0.65rem 1.4rem !important;
        box-shadow: 0 4px 15px rgba(168, 85, 247, 0.4) !important;
        transition: all 0.2s ease-in-out !important;
    }}
    .stButton>button:hover {{
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(168, 85, 247, 0.6) !important;
    }}

    /* Glass Cards */
    .glass-card {{
        background: rgba(30, 41, 59, 0.65);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        padding: 22px 26px;
        border-radius: 18px;
        border: 1px solid rgba(255, 255, 255, 0.12);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        margin-bottom: 16px;
    }}

    /* Modern Styled Navigation Tabs */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 10px;
        background: rgba(15, 23, 42, 0.6);
        padding: 8px;
        border-radius: 16px;
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }}
    .stTabs [data-baseweb="tab"] {{
        border-radius: 10px;
        padding: 10px 20px;
        font-weight: 700;
        color: #94a3b8 !important;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: rgba(255, 255, 255, 0.15) !important;
        color: #ffffff !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2) !important;
    }}
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
            st.error(f"Failed to delete: {str(e)}")
            return False
    else:
        if "subscriptions" in st.session_state and index < len(st.session_state.subscriptions):
            st.session_state.subscriptions.pop(index)
            return True
    return False

# --- EMAIL RECEIPT PARSER ---
def parse_receipt_with_ai(email_body):
    try:
        headers = {}
        if WORKSPACE_ID:
            headers["anthropic-workspace-id"] = WORKSPACE_ID

        client = anthropic.Anthropic(api_key=ACTIVE_KEY, default_headers=headers if headers else None)
        prompt = (
            "Extract the subscription service name and monthly price from this text.\n"
            "Return ONLY JSON: {\"name\": \"string\", \"price\": float}\n"
            f"Text:\n{email_body[:1500]}"
        )
        response = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}]
        )
        import json
        match = re.search(r'\{.*\}', response.content[0].text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception:
        pass
    return None

def scan_inbox_for_receipts(email_address, app_password, imap_server="imap.gmail.com"):
    scanned_items = []
    try:
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(email_address, app_password)
        mail.select("inbox")
        status, messages = mail.search(None, '(OR (SUBJECT "Receipt") (SUBJECT "Invoice"))')
        email_ids = messages[0].split()[-5:]
        
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
        st.error(f"Email Error: {str(e)}")
    return scanned_items

# --- HERO BANNER ---
st.markdown("""
<div style="background: linear-gradient(135deg, rgba(168, 85, 247, 0.4) 0%, rgba(99, 102, 241, 0.4) 100%); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); padding: 32px; border-radius: 24px; margin-bottom: 24px; border: 1px solid rgba(255, 255, 255, 0.2); box-shadow: 0 12px 40px rgba(0, 0, 0, 0.35);">
    <h1 style="color: #ffffff !important; margin: 0; font-size: 2.5rem; font-weight: 800;">🛡️ Subscription Guardian</h1>
    <p style="color: #cbd5e1 !important; margin-top: 6px; font-size: 1.1rem; font-weight: 500;">Automated E-Receipt Tracking, Spending Intelligence & Clause Auditing</p>
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

# --- MAIN TABS ---
tab_dashboard, tab_add, tab_scan, tab_ai = st.tabs([
    "📊 Expense Dashboard", 
    "➕ Add Service", 
    "📬 Inbox Auto-Scan", 
    "🤖 AI Savings & Clause Audit"
])

# --- TAB 1: DASHBOARD ---
with tab_dashboard:
    if subscriptions:
        col_chart, col_list = st.columns([1.2, 1])
        
        with col_chart:
            st.markdown("### 📈 Monthly Expense Breakdown")
            chart_df = pd.DataFrame([
                {"Service": sub["name"], "Cost (₹)": float(sub["price"])}
                for sub in subscriptions
            ]).set_index("Service")
            st.bar_chart(chart_df, y="Cost (₹)", color="#a855f7")
            
        with col_list:
            st.markdown("### 💳 Active Subscriptions")
            search_query = st.text_input("🔍 Search active items...", placeholder="Filter by service name...").strip().lower()
            
            filtered = [
                (idx, sub) for idx, sub in enumerate(subscriptions)
                if search_query in sub["name"].lower() or search_query in sub["plan"].lower()
            ]
            
            for idx, sub in filtered:
                sub_id = sub.get("id")
                with st.container():
                    st.markdown(f"""
                    <div class="glass-card">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <strong style="font-size: 1.2rem; color: #ffffff;">{sub['name']}</strong>
                                <div style="color: #cbd5e1; font-size: 0.9rem; margin-top: 2px;">{sub['plan']}</div>
                            </div>
                            <div style="font-size: 1.35rem; font-weight: 800; color: #a855f7;">₹{float(sub['price']):.2f}/mo</div>
                        </div>
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
                        template = f"""Subject: Request for Immediate Cancellation - {sub['name']}

Hello Support Team,

I am writing to formally request the cancellation of my {sub['name']} subscription ({sub['plan']} plan) effective immediately. Please confirm cancellation in writing and ensure auto-renewal is turned off.

Thank you,
[Your Name]"""
                        st.code(template, language="text")
    else:
        st.info("No active subscriptions found. Use the tabs above to register items or auto-scan your inbox.")

# --- TAB 2: ADD SERVICE ---
with tab_add:
    st.markdown("### ➕ Register New Subscription")
    with st.form("add_sub_form", clear_on_submit=True):
        col_a, col_b, col_c = st.columns([2, 2, 1])
        with col_a:
            name = st.text_input("Service Name", placeholder="e.g. Netflix, Spotify")
        with col_b:
            plan = st.text_input("Plan Tier", placeholder="e.g. Premium Family")
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

# --- TAB 3: INBOX SCANNER ---
with tab_scan:
    st.markdown("### 📬 E-Receipt & Invoice Auto-Scanner")
    st.write("Automatically detect and parse monthly digital receipts from your inbox.")
    
    e_col1, e_col2, e_col3 = st.columns([2, 2, 1])
    with e_col1:
        user_email = st.text_input("Email Address", placeholder="user@gmail.com")
    with e_col2:
        user_pass = st.text_input("App Password", type="password", placeholder="xxxx xxxx xxxx xxxx")
    with e_col3:
        imap_host = st.selectbox("IMAP Provider", ["imap.gmail.com", "outlook.office365.com", "imap.mail.yahoo.com"])
    
    if st.button("Scan Inbox Now"):
        if user_email and user_pass:
            with st.spinner("Connecting to inbox and extracting receipts..."):
                found_items = scan_inbox_for_receipts(user_email, user_pass, imap_host)
                if found_items:
                    added_count = 0
                    for item in found_items:
                        if add_subscription_to_db(item["name"], "Auto-Detected Email Receipt", float(item["price"])):
                            added_count += 1
                    st.success(f"Imported {added_count} subscriptions directly from your inbox!")
                    st.rerun()
                else:
                    st.info("No new subscription receipts detected in your recent emails.")
        else:
            st.warning("Please enter your email address and app password.")

# --- TAB 4: AI SAVINGS & AUDIT ---
with tab_ai:
    st.markdown("### 💡 AI Redundancy Optimizer")
    st.write("Scan your portfolio for overlapping services to find potential monthly savings.")
    
    if st.button("Run Savings Audit"):
        if len(subscriptions) < 2:
            st.warning("Add at least 2 subscriptions to execute redundancy checks.")
        else:
            with st.spinner("Analyzing active subscriptions for redundancy..."):
                try:
                    sub_summary = "\n".join([f"- {s['name']}: {s['plan']} (₹{s['price']}/mo)" for s in subscriptions])
                    headers = {}
                    if WORKSPACE_ID:
                        headers["anthropic-workspace-id"] = WORKSPACE_ID
                    client = anthropic.Anthropic(api_key=ACTIVE_KEY, default_headers=headers if headers else None)
                    
                    prompt = (
                        "Analyze this list of user subscriptions:\n"
                        f"{sub_summary}\n\n"
                        "1. Identify redundant/overlapping services (e.g. multiple music or streaming platforms).\n"
                        "2. Give actionable advice on what to cancel.\n"
                        "3. Estimate potential monthly and annual savings.\n"
                        "Format cleanly using Markdown."
                    )
                    
                    res = client.messages.create(
                        model="claude-3-5-sonnet-20240620",
                        max_tokens=400,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    st.markdown(res.content[0].text)
                except Exception as e:
                    st.error(f"Error generating recommendations: {str(e)}")
                    
    st.write("---")
    
    st.markdown("### 📜 AI Contract Fine-Print Auditor")
    SAMPLE_CONTRACTS = {
        "Custom Entry": "",
        "Sample 1: SaaS Software Agreement (Auto-Renew Penalty)": (
            "This subscription automatically renews for consecutive 12-month periods unless canceled "
            "at least 60 days prior to renewal. Cancellations submitted within 60 days incur a 50% penalty fee."
        ),
        "Sample 2: Gym Membership (30-Day Notice Window)": (
            "Rates increase by 8% annually. Members must submit cancellation notices in person. "
            "A 30-day processing period applies during which monthly fees continue to bill."
        )
    }
    
    selected_sample = st.selectbox("Pre-load Demo Sample", list(SAMPLE_CONTRACTS.keys()))
    contract_text = st.text_area("Agreement Text", value=SAMPLE_CONTRACTS[selected_sample], height=140)
    
    if st.button("Audit Contract Fine Print"):
        clean_input = contract_text.strip()
        if clean_input:
            with st.spinner("Auditing terms with AI..."):
                try:
                    headers = {}
                    if WORKSPACE_ID:
                        headers["anthropic-workspace-id"] = WORKSPACE_ID
                    client = anthropic.Anthropic(api_key=ACTIVE_KEY, default_headers=headers if headers else None)
                    
                    prompt = (
                        "Analyze the contract text below. Provide 3 points:\n"
                        "1. Renewal & Notice Window\n"
                        "2. Penalties or Cancellation Restrictions\n"
                        "3. Overall Risk Rating (Low, Medium, High)\n\n"
                        f"Text:\n{clean_input}"
                    )
                    
                    response = client.messages.create(
                        model="claude-3-5-sonnet-20240620",
                        max_tokens=350,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    st.markdown(response.content[0].text)
                except Exception as e:
                    st.error(f"Audit failed: {str(e)}")
        else:
            st.warning("Please provide agreement terms text.")