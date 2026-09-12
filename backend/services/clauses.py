from fastapi import APIRouter
from config import supabase

router = APIRouter()

@router.get("/clauses/{subscription_id}")
def get_clauses(subscription_id: int):
    result = supabase.table("hidden_clauses").select("*").eq("subscription_id", subscription_id).execute()
    return result.data
