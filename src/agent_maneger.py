import asyncio
from typing import Dict, Optional, List
from agent_framework import ChatAgent, MCPStreamableHTTPTool
from agent_framework_azure_ai import AzureAIAgentClient
from azure.identity.aio import DefaultAzureCredential
import os
from dotenv import load_dotenv
from datetime import datetime
import json

load_dotenv()

class SimpleContextManager:
    """Простий context manager в пам'яті"""
    
    def __init__(self):
        self.contexts: Dict[int, Dict] = {}
    
    def get_context(self, user_id: int) -> Optional[Dict]:
        """Отримує контекст з пам'яті"""
        return self.contexts.get(user_id)
    
    def save_context(self, user_id: int, data: Dict):
        """Зберігає контекст в пам'ять"""
        if user_id not in self.contexts:
            self.contexts[user_id] = {
                "user_id": user_id,
                "first_contact": datetime.now().isoformat(),
                "conversation_count": 0,
                "viewed_courses": [],
                "company": None,
                "is_corporate": False,
                "preferences": {},
                "history": []
            }
        
        self.contexts[user_id].update(data)
        self.contexts[user_id]["last_updated"] = datetime.now().isoformat()
        self.contexts[user_id]["conversation_count"] += 1
    
    def add_viewed_course(self, user_id: str, course_code: str):
        """Додає переглянутий курс"""
        if user_id in self.contexts:
            if course_code not in self.contexts[user_id]["viewed_courses"]:
                self.contexts[user_id]["viewed_courses"].append(course_code)


class AgentManager:
    """Управління агентами без Redis"""
    
    _instance = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.agent: Optional[ChatAgent] = None
            self.credential: Optional[DefaultAzureCredential] = None
            self.user_threads: Dict[str, any] = {}
            self.context_manager = SimpleContextManager()
            self.initialized = False
            
            self.endpoint = os.getenv("ENDPOINT")
            self.model_deployment = os.getenv("MODEL_DEPLOYMENT_NAME")
            self.agent_instructions = os.getenv("AGENT_INSTRUCTIONS")
    
    async def initialize(self):
        """Ініціалізує агента"""
        async with self._lock:
            if self.initialized:
                return
            
            print("🚀 Ініціалізація Azure AI Agent...")
            
            self.credential = DefaultAzureCredential()
            
            chat_client = AzureAIAgentClient(
                project_endpoint=self.endpoint,
                model_deployment_name=self.model_deployment,
                async_credential=self.credential,
                agent_name="nt-crm-agent",
                agent_id=None,
            )
            
            self.agent = ChatAgent(
                chat_client=chat_client,
                instructions=self.agent_instructions,
                max_completion_tokens=2048,
                tools=self._create_mcp_tools(),
            )
            
            self.initialized = True
            print("✅ Agent готовий до роботи")
    
    def _create_mcp_tools(self):
        """MCP інструменти для CRM"""
        return [
            MCPStreamableHTTPTool(
                name="local_server_crmconnector",
                description="MCP server for CRM courses connector",
                url="http://localhost:3001/mcp",
                headers={}
            ),
        ]
    
    def get_or_create_thread(self, user_id: int):
        """Отримує thread для користувача"""
        if user_id not in self.user_threads:
            if not self.agent:
                raise RuntimeError("Agent не ініціалізовано")
            self.user_threads[user_id] = self.agent.get_new_thread()
            print(f"📝 Створено thread для: {user_id}")
        
        return self.user_threads[user_id]
    
    def clear_thread(self, user_id: int):
        """Видаляє thread (нова розмова)"""
        if user_id in self.user_threads:
            del self.user_threads[user_id]
            print(f"🗑️ Thread видалено: {user_id}")
    
    def get_user_context(self, user_id: int) -> Dict:
        """Отримує контекст користувача"""
        context = self.context_manager.get_context(user_id)
        if context:
            return {
                "is_returning_client": True,
                "first_contact": context.get("first_contact"),
                "conversation_count": context.get("conversation_count", 0),
                "company": context.get("company"),
                "viewed_courses": context.get("viewed_courses", [])[-5:],
            }
        return {"is_new_client": True}
    
    def save_user_context(self, user_id: int, data: Dict):
        """Зберігає контекст"""
        self.context_manager.save_context(user_id, data)
    
    async def get_agent_response_stream(self, user_id: int, message: str):
        """Стрімить відповідь агента"""
        if not self.initialized:
            await self.initialize()
        
        thread = self.get_or_create_thread(user_id)
        
        # Додаємо контекст
        context = self.get_user_context(user_id)
        context_str = json.dumps(context, ensure_ascii=False)
        
        system_context = (
            f"[SYSTEM] User ID: {user_id}\n"
            f"User Context: {context_str}\n"
            f"Використовуй цю інформацію для персоналізації."
        )
        full_input = f"{system_context}\n\nUser: {message}"
        
        async for chunk in self.agent.run_stream([full_input], thread=thread):
            if chunk.text:
                yield chunk.text
    
    async def close(self):
        """Закриває агента"""
        if self.credential:
            await self.credential.close()
        
        self.user_threads.clear()
        self.initialized = False
        print("👋 Agent Manager закрито")


# Глобальний екземпляр
agent_manager = AgentManager()
