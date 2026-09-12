from fastapi import APIRouter
from config import supabase

router = APIRouter()

@router.get("/alerts/{user_id}")
def get_alerts(user_id: str):
    result = supabase.table("alerts").select("*").eq("acknowledged", False).execute()
    return result.data
