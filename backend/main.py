import os
import io
from fastapi import FastAPI, UploadFile, File
from dotenv import load_dotenv
from supabase import create_client, Client
import pypdf

# Load environment variables
load_dotenv(dotenv_path="../.env")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Subscription Guardian API running"}

@app.post("/analyze-receipt")
async def analyze_receipt(file: UploadFile = File(...)):
    file_bytes = await file.read()
    pdf_reader = pypdf.PdfReader(io.BytesIO(file_bytes))
    extracted_text = "".join([page.extract_text() or "" for page in pdf_reader.pages])

    ai_result = {
        "service_name": "Netflix",
        "amount": 15.99,
        "billing_cycle": "Monthly",
        "renewal_date": "2026-10-01",
        "hidden_clauses": "Price increases by $2/mo starting next billing cycle."
    }

    if SUPABASE_URL and SUPABASE_KEY and "your-project-id" not in SUPABASE_URL:
        try:
            supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
            db_response = supabase.table("subscriptions").insert(ai_result).execute()
            return {"status": "success", "data": db_response.data}
        except Exception as e:
            return {"status": "error", "message": str(e), "mock_data": ai_result}
    
    return {"status": "success", "mock_data": ai_result}