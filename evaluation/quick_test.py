"""
Quick Test Script - 10 Essential Queries

Simplified script for testing agent with 10 most important queries.
"""

import asyncio
import json
import os
from datetime import datetime
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
from agent_framework import ChatAgent, MCPStreamableHTTPTool
from agent_framework_azure_ai import AzureAIAgentClient
from azure.identity.aio import DefaultAzureCredential
from agent_framework.observability import setup_observability
from dotenv import load_dotenv

load_dotenv()

# ⚙️ CONFIGURATION
DELAY_BETWEEN_QUERIES = 6  # seconds - prevents rate limit errors


@dataclass
class TestQuery:
    """Single test query"""
    id: int
    category: str
    query: str
    expected_tools: List[str]


@dataclass
class QueryResult:
    """Result of query execution"""
    query_id: int
    query: str
    category: str
    response: str
    tools_used: List[str]
    execution_time: float
    timestamp: str


# 10 Essential Test Queries
TEST_QUERIES = [
    TestQuery(
        id=1,
        category="course_search",
        query="Привіт, чи є зараз курси по Python?",
        expected_tools=["search_courses", "get_available_courses"]
    ),
    TestQuery(
        id=2,
        category="course_search",
        query="Які курси доступні для початківців?",
        expected_tools=["list_courses", "filter_courses"]
    ),
    TestQuery(
        id=3,
        category="pricing",
        query="Скільки коштує курс JavaScript?",
        expected_tools=["get_course_price", "get_course_details"]
    ),
    TestQuery(
        id=4,
        category="pricing",
        query="Чи є знижки на курси?",
        expected_tools=["get_discounts", "get_promotions"]
    ),
    TestQuery(
        id=5,
        category="scheduling",
        query="Коли починається наступний набір на курси?",
        expected_tools=["get_course_schedule", "get_enrollment_dates"]
    ),
    TestQuery(
        id=6,
        category="scheduling",
        query="Скільки триває курс Python?",
        expected_tools=["get_course_details", "get_course_info"]
    ),
    TestQuery(
        id=7,
        category="enrollment",
        query="Хочу записатися на курс React",
        expected_tools=["enroll_student", "create_enrollment"]
    ),
    TestQuery(
        id=8,
        category="course_details",
        query="Які теми охоплює курс Python?",
        expected_tools=["get_course_curriculum", "get_course_details"]
    ),
    TestQuery(
        id=9,
        category="course_details",
        query="Чи потрібні попередні знання для курсу?",
        expected_tools=["get_course_prerequisites", "get_course_details"]
    ),
    TestQuery(
        id=10,
        category="conversation",
        query="Дякую за інформацію",
        expected_tools=[]
    ),
]


class QuickTester:
    """Quick tester for 10 essential queries"""
    
    def __init__(self, endpoint: str, model: str, instructions: str):
        self.endpoint = endpoint
        self.model = model
        self.instructions = instructions
        self.results: List[QueryResult] = []
        
        # Setup observability
        otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
        setup_observability(otlp_endpoint=otlp_endpoint, enable_sensitive_data="true")
    
    def _create_mcp_tools(self) -> List[Any]:
        """Create MCP tools for the agent"""
        return [
            MCPStreamableHTTPTool(
                name="local_server_crmconnector",
                description="MCP server for CRM connector - provides course information",
                url="http://localhost:3001/mcp",
                headers={}
            ),
        ]
    
    async def run_query(self, test_query: TestQuery, agent: ChatAgent, thread: Any) -> QueryResult:
        """Run single query and collect response"""
        print(f"\n{'='*70}")
        print(f"[{test_query.id}/10] Category: {test_query.category}")
        print(f"Query: {test_query.query}")
        print(f"{'='*70}")
        
        start_time = asyncio.get_event_loop().time()
        response_parts = []
        tools_used = []
        
        try:
            async for chunk in agent.run_stream([test_query.query], thread=thread):
                if chunk.text:
                    response_parts.append(chunk.text)
                    print(chunk.text, end="", flush=True)
                elif (chunk.raw_representation 
                      and hasattr(chunk.raw_representation, 'raw_representation')
                      and hasattr(chunk.raw_representation.raw_representation, 'step_details')
                      and hasattr(chunk.raw_representation.raw_representation.step_details, 'tool_calls')):
                    tool_calls = chunk.raw_representation.raw_representation.step_details.tool_calls
                    if tool_calls:
                        for tool_call in tool_calls:
                            if hasattr(tool_call, 'function') and hasattr(tool_call.function, 'name'):
                                tools_used.append(tool_call.function.name)
            
            print()  # New line
            
            execution_time = asyncio.get_event_loop().time() - start_time
            response = "".join(response_parts)
            
            # Print summary
            print(f"\n{'─'*70}")
            print(f"Tools used: {tools_used if tools_used else 'None'}")
            print(f"Expected: {test_query.expected_tools if test_query.expected_tools else 'None'}")
            print(f"Time: {execution_time:.2f}s")
            print(f"{'─'*70}")
            
            return QueryResult(
                query_id=test_query.id,
                query=test_query.query,
                category=test_query.category,
                response=response,
                tools_used=tools_used,
                execution_time=execution_time,
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            error_msg = str(e)
            
            # Check if it's a rate limit error
            if "rate limit" in error_msg.lower():
                print(f"\n⚠️  RATE LIMIT ERROR: {error_msg}")
                print(f"Tip: Increase DELAY_BETWEEN_QUERIES in quick_test.py")
            else:
                print(f"\n✗ ERROR: {error_msg}")
            return QueryResult(
                query_id=test_query.id,
                query=test_query.query,
                category=test_query.category,
                response=f"ERROR: {str(e)}",
                tools_used=[],
                execution_time=execution_time,
                timestamp=datetime.now().isoformat()
            )
    
    async def run_all(self):
        """Run all 10 queries"""
        print(f"\n{'='*70}")
        print(f"Quick Test - 10 Essential Queries")
        print(f"{'='*70}\n")
        
        async with (
            DefaultAzureCredential() as credential,
            ChatAgent(
                chat_client=AzureAIAgentClient(
                    project_endpoint=self.endpoint,
                    model_deployment_name=self.model,
                    async_credential=credential,
                    agent_name="quick-test-agent",
                    agent_id=None,
                ),
                instructions=self.instructions,
                max_completion_tokens=4096,
                tools=self._create_mcp_tools(),
            ) as agent
        ):
            thread = agent.get_new_thread()
            
            for i, test_query in enumerate(TEST_QUERIES):
                result = await self.run_query(test_query, agent, thread)
                self.results.append(result)
    
            # ⚙️ Add delay between queries (except after last one)
            if i < len(TEST_QUERIES) - 1:
                print(f"\n⏸️  Waiting {DELAY_BETWEEN_QUERIES}s before next query...")
                await asyncio.sleep(DELAY_BETWEEN_QUERIES)
        
        self.print_summary()
        self.save_results()
    
    def print_summary(self):
        """Print test summary"""
        print(f"\n{'='*70}")
        print(f"TEST SUMMARY")
        print(f"{'='*70}")
        
        total_time = sum(r.execution_time for r in self.results)
        avg_time = total_time / len(self.results) if self.results else 0
        
        print(f"Total Queries: {len(self.results)}")
        print(f"Total Time: {total_time:.2f}s")
        print(f"Average Time: {avg_time:.2f}s")
        
        # Category breakdown
        categories = {}
        for result in self.results:
            if result.category not in categories:
                categories[result.category] = 0
            categories[result.category] += 1
        
        print(f"\nCategory Breakdown:")
        for cat, count in sorted(categories.items()):
            print(f"  {cat}: {count} queries")
        
        # Tool usage
        tools_count = sum(1 for r in self.results if r.tools_used)
        print(f"\nTool Usage:")
        print(f"  Queries with tools: {tools_count}/{len(self.results)}")
        print(f"  Queries without tools: {len(self.results) - tools_count}/{len(self.results)}")
        
        print(f"{'='*70}\n")
    
    def save_results(self, filepath: str = None):
        """Save results to JSON file"""
        if filepath is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"evaluation/data/quick_test_{timestamp}.json"
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        data = {
            "test_name": "Quick Test - 10 Essential Queries",
            "timestamp": datetime.now().isoformat(),
            "total_queries": len(self.results),
            "results": [asdict(r) for r in self.results],
            "statistics": {
                "total_time": sum(r.execution_time for r in self.results),
                "average_time": sum(r.execution_time for r in self.results) / len(self.results) if self.results else 0,
                "categories": {},
                "tool_usage_rate": sum(1 for r in self.results if r.tools_used) / len(self.results) if self.results else 0
            }
        }
        
        # Add category stats
        for result in self.results:
            cat = result.category
            if cat not in data["statistics"]["categories"]:
                data["statistics"]["categories"][cat] = {"count": 0, "total_time": 0}
            data["statistics"]["categories"][cat]["count"] += 1
            data["statistics"]["categories"][cat]["total_time"] += result.execution_time
        
        for cat in data["statistics"]["categories"]:
            count = data["statistics"]["categories"][cat]["count"]
            data["statistics"]["categories"][cat]["avg_time"] = (
                data["statistics"]["categories"][cat]["total_time"] / count
            )
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Results saved to: {filepath}")


async def main():
    """Main entry point"""
    endpoint = os.getenv("ENDPOINT")
    model = os.getenv("MODEL_DEPLOYMENT_NAME")
    instructions = os.getenv("AGENT_INSTRUCTIONS")
    
    if not all([endpoint, model, instructions]):
        print("ERROR: Missing required environment variables")
        print("Required: ENDPOINT, MODEL_DEPLOYMENT_NAME, AGENT_INSTRUCTIONS")
        return
    
    tester = QuickTester(endpoint, model, instructions)
    await tester.run_all()
    
    print("\n✓ Quick test completed successfully!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
