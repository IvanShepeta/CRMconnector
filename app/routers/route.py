from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
import json
from src.agent_maneger import agent_manager
from app.models import ChatMessage, NewConversationRequest
from app.websocket_handler import ConnectionManager
from app.redis_connector import RedisConnector
from datetime import timedelta

# Створюємо FastAPI додаток
router  = APIRouter(
    prefix="",
    tags=["chat"],
)


# Ініціалізація
redis_connector = RedisConnector(host="localhost", port=6379)
manager = ConnectionManager(redis_connector)


@router.post("/api/new-conversation")
async def new_conversation(request: NewConversationRequest):
    """Створює нову розмову (видаляє старий thread)"""
    agent_manager.clear_thread(request.user_id)
    return {"status": "success", "message": "Нова розмова розпочата"}

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    """
    WebSocket ендпоінт для real-time чату.
    Логує: user_id, час, IP, історію переписки в Redis.
    """
    await manager.connect(websocket, user_id)
    
    # Привітальне повідомлення
    greeting = """Вітаю!
Я твій NT-помічник. Можу відповідати на твої питання щодо курсів, формату, вартості та наповнення. 
Також можу з'єднати тебе із нашими менеджерами :)
Робочі години Навчального Центру: із 9:00 до 18:00
Чим я можу Вам допомогти?"""
    
    await manager.send_personal_message(user_id, "assistant", greeting)
    
    try:
        while True:
            # Отримуємо повідомлення від клієнта
            data = await websocket.receive_text()
            message_data = json.loads(data)
            user_message = message_data.get("message", "")
            
            if not user_message:
                continue
            
            # Зберігаємо повідомлення користувача
            await manager.send_personal_message(user_id, "user", user_message)
            
             # Отримуємо відповідь від агента в режимі стріму
            full_response = ""
            
            try:
                async for chunk in agent_manager.get_agent_response_stream(
                    user_id, 
                    user_message
                ):
                    full_response += chunk
                    await manager.send_stream_chunk(user_id, chunk)
                    
                # ✅ Зберігаємо повну відповідь
                await manager.save_agent_response(user_id, full_response)
                # Сигналізуємо про завершення
                await manager.send_stream_end(user_id)
                



            except Exception as e:
                error_msg = f"Помилка агента: {str(e)}"
                print(f"❌ {error_msg}")
                await manager.send_message(user_id, "assistant", error_msg)
    
    except WebSocketDisconnect:
        await manager.disconnect(user_id)
    
    except Exception as e:
        print(f"❌ Помилка: {str(e)}")
        await manager.disconnect(user_id)

@router.get("/history/{user_id}")
async def get_chat_history(user_id: int, limit: int = 50):
    """API для отримання історії чату"""
    history = await manager.get_history(user_id, limit)
    session = await manager.get_session_info(user_id)
    
    return {
        "user_id": user_id,
        "session": session,
        "history": history
    }