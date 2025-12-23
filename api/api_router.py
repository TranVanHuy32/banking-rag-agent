# api/api_router.py
from fastapi import APIRouter
from .endpoints.chat import router as chat_router
from .endpoints.health import router as health_router
from .endpoints.tts import router as tts_router

api_router = APIRouter()
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(chat_router,   prefix="/chat",   tags=["chat"])   
api_router.include_router(tts_router,    prefix="/tts",    tags=["tts"]) 
