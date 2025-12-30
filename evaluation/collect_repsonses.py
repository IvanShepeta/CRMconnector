"""Collect Responses - збір відповідей агента на 4 запити

Збирає відповіді у форматі JSONL для оцінки якості.
Кожен рядок - окремий JSON об'єкт.
"""

import asyncio
import json
import os
from datetime import datetime
from typing import List, Any
from agent_framework import ChatAgent, MCPStreamableHTTPTool
from agent_framework_azure_ai import AzureAIAgentClient
from azure.identity.aio import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()

# ⚙️ Configuration
DELAY_BETWEEN_QUERIES = 6  # seconds


# 4 Test Queries with ground truth
TEST_CASES = [
    {
        "query": "Привіт, чи є зараз курси по Python?",
        "ground_truth": "Так, зараз доступні курси по Python для початківців та просунутих користувачів. Курс включає основи програмування, структури даних та веб-розробку.",
        "tool_definitions": ["search_courses", "list_courses", "get_course_details"],
    },
    {
        "query": "Скільки коштує курс JavaScript?",
        "ground_truth": "Курс JavaScript коштує від 4000 до 6000 грн в залежності від рівня складності. Базовий курс - 4000 грн, просунутий - 6000 грн.",
        "tool_definitions": ["get_course_price", "search_courses", "get_course_details"],
    },
    {
        "query": "Коли починається наступний набір на курси?",
        "ground_truth": "Наступний набір на курси починається 15 січня 2025 року. Реєстрація відкрита до 10 січня.",
        "tool_definitions": ["get_course_schedule", "get_enrollment_dates"],
    },
    {
        "query": "Хочу записатися на курс React",
        "ground_truth": "Для запису на курс React вам потрібно залишити контактні дані: ім'я, телефон, email. Курс починається 20 січня, тривалість 2 місяці, вартість 5500 грн.",
        "tool_definitions": ["enroll_student", "get_course_details", "create_enrollment"],
    },
]


class ResponseCollector:
    """Collector for agent responses"""
    
    def __init__(self, endpoint: str, model: str, instructions: str):
        self.endpoint = endpoint
        self.model = model
        self.instructions = instructions
        self.results = []
    
    def _create_mcp_tools(self) -> List[Any]:
        """Create MCP tools"""
        return [
            MCPStreamableHTTPTool(
                name="local_server_crmconnector",
                description="MCP server for CRM connector",
                url="http://localhost:3001/mcp",
                headers={}
            ),
        ]
    
    async def collect_response(self, test_case: dict, agent: ChatAgent, thread: Any, index: int):
        """Collect single response"""
        query = test_case["query"]
        
        print(f"\n{'='*70}")
        print(f"[{index + 1}/4] Collecting response...")
        print(f"Query: {query}")
        print(f"{'='*70}\n")
        
        response_parts = []
        tool_calls = []
        
        try:
            async for chunk in agent.run_stream([query], thread=thread):
                if chunk.text:
                    response_parts.append(chunk.text)
                    print(chunk.text, end="", flush=True)
                elif (chunk.raw_representation 
                      and hasattr(chunk.raw_representation, 'raw_representation')
                      and hasattr(chunk.raw_representation.raw_representation, 'step_details')
                      and hasattr(chunk.raw_representation.raw_representation.step_details, 'tool_calls')):
                    calls = chunk.raw_representation.raw_representation.step_details.tool_calls
                    if calls:
                        for call in calls:
                            if hasattr(call, 'function') and hasattr(call.function, 'name'):
                                tool_calls.append(call.function.name)
            
            print()  # New line
            response = "".join(response_parts)
            
            # Create result in required format
            result = {
                "query": query,
                "ground_truth": test_case["ground_truth"],
                "response": response,
                "tool_definitions": test_case["tool_definitions"],
                "tool_calls": tool_calls
            }
            
            print(f"\n{'─'*70}")
            print(f"✓ Response collected")
            print(f"Tools used: {tool_calls if tool_calls else 'None'}")
            print(f"{'─'*70}")
            
            return result
            
        except Exception as e:
            print(f"\n⚠️ ERROR: {str(e)}")
            
            # Still save with error
            return {
                "query": query,
                "ground_truth": test_case["ground_truth"],
                "response": f"ERROR: {str(e)}",
                "tool_definitions": test_case["tool_definitions"],
                "tool_calls": []
            }
    
    async def collect_all(self):
        """Collect all responses"""
        print(f"\n{'='*70}")
        print(f"Response Collection - 4 Queries")
        print(f"Delay: {DELAY_BETWEEN_QUERIES}s between queries")
        print(f"{'='*70}")
        
        async with (
            DefaultAzureCredential() as credential,
            ChatAgent(
                chat_client=AzureAIAgentClient(
                    project_endpoint=self.endpoint,
                    model_deployment_name=self.model,
                    async_credential=credential,
                    agent_name="response-collector-agent",
                    agent_id=None,
                ),
                instructions=self.instructions,
                max_completion_tokens=2048,
                tools=self._create_mcp_tools(),
            ) as agent
        ):
            thread = agent.get_new_thread()
            
            for i, test_case in enumerate(TEST_CASES):
                result = await self.collect_response(test_case, agent, thread, i)
                self.results.append(result)
                
                # Delay between queries (except after last)
                if i < len(TEST_CASES) - 1:
                    print(f"\n⏸️  Waiting {DELAY_BETWEEN_QUERIES}s...")
                    await asyncio.sleep(DELAY_BETWEEN_QUERIES)
        
        self.save_results()
    
    def save_results(self):
        """Save results in JSONL format (one JSON per line)"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = f"evaluation/data/responses_{timestamp}.jsonl"
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Save as JSONL (one JSON object per line)
        with open(filepath, 'w', encoding='utf-8') as f:
            for result in self.results:
                json_line = json.dumps(result, ensure_ascii=False)
                f.write(json_line + '\n')
        
        print(f"\n{'='*70}")
        print(f"✓ Responses saved: {filepath}")
        print(f"Total: {len(self.results)} responses")
        print(f"{'='*70}")
        
        # Also save as regular JSON for readability
        json_filepath = filepath.replace('.jsonl', '.json')
        with open(json_filepath, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Also saved as JSON: {json_filepath}")
        
        # Print sample
        print(f"\n{'='*70}")
        print("SAMPLE OUTPUT (first line):")
        print(f"{'='*70}")
        if self.results:
            print(json.dumps(self.results[0], ensure_ascii=False, indent=2))


async def main():
    """Main entry point"""
    endpoint = os.getenv("ENDPOINT")
    model = os.getenv("MODEL_DEPLOYMENT_NAME")
    instructions = os.getenv("AGENT_INSTRUCTIONS")
    
    if not all([endpoint, model, instructions]):
        print("ERROR: Missing environment variables")
        print("Required: ENDPOINT, MODEL_DEPLOYMENT_NAME, AGENT_INSTRUCTIONS")
        return
    
    collector = ResponseCollector(endpoint, model, instructions)
    await collector.collect_all()
    
    print("\n✓ Collection completed!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
