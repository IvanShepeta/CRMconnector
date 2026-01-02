from pydantic import BaseModel, EmailStr
from typing import Optional

class ChatMessage(BaseModel):
    user_id: int
    message: str
    
class ChatResponse(BaseModel):
    role: str  
    content: int
    
class NewConversationRequest(BaseModel):
    user_id: int

