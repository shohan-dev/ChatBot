from pydantic import BaseModel
from typing import Optional

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None  # Optional - auto-generated if not provided
    user_id: Optional[str] = None  # Optional user ID for automatic lookup
    language: Optional[str] = "EN"  # Language preference: EN or BN

class ChatResponse(BaseModel):
    response: str
    conversation_id: Optional[str] = None  # Return conversation ID for continuity
