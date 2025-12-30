from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.routers import route
from contextlib import asynccontextmanager
from src.agent_maneger import agent_manager
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

import logging
import time


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager для FastAPI.
    Ініціалізує агента при старті та закриває при завершенні.
    """
    print("🚀 Запуск FastAPI сервера...")
    
    # Startup: ініціалізуємо агента
    await agent_manager.initialize()
    
    yield
    
    # Shutdown: закриваємо агента
    print("🛑 Зупинка FastAPI сервера...")
    await agent_manager.close()

# Створюємо FastAPI додаток
app = FastAPI(
    title="NT.UA Chat API",
    description="API для чату з AI консультантом курсів",
    version="1.0.0",
    lifespan=lifespan
)

# Settings for logging
logging.basicConfig(level=logging.INFO)

# Middleware for logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logging.info(f"{request.method} {request.url.path} {response.status_code} {process_time:.2f}s")
    return response



# CORS для локальної розробки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(route.router)


# Статичні файли (HTML/CSS/JS)
static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_path), name="static")

@app.get("/", response_class=HTMLResponse)
async def get_index():
    """Повертає головну сторінку чату"""
    index_file = static_path / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return HTMLResponse("<h1>Chat interface - створіть static/index.html</h1>")

@app.get("/health")
async def health_check():
    """Перевірка здоров'я сервера"""
    return {
        "status": "healthy",
        "agent_initialized": agent_manager.initialized,
        "active_threads": len(agent_manager.user_threads)
    }


