import json
import requests
from requests_ntlm import HttpNtlmAuth
from mcp.server.fastmcp import FastMCP
from typing import List, Dict, Optional
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Конфігурація CRM
CRM_CONFIG = {
    "url": os.getenv("URL"),
    "username": os.getenv("USERNAME"),
    "password": os.getenv("PASSWORD")
}


# Ініціалізація MCP сервера
server = FastMCP("CRM Courses Connector")


def _get_crm_data(endpoint: str, params: Dict = None) -> List[Dict]:
    """Внутрішня функція для CRM запитів"""
    url = f"{CRM_CONFIG['url']}/{endpoint}"
    auth = HttpNtlmAuth(CRM_CONFIG['username'], CRM_CONFIG['password'])

    response = requests.get(url, params=params, auth=auth)
    response.raise_for_status()
    return response.json().get('value', [])


@server.tool(
    name="get_active_courses",
    title="Отримати активні курси",
    description="Витягує список активних курсів з CRM (код, назва, ціна, тривалість, лінк)"
)
async def get_active_courses(search: Optional[str] = None, limit: int = 10) -> str:
    """
    Отримує активні курси з таблиці products.

    Args:
        search: Пошук за назвою (опціонально)
        limit: Кількість курсів (за замовчуванням 10)
    """
    params = {
        "$filter": "isstockitem eq false and new_nameua ne null",
        "$select": "productnumber,new_nameua,producturl,new_abstractua,new_hours,price",
        "$orderby": "new_nameua asc",
        "$top": limit
    }

    if search:
        params["$filter"] += f" and contains(new_nameua,'{search}')"

    courses = _get_crm_data("products", params)

    if not courses:
        return "Активні курси не знайдено."

    result = []
    for course in courses:
        result.append({
            "code": course.get("productnumber", ""),
            "name_ua": course.get("new_nameua", ""),
            "price": float(course.get("price_base", 0)),
            "hours": float(course.get("new_hours", 0)),
            "url": course.get("producturl", ""),
            "description": course.get("new_abstractua", "")[:200] + "..." if course.get("new_abstractua") else ""
        })

    return json.dumps(result, ensure_ascii=False, indent=2)


@server.tool(
    name="search_courses",
    title="Пошук курсів",
    description="Шукає курси за ключовими словами в назві або описі"
)
async def search_courses(query: str, limit: int = 20) -> str:
    """
    Шукає курси за ключовими словами.

    Args:
        query: Ключові слова для пошуку
        limit: Максимальна кількість результатів
    """
    if not query:
        return "Потрібно вказати запит для пошуку."

    params = {
        "$filter": f"contains(new_nameua,'{query}') or contains(new_abstractua,'{query}') and isstockitem eq false",
        "$select": "productnumber,new_nameua,producturl,new_hours,price_base",
        "$top": limit
    }

    courses = _get_crm_data("products", params)

    if not courses:
        return f"Курси за запитом '{query}' не знайдено."

    result = [{"code": c.get("productnumber"), "name": c.get("new_nameua"),
               "hours": c.get("new_hours"), "price": c.get("price_base")} for c in courses]
    return json.dumps(result, ensure_ascii=False, indent=2)


@server.tool(
    name="get_course_by_code",
    title="Курс за кодом",
    description="Отримує детальну інформацію про курс за його кодом (productnumber)"
)
async def get_course_by_code(code: str) -> str:
    """
    Отримує курс за точним кодом.

    Args:
        code: Код курсу (productnumber)
    """
    params = {
        "$filter": f"productnumber eq '{code}' and isstockitem eq false",
        "$select": "productnumber,new_nameua,producturl,new_abstractua,new_hours,price_base"
    }

    courses = _get_crm_data("products", params)

    if not courses:
        return f"Курс з кодом '{code}' не знайдено."

    course = courses[0]
    result = {
        "code": course.get("productnumber"),
        "name_ua": course.get("new_nameua"),
        "description": course.get("new_abstractua"),
        "hours": float(course.get("new_hours", 0)),
        "price": float(course.get("price_base", 0)),
        "url": course.get("producturl")
    }
    return json.dumps(result, ensure_ascii=False, indent=2)

# ...existing code...
@server.tool(
    name="health",
    title="Health check",
    description="Простіше перевірити, що сервер живий"
)
async def health() -> str:
    return "ok"

import os
import sys
if __name__ == "__main__":
    transport_type = sys.argv[1] if len(sys.argv) > 1 else "http"
    server.settings.log_level = os.environ.get("LOG_LEVEL", "DEBUG")

    if transport_type == "http":
        port = int(os.environ.get("PORT", 3001))
        server.settings.port = port
        server.settings.host = "127.0.0.1"
        print(f"Starting MCP server (http) on {server.settings.host}:{server.settings.port} ...")
        server.run(transport="streamable-http")
    elif transport_type == "stdio":
        print("Starting MCP server (stdio) ...")
        server.run(transport="stdio")
    else:
        print("Invalid transport type. Use 'http' or 'stdio'.")
        sys.exit(1)
