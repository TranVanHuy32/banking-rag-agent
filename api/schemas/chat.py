# api/schemas/chat.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    question: str = Field(..., description="User's question or message")
    session_id: Optional[str] = Field(
        None, 
        description="Session ID for maintaining conversation context. If not provided, a new session will be created."
    )
    
class ChatResponse(BaseModel):
    """Response model for chat endpoint"""
    response: str = Field(..., description="AI's response")
    session_id: str = Field(..., description="Session ID for maintaining conversation context")
    sources: List[Dict[str, Any]] = Field(
        default_factory=list, 
        description="List of sources used to generate the response"
    )
