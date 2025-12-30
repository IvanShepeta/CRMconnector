"""Common utilities for evaluation scripts"""

import json
import os
from dataclasses import dataclass, asdict
from typing import List, Dict, Any
from datetime import datetime
from agent_framework import MCPStreamableHTTPTool


@dataclass
class Query:
    """Base query structure"""
    id: str
    text: str
    category: str


@dataclass
class Response:
    """Base response structure"""
    query_id: str
    query: str
    response: str
    tools_used: List[str]
    execution_time: float
    timestamp: str
    category: str = ""


def create_mcp_tool():
    """Create MCP tool instance"""
    return MCPStreamableHTTPTool(
        name="local_server_crmconnector",
        description="MCP server for CRM connector",
        url="http://localhost:3001/mcp",
        headers={}
    )


def save_json(data: Dict[str, Any], filepath: str):
    """Save data to JSON file"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✓ Saved to: {filepath}")


def load_json(filepath: str) -> Dict[str, Any]:
    """Load data from JSON file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def format_time(seconds: float) -> str:
    """Format execution time"""
    return f"{seconds:.2f}s"


def print_header(title: str):
    """Print formatted header"""
    print(f"\n{'='*70}")
    print(f"{title}")
    print(f"{'='*70}\n")


def print_result(success: bool, message: str = ""):
    """Print formatted result"""
    symbol = "✓" if success else "✗"
    status = "PASS" if success else "FAIL"
    print(f"{symbol} {status} {message}")
