import redis.asyncio as redis
import json
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional

class RedisConnector:
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        self.redis = redis.Redis(
            host=host, 
            port=port, 
            db=db, 
            decode_responses=True
        )
    
    async def ping(self):
        """Перевірка з'єднання"""
        return await self.redis.ping()
    
    async def create_session(self, user_id: int, client_ip: str) -> str:
        """Створити нову сесію"""
        session_data = {
            "user_id": user_id,
            "ip": client_ip,
            "connect_time": datetime.now(timezone.utc).isoformat(),
            "total_messages": 0
        }
        
        await self.redis.setex(
            f"ws:session:{user_id}",
            timedelta(days=7),  # TTL 7 днів
            json.dumps(session_data)
        )
        
        print(f"✅ Створено сесію для user_id={user_id}, IP={client_ip}")
        return session_data["connect_time"]
    
    async def save_message(self, user_id: int, role: str, content: str):
        """Зберегти повідомлення в історію"""
        message = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "role": role,
            "content": content
        }
        
        # Додаємо в список (нові зверху)
        await self.redis.lpush(f"ws:chat:{user_id}", json.dumps(message))
        
        # Обмежуємо історію 500 повідомленнями
        await self.redis.ltrim(f"ws:chat:{user_id}", 0, 499)
        
        # Збільшуємо лічильник
        session_key = f"ws:session:{user_id}"
        session_data = await self.redis.get(session_key)
        if session_data:
            data = json.loads(session_data)
            data["total_messages"] += 1
            await self.redis.setex(session_key, timedelta(days=7), json.dumps(data))
    
    async def get_chat_history(self, user_id: int, limit: int = 50) -> List[Dict]:
        """Отримати історію чату"""
        history = await self.redis.lrange(f"ws:chat:{user_id}", 0, limit - 1)
        messages = [json.loads(msg) for msg in history]
        return list(reversed(messages))  # Старі зверху
    
    async def get_session_info(self, user_id: int) -> Optional[Dict]:
        """Отримати інформацію про сесію"""
        session_data = await self.redis.get(f"ws:session:{user_id}")
        return json.loads(session_data) if session_data else None
    
    async def close_session(self, user_id: int):
        """Закрити сесію"""
        session_key = f"ws:session:{user_id}"
        session_data = await self.redis.get(session_key)
        
        if session_data:
            data = json.loads(session_data)
            data["disconnect_time"] = datetime.now(timezone.utc).isoformat()
            await self.redis.setex(session_key, timedelta(days=7), json.dumps(data))
            print(f"✅ Сесію {user_id} закрито")
    
    async def close(self):
        """Закрити Redis з'єднання"""
        await self.redis.close()
