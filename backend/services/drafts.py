from fastapi import APIRouter
from config import supabase, ANTHROPIC_API_KEY
from pydantic import BaseModel
import anthropic

router = APIRouter()
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

class DraftRequest(BaseModel):
    subscription_id: int
    vendor: str
    tone: str = "firm"

@router.post("/drafts")
def generate_draft(request: DraftRequest):
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        messages=[{"role": "user", "content": f"Write a {request.tone} cancellation letter for {request.vendor}."}]
    )
    draft_text = message.content[0].text
    supabase.table("cancellation_drafts").insert({
        "subscription_id": request.subscription_id,
        "draft_text": draft_text,
        "tone": request.tone
    }).execute()
    return {"draft": draft_text}
