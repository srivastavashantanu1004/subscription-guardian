import os
import streamlit as st
import anthropic
from dotenv import load_dotenv
from supabase import create_client, Client

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Subscription Guardian", page_icon="🛡️", layout="wide")

# --- LOAD ENVIRONMENT & SECRETS ---
load_dotenv(dotenv_path="../.env")

SUPABASE_URL = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")
ANTHROPIC_API_KEY = st.secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")

# Initialize Supabase client if keys exist
supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        st.error(f"Failed to connect to Supabase: {e}")

# --- HEADER SECTION ---
st.title("🛡️ Subscription Guardian")
st.caption("AI Subscription Manager & Hidden Clause Detector")

# Initialize session state for temporary storing if DB isn't loaded
if "subscriptions" not in st.session_state:
    st.session_state.subscriptions = []

# --- TOP METRICS ---
total_spend = sum(sub["price"] for sub in st.session_state.subscriptions)
col1, col2 = st.columns(2)
col1.metric("Total Monthly Spend", f"₹{total_spend:.2f}")
col2.metric("Active Subscriptions", len(st.session_state.subscriptions))

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
        new_sub = {"name": name, "plan": plan, "price": prices[plan]}
        st.session_state.subscriptions.append(new_sub)
        st.success(f"Added {name} ({plan}) successfully!")
        st.rerun()

st.divider()

# --- DISPLAY SUBSCRIPTIONS ---
st.subheader("📋 Your Subscriptions")
if st.session_state.subscriptions:
    for idx, sub in enumerate(st.session_state.subscriptions):
        st.write(f"**{idx + 1}. {sub['name']}** - {sub['plan']} (₹{sub['price']:.2f}/mo)")
else:
    st.info("No active subscriptions added yet.")

st.divider()

# --- AI CONTRACT ANALYSIS ---
st.subheader("🔍 Analyze Terms & Conditions")
contract_text = st.text_area("Paste contract or terms of service below:", height=200)

if st.button("Detect Hidden Clauses"):
    if contract_text:
        st.info("Analyzing contract text with AI...")
        try:
            if not ANTHROPIC_API_KEY:
                st.error("Missing ANTHROPIC_API_KEY in Secrets or .env file!")
            else:
                client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
                
                response = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=500,
                    messages=[{
                        "role": "user", 
                        "content": f"Analyze these terms of service and list key potential hidden clauses, auto-renewals, unexpected charges, or cancellation restrictions in bullet points:\n\n{contract_text}"
                    }]
                )
                
                st.success("Analysis Complete!")
                st.write(response.content[0].text)
        except Exception as e:
            st.error(f"Error during analysis: {e}")
    else:
        st.warning("Please paste some text to analyze.")