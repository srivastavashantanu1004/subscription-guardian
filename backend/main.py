import os
import re
import imaplib
import email
import base64
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

# --- BACKGROUND IMAGE BASE64 ENCODER ---
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return ""

bg_image_path = os.path.join(os.path.dirname(__file__), "background.jpg")
bg_base64 = get_base64_image(bg_image_path)

# Build dynamic background CSS if file exists, else fallback to sleek gradient background
bg_css = f"""
    .stApp {{
        background: linear-gradient(rgba(248, 250, 252, 0.85), rgba(248, 250, 252, 0.85)), 
                    url("data:image/jpg;base64,{bg_base64}") no-repeat center center fixed !important;
        background-size: cover !important;
        backdrop-filter: blur(8px) !important;
        -webkit-backdrop-filter: blur(8px) !important;
    }}
""" if bg_base64 else """
    .stApp {
        background: linear-gradient(135deg, #e0e7ff 0%, #fae8ff 50%, #f3e8ff 100%) !important;
    }
"""

# --- HIGH-CONTRAST VIBRANT GLASSMORPHISM CSS ---
st.markdown(f"""
<style>
    #MainMenu {{visibility: hidden;}}
    header {{visibility: hidden;}}
    footer {{visibility: hidden;}}

    {bg_css}

    /* Global Text Visibility */
    h1, h2, h3, h4, h5, h6, p, label, span, div {{
        color: #0f172a !important;
        font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
    }}

    /* Glassmorphism Cards for Metrics */
    [data-testid="stMetricValue"] {{
        font-size: 2.3rem !important;
        font-weight: 800 !important;
        color: #4f46e5 !important;
    }}
    [data-testid="stMetricLabel"] {{
        font-size: 0.9rem !important;
        font-weight: 700 !important;
        color: #475569 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
    }}
    div[data-testid="stMetric"] {{
        background: rgba(255, 255, 255, 0.85) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        padding: 20px 24px !important;
        border-radius: 18px !important;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.08) !important;
        border: 1px solid rgba(255, 255, 255, 0.6) !important;
    }}

    /* Input & Select Box Styling */
    .stTextInput input, .stNumberInput input, .stTextArea textarea, div[data-baseweb="select"] {{
        border-radius: 12px !important;
        border: 1px solid #cbd5e1 !important;
        background-color: rgba(255, 255, 255, 0.9) !important;
        color: #0f172a !important;
        padding: 10px 14px !important;
    }}
    .stTextInput input:focus, .stTextArea textarea:focus {{
        border-color: #6366f1 !important;
        box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.2) !important;
    }}

    /* Vibrant Purple/Indigo Action Buttons */
    .stButton>button {{
        border-radius: 12px !important;
        font-weight: 700 !important;
        border: none !important;
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
        color: #ffffff !important;
        padding: 0.65rem 1.4rem !important;
        box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35) !important;
        transition: all 0.2s ease-in-out !important;
    }}
    .stButton>button:hover {{
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(99, 102, 241, 0.45) !important;
    }}

    /* Glass Cards */
    .glass-card {{
        background: rgba(255, 255, 255, 0.88);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        padding: 22px 26px;
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.7);
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.07);
        margin-bottom: 16px;
    }}

    /* Modern Styled Tabs */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 10px;
        background: rgba(241, 245, 249, 0.8);
        padding: 8px;
        border-radius: 14px;
        backdrop-filter: blur(10px);
    }}
    .stTabs [data-baseweb="tab"] {{
        border-radius: 10px;
        padding: 10px 20px;
        font-weight: 700;
        color: #475569 !important;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: #ffffff !important;
        color: #6366f1 !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important;
    }}
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
            st.error(f"Failed to delete: {str(e)}")
            return False
    else:
        if "subscriptions" in st.session_state and index < len(st.session_state.subscriptions):
            st.session_state.subscriptions.pop(index)
            return True
    return False

# --- EMAIL PARSER ---
def parse_receipt_with_ai(email_body):
    try:
        headers = {}
        if WORKSPACE_ID:
            headers["anthropic-workspace-id"] = WORKSPACE_ID

        client = anthropic.Anthropic(api_key=ACTIVE_KEY, default_headers=headers if headers else None)
        prompt = (
            "Extract the subscription service name and monthly price from this receipt text.\n"
            "Return ONLY a JSON object: {\"name\": \"string\", \"price\": float}\n"
            f"Receipt Text:\n{email_body[:1500]}"
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

# --- HEADER BANNER ---
st.markdown("""
<div style="background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); padding: 32px; border-radius: 22px; margin-bottom: 24px; box-shadow: 0 12px 30px -5px rgba(79, 70, 229, 0.4);">
    <h1 style="color: #ffffff !important; margin: 0; font-size: 2.5rem; font-weight: 800; letter-spacing: -0.02em;">🛡️ Subscription Guardian</h1>
    <p style="color: #e0e7ff !important; margin-top: 6px; font-size: 1.1rem; font-weight: 500;">Smart Expense Auditing, Multi-Inbox Receipt Parser & AI Contract Intelligence</p>
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
    st.metric("Annual Spend", f"₹{total_yearly:.2f}")
with m3:
    st.metric("Tracked Services", len(subscriptions))

st.write("")

# --- TABS ---
tab_dashboard, tab_add, tab_scan, tab_ai = st.tabs([
    "📊 Expense Dashboard", 
    "➕ Add Service", 
    "📬 Inbox Auto-Scan", 
    "🤖 AI Savings & Clause Audit"
])

# --- DASHBOARD TAB ---
with tab_dashboard:
    if subscriptions:
        col_chart, col_list = st.columns([1.2, 1])
        
        with col_chart:
            st.markdown("### 📈 Monthly Expense Breakdown")
            chart_df = pd.DataFrame([
                {"Service": sub["name"], "Cost (₹)": float(sub["price"])}
                for sub in subscriptions
            ]).set_index("Service")
            st.bar_chart(chart_df, y="Cost (₹)", color="#6366f1")
            
        with col_list:
            st.markdown("### 💳 Active Accounts")
            search_query = st.text_input("🔍 Filter list...", placeholder="Type to filter...").strip().lower()
            
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
                                <strong style="font-size: 1.15rem; color: #0f172a;">{sub['name']}</strong>
                                <div style="color: #64748b; font-size: 0.9rem; margin-top: 2px;">{sub['plan']}</div>
                            </div>
                            <div style="font-size: 1.3rem; font-weight: 800; color: #6366f1;">₹{float(sub['price']):.2f}/mo</div>
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

I am writing to formally request the cancellation of my {sub['name']} subscription ({sub['plan']} plan) effective immediately. Please confirm written cancellation and ensure auto-renewal is disabled.

Thank you,
[Your Name]"""
                        st.code(template, language="text")
    else:
        st.info("No active subscriptions logged. Use the tabs above to add or import your subscriptions.")

# --- MANUAL ENTRY TAB ---
with tab_add:
    st.markdown("### ➕ Add Subscription Entry")
    with st.form("add_sub_form", clear_on_submit=True):
        col_a, col_b, col_c = st.columns([2, 2, 1])
        with col_a:
            name = st.text_input("Service Name", placeholder="e.g. Netflix, Spotify")
        with col_b:
            plan = st.text_input("Plan Tier", placeholder="e.g. Premium Individual")
        with col_c:
            price = st.number_input("Monthly Cost (₹)", min_value=0.00, step=10.00, value=0.00)
        
        submitted = st.form_submit_button("Save Subscription")
        if submitted:
            if name and plan and price > 0:
                if add_subscription_to_db(name.strip(), plan.strip(), price):
                    st.success(f"Added {name} successfully!")
                    st.rerun()
            else:
                st.error("Please complete all input fields.")

# --- INBOX SCANNER TAB ---
with tab_scan:
    st.markdown("### 📬 E-Receipt Inbox Auto-Scanner")
    st.write("Automatically identify receipts, invoices, and payment confirmations from your email provider.")
    
    e_col1, e_col2, e_col3 = st.columns([2, 2, 1])
    with e_col1:
        user_email = st.text_input("Email Address", placeholder="user@gmail.com")
    with e_col2:
        user_pass = st.text_input("App Password", type="password", placeholder="xxxx xxxx xxxx xxxx")
    with e_col3:
        imap_host = st.selectbox("Provider", ["imap.gmail.com", "outlook.office365.com", "imap.mail.yahoo.com"])
    
    if st.button("Scan Inbox Now"):
        if user_email and user_pass:
            with st.spinner("Connecting and scanning email inbox..."):
                found_items = scan_inbox_for_receipts(user_email, user_pass, imap_host)
                if found_items:
                    added_count = 0
                    for item in found_items:
                        if add_subscription_to_db(item["name"], "Auto-Detected Receipt", float(item["price"])):
                            added_count += 1
                    st.success(f"Added {added_count} subscriptions from your email!")
                    st.rerun()
                else:
                    st.info("No matching subscription receipts found.")
        else:
            st.warning("Please enter your email credentials.")

# --- AI ADVISOR TAB ---
with tab_ai:
    st.markdown("### 💡 AI Redundancy Optimizer")
    st.write("Scan your active portfolio for overlapping subscriptions and potential savings.")
    
    if st.button("Generate Optimization Advice"):
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
                        "Analyze this subscription list:\n"
                        f"{sub_summary}\n\n"
                        "1. Identify redundant/overlapping services.\n"
                        "2. Provide clear advice on what to cancel.\n"
                        "3. Estimate monthly and annual savings.\n"
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
    
    st.markdown("### 📜 AI Contract & Fine Print Auditor")
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
    contract_text = st.text_area("Agreement Terms", value=SAMPLE_CONTRACTS[selected_sample], height=140)
    
    if st.button("Audit Fine Print"):
        clean_input = contract_text.strip()
        if clean_input:
            with st.spinner("Auditing contract terms..."):
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