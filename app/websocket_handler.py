from fastapi import WebSocket
from typing import Dict
import json
from datetime import datetime, timedelta
from app.redis_connector import RedisConnector

class ConnectionManager:
    def __init__(self, redis_connector: RedisConnector):
        self.active_connections: Dict[int, WebSocket] = {}
        self.redis = redis_connector
    
    async def connect(self, websocket: WebSocket, user_id: int):
        """Підключити користувача"""
        await websocket.accept()
        
        # Отримуємо IP клієнта
        client_ip = websocket.client.host if websocket.client else "unknown"
        
        # Зберігаємо в активні з'єднання
        self.active_connections[user_id] = websocket
        
        # Створюємо сесію в Redis
        await self.redis.create_session(user_id, client_ip)
        
        print(f"🔌 Підключено: user_id={user_id}, IP={client_ip}")
    
    async def send_personal_message(self, user_id: int, role: str, content: str):
        """Відправити повідомлення користувачу"""
        websocket = self.active_connections.get(user_id)
        
        if websocket:
            message = {
                "timestamp": datetime.utcnow().isoformat(),
                "role": role,
                "content": content
            }
            
            # Відправляємо клієнту
            await websocket.send_text(json.dumps(message))
            
            # Зберігаємо в Redis
            await self.redis.save_message(user_id, role, content)
    
    async def send_stream_chunk(self, user_id: int, chunk: str):
        """Відправити частину стріму"""
        websocket = self.active_connections.get(user_id)
        if websocket:
            await websocket.send_text(json.dumps({
                "type": "stream",
                "chunk": chunk
            }))
    
    async def send_stream_end(self, user_id: int):
        """Сигнал завершення стріму"""
        websocket = self.active_connections.get(user_id)
        if websocket:
            await websocket.send_text(json.dumps({"type": "stream_end"}))
    
    async def disconnect(self, user_id: int):
        """Відключити користувача"""
        websocket = self.active_connections.pop(user_id, None)
        
        if websocket:
            try:
                await websocket.close()
            except:
                pass
            
            # Закриваємо сесію в Redis
            await self.redis.close_session(user_id)
            print(f"👋 Відключено: user_id={user_id}")
    
    async def get_history(self, user_id: int, limit: int = 50):
        """Отримати історію чату"""
        return await self.redis.get_chat_history(user_id, limit)
    
    async def get_session_info(self, user_id: int):
        """Отримати інформацію про сесію"""
        return await self.redis.get_session_info(user_id)
    
    async def save_agent_response(self, user_id: int, response: str):
        """Зберегти відповідь агента після стріму"""
        # print(f"🔵 save_agent_response викликано для user_id={user_id}")
        # print(f"📏 Довжина відповіді: {len(response)} символів")
        # print(f"📄 Перші 100 символів: {response[:100]}")
        try:
            await self.redis.save_message(user_id, "assistant", response)
            print(f"✅ Повідомлення агента збережено в Redis")
        
            # Оновити статистику сесії
            session_key = f"ws:session:{user_id}"
            session_data = await self.redis.redis.get(session_key)
            if session_data:
                data = json.loads(session_data)
                data["total_messages"] = data.get("total_messages", 0) + 1
                data["last_message_time"] = datetime.utcnow().isoformat()
                await self.redis.redis.setex(
                    session_key,
                    timedelta(days=7),
                    json.dumps(data)
                )
            print(f"✅ Статистику оновлено: total_messages={data['total_messages']}")
        except Exception as e:
            print(f"❌ Помилка при збереженні відповіді агента: {str(e)}")

