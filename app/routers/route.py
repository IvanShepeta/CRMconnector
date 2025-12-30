from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
import json

from src.agent_maneger import agent_manager
from app.websocket_handler import manager
from app.models import ChatMessage, NewConversationRequest


# Створюємо FastAPI додаток
router  = APIRouter(
    prefix="",
    tags=["chat"],
)




@router.post("/api/new-conversation")
async def new_conversation(request: NewConversationRequest):
    """Створює нову розмову (видаляє старий thread)"""
    agent_manager.clear_thread(request.user_id)
    return {"status": "success", "message": "Нова розмова розпочата"}

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """
    WebSocket ендпоінт для real-time чату.
    Один WebSocket на користувача.
    """
    await manager.connect(websocket, user_id)
    
    try:
        while True:
            # Отримуємо повідомлення від клієнта
            data = await websocket.receive_text()
            message_data = json.loads(data)
            user_message = message_data.get("message", "")
            
            if not user_message:
                continue
            
            # Відправляємо повідомлення користувача назад (підтвердження)
            await manager.send_message(user_id, "user", user_message)
            
            # Отримуємо відповідь від агента в режимі стріму
            full_response = ""
            
            try:
                async for chunk in agent_manager.get_agent_response_stream(
                    user_id, 
                    user_message
                ):
                    full_response += chunk
                    await manager.send_stream_chunk(user_id, chunk)
                
                # Сигналізуємо про завершення
                await manager.send_stream_end(user_id)
                
            except Exception as e:
                error_msg = f"Помилка агента: {str(e)}"
                print(f"❌ {error_msg}")
                await manager.send_message(user_id, "assistant", error_msg)
    
    except WebSocketDisconnect:
        manager.disconnect(user_id)
        print(f"👋 Користувач {user_id} відключився")
    
    except Exception as e:
        print(f"❌ WebSocket помилка: {str(e)}")
        manager.disconnect(user_id)


@router.get("/api/stats")
async def get_stats():
    """Статистика сервера"""
    return {
        "active_users": len(manager.active_connections),
        "total_threads": len(agent_manager.user_threads),
        "agent_initialized": agent_manager.initialized
    }

