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

raw_key = st.secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or ""
ANTHROPIC_API_KEY = raw_key.strip().strip('"').strip("'")

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
    name = st.text_input("Service Name", placeholder="e.g. Netflix, Spotify, Prime")
    plan = st.text_input("Plan Name", placeholder="e.g. Mobile, Premium, Duo, Student")
    price = st.number_input("Monthly Cost (₹)", min_value=0.00, step=10.00, value=0.00)
    
    submitted = st.form_submit_button("Add Subscription")
    if submitted:
        if not name.strip():
            st.error("Please enter a service name.")
        elif not plan.strip():
            st.error("Please enter a plan name.")
        elif price <= 0:
            st.error("Please enter a valid monthly cost greater than ₹0.")
        else:
            new_sub = {"name": name.strip(), "plan": plan.strip(), "price": price}
            st.session_state.subscriptions.append(new_sub)
            st.success(f"Added {name} ({plan}) - ₹{price:.2f}/mo successfully!")
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

if ANTHROPIC_API_KEY:
    masked_key = ANTHROPIC_API_KEY[:8] + "..." + ANTHROPIC_API_KEY[-4:]
    st.caption(f"🔑 Active Key Loaded: `{masked_key}`")
else:
    st.warning("⚠️ No API key detected in Streamlit Secrets.")

contract_text = st.text_area("Paste contract or terms of service below:", height=200)

if st.button("Detect Hidden Clauses"):
    if contract_text:
        st.info("Analyzing contract text with AI...")
        try:
            if not ANTHROPIC_API_KEY:
                st.error("Missing ANTHROPIC_API_KEY in Secrets or .env file!")
            else:
                client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
                
                # Using standard release snapshot string to avoid 404 routing errors
                response = client.messages.create(
                    model="claude-3-5-sonnet-20240620",
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