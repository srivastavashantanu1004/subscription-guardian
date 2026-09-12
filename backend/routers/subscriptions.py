from fastapi import APIRouter
from config import supabase

router = APIRouter()

@router.get("/subscriptions/{user_id}")
def get_subscriptions(user_id: str):
    result = supabase.table("subscriptions").select("*").eq("user_id", user_id).execute()
    return result.data
