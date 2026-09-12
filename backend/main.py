import os
import streamlit as st
import anthropic
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Subscription Guardian", page_icon="💳", layout="wide")

# --- CUSTOM CSS (Polished Presentation & Light Theme Enforcement) ---
st.markdown("""
<style>
    /* Hide top header bar, menu, and Streamlit branding */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Global App Background */
    .stApp {
        background-color: #ffffff !important;
        color: #1e293b !important;
    }
    
    /* Force Dark Color for Titles, Headers, Labels, and Body Text */
    h1, h2, h3, h4, h5, h6, label, p, span, div {
        color: #0f172a !important;
    }

    /* Metric Display Values */
    [data-testid="stMetricValue"] {
        font-size: 2rem !important;
        font-weight: 700 !important;
        color: #0f172a !important;
    }
    
    [data-testid="stMetricLabel"] {
        color: #475569 !important;
        font-weight: 600 !important;
    }

    /* Form Inputs & Selectboxes */
    .stTextInput input, .stNumberInput input, .stTextArea textarea, div[data-baseweb="select"] {
        border-radius: 8px !important;
        border: 1px solid #cbd5e1 !important;
        background-color: #ffffff !important;
        color: #0f172a !important;
    }
    
    /* Buttons */
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

# --- DATABASE OPERATIONS (CRUD) ---
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

# --- HEADER SECTION ---
st.title("Subscription Guardian")
st.write("Track recurring commitments, visualize annual projections, and analyze contract terms with AI.")

subscriptions = fetch_subscriptions()

st.write("")

# --- ANALYTICS & METRICS DASHBOARD ---
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

# --- VISUAL BREAKDOWN CHART ---
if subscriptions:
    st.subheader("Spending Distribution")
    chart_df = pd.DataFrame([
        {"Service": sub["name"], "Monthly Cost (₹)": float(sub["price"])}
        for sub in subscriptions
    ]).set_index("Service")
    
    st.bar_chart(chart_df, y="Monthly Cost (₹)")
    st.write("---")

# --- ADD NEW SUBSCRIPTION FORM ---
st.subheader("Add Subscription")
with st.form("add_sub_form", clear_on_submit=True):
    col_a, col_b, col_c = st.columns([2, 2, 1])
    with col_a:
        name = st.text_input("Service Name", placeholder="e.g. Netflix, Gym, AWS")
    with col_b:
        plan = st.text_input("Plan Details", placeholder="e.g. Premium Tier, Annual")
    with col_c:
        price = st.number_input("Cost (₹/mo)", min_value=0.00, step=10.00, value=0.00)
    
    submitted = st.form_submit_button("Save Subscription")
    if submitted:
        if not name.strip():
            st.error("Please enter a service name.")
        elif not plan.strip():
            st.error("Please specify plan details.")
        elif price <= 0:
            st.error("Please enter a valid monthly price.")
        else:
            if add_subscription_to_db(name.strip(), plan.strip(), price):
                st.success(f"Added {name} successfully.")
                st.rerun()

st.write("---")

# --- ACTIVE SUBSCRIPTIONS & MANAGEMENT ---
st.subheader("Active Subscriptions")

# Search / Filter Bar
search_query = st.text_input("🔍 Search subscriptions", placeholder="Filter by service name...").strip().lower()

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

Please disable auto-renewal for my account and confirm in writing that no further charges will occur.

Thank you,
[Your Name]
[Your Account Email]"""
                st.code(template, language="text")
else:
    st.info("No active subscriptions found matching your query.")

st.write("---")

# --- CONTRACT & CLAUSE AI AUDITOR ---
st.subheader("Review Terms & Fine Print")
st.write("Paste contract text or select a demo sample below to audit cancellation windows and auto-renewals.")

SAMPLE_CONTRACTS = {
    "Custom Text": "",
    "Sample 1: SaaS Software Agreement (Auto-Renew Risk)": (
        "This subscription automatically renews for consecutive 12-month periods unless canceled "
        "at least 60 days prior to the end of the current term. Cancellations submitted within 60 days of renewal "
        "will incur a 50% early termination penalty fee."
    ),
    "Sample 2: Fitness Club Membership (Notice Period)": (
        "Membership rates increase by 8% annually on January 1st. Members must submit cancellation notices in writing "
        "in person at the local facility. A 30-day processing period applies during which monthly dues will still be billed."
    )
}

selected_sample = st.selectbox("Pre-load Demo Sample (For Panel Testing)", list(SAMPLE_CONTRACTS.keys()))

default_text = SAMPLE_CONTRACTS[selected_sample]
contract_text = st.text_area("Contract Terms Text", value=default_text, height=150, placeholder="Paste agreement terms here...")

if st.button("Run AI Clause Audit"):
    clean_input = contract_text.strip()
    if clean_input:
        st.info("Auditing text for contractual risks...")
        try:
            headers = {}
            if WORKSPACE_ID:
                headers["anthropic-workspace-id"] = WORKSPACE_ID

            client = anthropic.Anthropic(
                api_key=ACTIVE_KEY,
                default_headers=headers if headers else None
            )
            
            prompt = (
                "Analyze the following contract text. Structure your response into 3 concise bullet points:\n"
                "1. Auto-Renewal & Notice Period Requirements\n"
                "2. Hidden Fees or Cancellation Penalties\n"
                "3. Overall Risk Rating (Low, Medium, High)\n\n"
                f"Contract Text:\n{clean_input}"
            )

            response = client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=400,
                messages=[{"role": "user", "content": prompt}]
            )
            
            st.success("Analysis Complete")
            st.markdown(response.content[0].text)
            
        except anthropic.APIError as api_err:
            st.error(f"API Error {api_err.status_code}: {api_err.message}")
        except Exception as e:
            st.error(f"Execution Error: {str(e)}")
    else:
        st.warning("Please enter or select contract text before running the audit.")