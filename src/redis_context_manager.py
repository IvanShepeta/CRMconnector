import json
import redis.asyncio as redis
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import os

class RedisContextManager:
    """Управління контекстом через Redis для швидкого доступу"""
    
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.client: Optional[redis.Redis] = None
        self.session_ttl = 86400 * 7  # 7 днів
    
    async def connect(self):
        """Встановлює з'єднання з Redis"""
        self.client = await redis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
    
    async def close(self):
        """Закриває з'єднання"""
        if self.client:
            await self.client.close()
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    def _get_user_key(self, user_id: str) -> str:
        """Генерує ключ для користувача"""
        return f"user:context:{user_id}"
    
    def _get_history_key(self, user_id: str) -> str:
        """Ключ для історії розмов"""
        return f"user:history:{user_id}"
    
    async def save_context(self, user_id: str, context: Dict) -> None:
        """Зберігає контекст користувача з TTL"""
        context["last_updated"] = datetime.now().isoformat()
        
        key = self._get_user_key(user_id)
        await self.client.setex(
            key,
            self.session_ttl,
            json.dumps(context, ensure_ascii=False)
        )
    
    async def load_context(self, user_id: str) -> Optional[Dict]:
        """Завантажує контекст користувача"""
        key = self._get_user_key(user_id)
        data = await self.client.get(key)
        
        if not data:
            return None
        
        return json.loads(data)
    
    async def update_context(self, user_id: str, updates: Dict) -> Dict:
        """Оновлює контекст користувача"""
        context = await self.load_context(user_id)
        
        if not context:
            context = {
                "user_id": user_id,
                "first_contact": datetime.now().isoformat(),
                "conversation_count": 0,
                "preferences": {},
                "viewed_courses": [],
                "company": None,
                "is_corporate": False
            }
        
        context.update(updates)
        context["conversation_count"] = context.get("conversation_count", 0) + 1
        
        await self.save_context(user_id, context)
        return context
    
    async def add_to_history(
        self, 
        user_id: str, 
        interaction: Dict
    ) -> None:
        """Додає запис до історії (використовує Redis List)"""
        history_key = self._get_history_key(user_id)
        
        interaction["timestamp"] = datetime.now().isoformat()
        await self.client.lpush(
            history_key,
            json.dumps(interaction, ensure_ascii=False)
        )
        
        # Зберігаємо тільки останні 50 записів
        await self.client.ltrim(history_key, 0, 49)
        await self.client.expire(history_key, self.session_ttl)
    
    async def get_history(
        self, 
        user_id: str, 
        limit: int = 10
    ) -> List[Dict]:
        """Отримує історію взаємодій"""
        history_key = self._get_history_key(user_id)
        items = await self.client.lrange(history_key, 0, limit - 1)
        
        return [json.loads(item) for item in items]
    
    async def add_viewed_course(self, user_id: str, course_code: str) -> None:
        """Додає курс до переглянутих (використовує Redis Set)"""
        key = f"user:viewed:{user_id}"
        await self.client.sadd(key, course_code)
        await self.client.expire(key, self.session_ttl)
    
    async def get_viewed_courses(self, user_id: str) -> List[str]:
        """Отримує список переглянутих курсів"""
        key = f"user:viewed:{user_id}"
        return list(await self.client.smembers(key))
    
    async def increment_metric(self, metric_name: str) -> int:
        """Лічильники для аналітики"""
        key = f"metrics:{metric_name}:{datetime.now().date()}"
        count = await self.client.incr(key)
        await self.client.expire(key, 86400 * 30)  # 30 днів
        return count
