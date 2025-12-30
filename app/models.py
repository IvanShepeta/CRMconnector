from pydantic import BaseModel, EmailStr
from typing import Optional

class ChatMessage(BaseModel):
    user_id: str
    message: str
    
class ChatResponse(BaseModel):
    role: str  
    content: str
    
class NewConversationRequest(BaseModel):
    user_id: str

class NewConversationRequest(BaseModel):
    user_id: str
