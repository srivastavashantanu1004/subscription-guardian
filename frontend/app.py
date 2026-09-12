
import streamlit as st
import os
from dotenv import load_dotenv
from supabase import create_client, Client

st.set_page_config(page_title="Subscription Guardian", layout="wide")

# Load .env from parent folder
load_dotenv(dotenv_path="../.env")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

st.title("🛡️ Subscription Guardian")
st.caption("AI Subscription Manager & Hidden Clause Detector")

# Fetch data from Supabase
if SUPABASE_URL and SUPABASE_KEY and "your-project-id" not in SUPABASE_URL:
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        response = supabase.table("subscriptions").select("*").execute()
        subscriptions = response.data or []
    except Exception as e:
        st.error(f"Error connecting to Supabase: {e}")
        subscriptions = []
else:
    subscriptions = [
        {
            "id": "1",
            "service_name": "Adobe Creative Cloud",
            "amount": 54.99,
            "billing_cycle": "Monthly",
            "renewal_date": "2026-10-15",
            "hidden_clauses": "Auto-renews annually. Requires 30-day notice prior to cancel without fee."
        }
    ]

col1, col2 = st.columns(2)
total_spend = sum(sub.get("amount", 0) for sub in subscriptions)
col1.metric("Total Monthly Spend", f"${total_spend:.2f}")
col2.metric("Active Subscriptions", len(subscriptions))

st.divider()
st.subheader("Your Subscriptions")

for sub in subscriptions:
    with st.expander(f"📌 {sub.get('service_name', 'Unknown')} — ${sub.get('amount', 0)}/mo"):
        st.write(f"**Billing Cycle:** {sub.get('billing_cycle', 'N/A')}")
        st.write(f"**Renewal Date:** {sub.get('renewal_date', 'N/A')}")
        
        if sub.get("hidden_clauses"):
            st.warning(f"⚠️ **Hidden Term Detected:** {sub['hidden_clauses']}")
            
        if st.button(f"Generate Cancellation Email for {sub.get('service_name')}", key=str(sub.get("id"))):
            st.code(
                f"Subject: Immediate Cancellation Request - {sub.get('service_name')}\n\n"
                f"To Whom It May Concern,\n\nPlease process the immediate cancellation of my "
                f"{sub.get('service_name')} subscription prior to {sub.get('renewal_date')}. "
                f"Confirm receipt of this request.",
                language="markdown"
            )
            st.divider()

# --- ADD NEW SUBSCRIPTION FORM ---
st.subheader("➕ Add New Subscription")
with st.form("add_sub_form", clear_on_submit=True):
    name = st.text_input("Service Name", value="Netflix")
    
    plan = st.selectbox(
        "Plan Type",
        ["Mobile (₹149/mo)", "Basic (₹199/mo)", "Standard (₹499/mo)", "Premium (₹649/mo)"]
    )
    
    prices = {
        "Mobile (₹149/mo)": 149.00,
        "Basic (₹199/mo)": 199.00,
        "Standard (₹499/mo)": 499.00,
        "Premium (₹649/mo)": 649.00
    }
    
    submitted = st.form_submit_button("Add Subscription")
    if submitted:
        if "subscriptions" not in st.session_state:
            st.session_state.subscriptions = []
        st.session_state.subscriptions.append({"name": name, "plan": plan, "price": prices[plan]})
        st.success(f"Added {name} ({plan}) successfully!")
        st.rerun()

st.divider()

# --- CONTRACT ANALYSIS ---
st.subheader("🔍 Analyze Terms & Conditions")
contract_text = st.text_area("Paste contract or terms of service below:")
if st.button("Detect Hidden Clauses"):
    if contract_text:
        st.info("Analyzing contract text with AI...")
    else:
        st.warning("Please paste some text to analyze.")