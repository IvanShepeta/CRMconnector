from fastapi import WebSocket
from typing import Dict
import json

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        print(f"✅ Підключено: {user_id}")
    
    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            print(f"❌ Відключено: {user_id}")
    
    async def send_message(self, user_id: str, role: str, content: str):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_text(
                json.dumps({"role": role, "content": content}, ensure_ascii=False)
            )
    
    async def send_stream_chunk(self, user_id: str, chunk: str):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_text(
                json.dumps({"type": "chunk", "content": chunk}, ensure_ascii=False)
            )
    
    async def send_stream_end(self, user_id: str):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_text(
                json.dumps({"type": "stream_end"}, ensure_ascii=False)
            )

manager = ConnectionManager()
