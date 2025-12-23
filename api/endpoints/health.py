# api/endpoints/health.py
from fastapi import APIRouter

router = APIRouter()

@router.get("", tags=["Health"], summary="Health Check") 
def health_check():
    return {"status": "ok"}