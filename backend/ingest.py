from fastapi import APIRouter, UploadFile, File, Form
from services.ai_parser import parse_subscription
from services.pdf_parser import extract_text_from_pdf

router = APIRouter()

@router.post("/ingest/text")
async def ingest_text(text: str = Form(...), user_id: str = Form(...)):
    result = parse_subscription(text, user_id)
    return result

@router.post("/ingest/pdf")
async def ingest_pdf(file: UploadFile = File(...), user_id: str = Form(...)):
    file_bytes = await file.read()
    text = extract_text_from_pdf(file_bytes)
    result = parse_subscription(text, user_id)
    return result
