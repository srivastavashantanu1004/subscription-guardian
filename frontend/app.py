import os
import streamlit as st
import anthropic
from dotenv import load_dotenv
from supabase import create_client, Client

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Subscription Guardian", page_icon="💳", layout="wide")

# --- CUSTOM CSS (Clean, Human UI) ---
st.markdown("""
<style>
    .stApp {
        background-color: #fafafa;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: 600 !important;
        color: #111827;
    }
    .stTextInput input, .stNumberInput input, .stTextArea textarea {
        border-radius: 8px !important;
        border: 1px solid #e5e7eb !important;
        background-color: #ffffff !important;
    }
    .stButton>button {
        border-radius: 8px !important;
        font-weight: 500 !important;
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

# --- MAIN HEADER ---
st.title("Subscription Guardian")
st.write("Track monthly expenses and review contract terms before renewing.")

if "subscriptions" not in st.session_state:
    st.session_state.subscriptions = []

st.write("")

# --- OVERVIEW METRICS ---
total_spend = sum(sub["price"] for sub in st.session_state.subscriptions)
m1, m2 = st.columns(2)
with m1:
    st.metric("Total Monthly Cost", f"₹{total_spend:.2f}")
with m2:
    st.metric("Active Services", len(st.session_state.subscriptions))

st.write("---")

# --- ADD SUBSCRIPTION ---
st.subheader("Add a Subscription")
with st.form("add_sub_form", clear_on_submit=True):
    col_a, col_b, col_c = st.columns([2, 2, 1])
    with col_a:
        name = st.text_input("Service Name", placeholder="e.g. Netflix, Gym, Cloud Storage")
    with col_b:
        plan = st.text_input("Plan Details", placeholder="e.g. Standard, Individual, Annual")
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
            new_sub = {"name": name.strip(), "plan": plan.strip(), "price": price}
            st.session_state.subscriptions.append(new_sub)
            st.success(f"Added {name} to your list.")
            st.rerun()

st.write("---")

# --- SUBSCRIPTION LIST & CANCELLATION EMAIL GENERATOR ---
st.subheader("Your Active Plans")

if st.session_state.subscriptions:
    for idx, sub in enumerate(st.session_state.subscriptions):
        with st.container():
            c_info, c_action = st.columns([3, 1])
            with c_info:
                st.write(f"**{sub['name']}** — {sub['plan']} | **₹{sub['price']:.2f}** / month")
            with c_action:
                if st.button("Cancellation Email", key=f"cancel_{idx}"):
                    st.session_state[f"show_email_{idx}"] = not st.session_state.get(f"show_email_{idx}", False)
            
            if st.session_state.get(f"show_email_{idx}", False):
                template = f"""Subject: Request for Immediate Cancellation - {sub['name']}

Hello Support Team,

I am writing to formally request the cancellation of my {sub['name']} subscription ({sub['plan']} plan) effective immediately. 

Please ensure that auto-renewal is turned off for my account and confirm that no further charges will be billed to my payment method. 

Kindly reply with written confirmation of this cancellation at your earliest convenience.

Thank you,
[Your Name]
[Your Account Email / Phone Number]"""
                st.code(template, language="text")
else:
    st.info("No subscriptions added yet. Use the form above to get started.")

st.write("---")

# --- CONTRACT & CLAUSE REVIEW ---
st.subheader("Review Terms & Fine Print")
st.write("Paste terms, renewal details, or cancellation policies below to check for unexpected charges or limitations.")

contract_text = st.text_area("Contract or Terms Text", height=180, placeholder="Paste agreement text here...")

if st.button("Review Text"):
    clean_input = contract_text.strip()
    if clean_input:
        st.info("Analyzing document details...")
        try:
            # Pass workspace header dynamically if present
            headers = {}
            if WORKSPACE_ID:
                headers["anthropic-workspace-id"] = WORKSPACE_ID

            client = anthropic.Anthropic(
                api_key=ACTIVE_KEY,
                default_headers=headers if headers else None
            )
            
            response = client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=300,
                messages=[
                    {
                        "role": "user",
                        "content": f"Review this text for subscription charges or fine print:\n\n{clean_input}"
                    }
                ]
            )
            
            st.write("### Review Results")
            st.write(response.content[0].text)
            
        except anthropic.APIError as api_err:
            st.error(f"API Code {api_err.status_code}: {api_err.message}")
        except Exception as e:
            st.error(f"Execution Error: {str(e)}")
    else:
        st.warning("Please paste contract text before reviewing.")