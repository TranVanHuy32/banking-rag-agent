# api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api_router import api_router
from src.generation.rag_engine import rag_engine

app = FastAPI(title="ABC AI Agent", version="1.0.0")

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

@app.on_event("startup")
async def _startup():
    await rag_engine.start()

@app.on_event("shutdown")
async def _shutdown():
    await rag_engine.shutdown()

@app.get("/healthz")
async def healthz():
    return {"ok": True}
