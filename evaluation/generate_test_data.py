"""
Test Data Generator for CRM Connector Agent

Generates synthetic test data including queries, expected responses,
and collects actual agent responses for evaluation.
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from agent_framework import ChatAgent, MCPStreamableHTTPTool
from agent_framework_azure_ai import AzureAIAgentClient
from azure.identity.aio import DefaultAzureCredential
from agent_framework.observability import setup_observability
from dotenv import load_dotenv

load_dotenv()


@dataclass
class SyntheticQuery:
    """Represents a synthetic test query"""
    id: str
    category: str
    query: str
    variations: List[str]
    expected_intent: str
    expected_tools: List[str]
    metadata: Dict[str, Any]


@dataclass
class AgentResponse:
    """Agent's response to a query"""
    query_id: str
    query: str
    response: str
    tools_used: List[str]
    execution_time: float
    timestamp: str
    metadata: Dict[str, Any]


@dataclass
class TestDataset:
    """Complete test dataset with queries and responses"""
    generated_at: str
    total_queries: int
    queries: List[SyntheticQuery]
    responses: List[AgentResponse]
    statistics: Dict[str, Any]


class TestDataGenerator:
    """Generates synthetic test data and collects agent responses"""
    
    def __init__(self):
        self.synthetic_queries = self._generate_synthetic_queries()
    
    def _generate_synthetic_queries(self) -> List[SyntheticQuery]:
        """Generate comprehensive set of synthetic queries"""
        return [
            # Course Search Queries
            SyntheticQuery(
                id="SQ001",
                category="course_search",
                query="Які курси є в наявності?",
                variations=[
                    "Покажіть доступні курси",
                    "Які курси можна пройти?",
                    "Що ви пропонуєте з курсів?",
                    "Які навчальні програми є?"
                ],
                expected_intent="list_all_courses",
                expected_tools=["list_courses", "get_available_courses"],
                metadata={"difficulty": "easy", "requires_context": False}
            ),
            SyntheticQuery(
                id="SQ002",
                category="course_search",
                query="Чи є курси по Python для початківців?",
                variations=[
                    "Python для новачків - є такі курси?",
                    "Хочу вивчити Python з нуля, що маєте?",
                    "Курс Python для тих, хто не програмував",
                    "Базовий курс Python"
                ],
                expected_intent="search_course_by_language_and_level",
                expected_tools=["search_courses", "filter_courses"],
                metadata={"difficulty": "medium", "requires_context": False}
            ),
            SyntheticQuery(
                id="SQ003",
                category="course_search",
                query="Які є курси з веб-розробки?",
                variations=[
                    "Курси по веб-програмуванню",
                    "Хочу стати веб-розробником, що порадите?",
                    "Frontend та backend курси",
                    "Веб-розробка для початківців"
                ],
                expected_intent="search_courses_by_category",
                expected_tools=["search_courses", "filter_by_category"],
                metadata={"difficulty": "medium", "requires_context": False}
            ),
            
            # Pricing Queries
            SyntheticQuery(
                id="SQ004",
                category="pricing",
                query="Скільки коштує курс JavaScript?",
                variations=[
                    "Яка ціна на JavaScript?",
                    "Вартість курсу JavaScript",
                    "Ціна навчання JavaScript",
                    "Скільки треба заплатити за JavaScript курс?"
                ],
                expected_intent="get_course_price",
                expected_tools=["get_course_price", "get_course_details"],
                metadata={"difficulty": "medium", "requires_context": False}
            ),
            SyntheticQuery(
                id="SQ005",
                category="pricing",
                query="Чи є знижки на курси?",
                variations=[
                    "Які знижки діють зараз?",
                    "Акції на навчання",
                    "Можна купити курс зі знижкою?",
                    "Промокоди на курси"
                ],
                expected_intent="get_discounts",
                expected_tools=["get_discounts", "get_promotions"],
                metadata={"difficulty": "easy", "requires_context": False}
            ),
            SyntheticQuery(
                id="SQ006",
                category="pricing",
                query="Чи можна оплатити курс частинами?",
                variations=[
                    "Розстрочка на навчання",
                    "Оплата курсу по частинах",
                    "Чи є можливість платити поетапно?",
                    "Розтермінування платежу за курс"
                ],
                expected_intent="get_payment_options",
                expected_tools=["get_payment_options", "get_course_details"],
                metadata={"difficulty": "medium", "requires_context": False}
            ),
            
            # Schedule and Timing
            SyntheticQuery(
                id="SQ007",
                category="scheduling",
                query="Коли стартує наступний набір?",
                variations=[
                    "Дати набору на курси",
                    "Коли починається навчання?",
                    "Найближчий старт курсів",
                    "Коли можна розпочати навчання?"
                ],
                expected_intent="get_next_enrollment_date",
                expected_tools=["get_enrollment_dates", "get_course_schedule"],
                metadata={"difficulty": "easy", "requires_context": False}
            ),
            SyntheticQuery(
                id="SQ008",
                category="scheduling",
                query="Скільки триває курс Python?",
                variations=[
                    "Яка тривалість курсу Python?",
                    "Як довго триває навчання Python?",
                    "Термін навчання на курсі Python",
                    "За який час можна пройти курс Python?"
                ],
                expected_intent="get_course_duration",
                expected_tools=["get_course_details", "get_course_info"],
                metadata={"difficulty": "medium", "requires_context": False}
            ),
            SyntheticQuery(
                id="SQ009",
                category="scheduling",
                query="Який розклад занять на курсі?",
                variations=[
                    "Коли проходять заняття?",
                    "Графік навчання",
                    "В які дні та години навчання?",
                    "Розклад лекцій"
                ],
                expected_intent="get_class_schedule",
                expected_tools=["get_course_schedule", "get_timetable"],
                metadata={"difficulty": "medium", "requires_context": True}
            ),
            
            # Enrollment
            SyntheticQuery(
                id="SQ010",
                category="enrollment",
                query="Як записатися на курс?",
                variations=[
                    "Процес реєстрації на курс",
                    "Хочу записатися, що робити?",
                    "Як стати студентом?",
                    "Процедура запису на навчання"
                ],
                expected_intent="get_enrollment_process",
                expected_tools=["get_enrollment_info", "enroll_student"],
                metadata={"difficulty": "easy", "requires_context": False}
            ),
            SyntheticQuery(
                id="SQ011",
                category="enrollment",
                query="Хочу записатися на курс React",
                variations=[
                    "Запишіть мене на React",
                    "Реєстрація на курс React",
                    "Беру курс по React",
                    "Хочу навчатися React"
                ],
                expected_intent="enroll_in_specific_course",
                expected_tools=["enroll_student", "create_enrollment"],
                metadata={"difficulty": "medium", "requires_context": False}
            ),
            SyntheticQuery(
                id="SQ012",
                category="enrollment",
                query="Які документи потрібні для запису?",
                variations=[
                    "Що потрібно для реєстрації?",
                    "Які дані надати при записі?",
                    "Документи для навчання",
                    "Вимоги до студентів"
                ],
                expected_intent="get_enrollment_requirements",
                expected_tools=["get_enrollment_requirements", "get_enrollment_info"],
                metadata={"difficulty": "easy", "requires_context": False}
            ),
            
            # Course Details
            SyntheticQuery(
                id="SQ013",
                category="course_details",
                query="Що входить в програму курсу Python?",
                variations=[
                    "Які теми вивчаються на курсі Python?",
                    "Програма навчання Python",
                    "Що я вивчу на курсі Python?",
                    "Силабус курсу Python"
                ],
                expected_intent="get_course_curriculum",
                expected_tools=["get_course_curriculum", "get_course_details"],
                metadata={"difficulty": "medium", "requires_context": False}
            ),
            SyntheticQuery(
                id="SQ014",
                category="course_details",
                query="Чи потрібні попередні знання для курсу?",
                variations=[
                    "Які передумови для навчання?",
                    "Що треба знати перед початком?",
                    "Prerequisites курсу",
                    "Базові вимоги до знань"
                ],
                expected_intent="get_prerequisites",
                expected_tools=["get_course_prerequisites", "get_course_details"],
                metadata={"difficulty": "medium", "requires_context": True}
            ),
            SyntheticQuery(
                id="SQ015",
                category="course_details",
                query="Хто викладає на курсі?",
                variations=[
                    "Інформація про викладачів",
                    "Які менторі на курсі?",
                    "Хто буде вести заняття?",
                    "Досвід викладачів"
                ],
                expected_intent="get_instructor_info",
                expected_tools=["get_instructor_info", "get_course_details"],
                metadata={"difficulty": "medium", "requires_context": True}
            ),
            
            # Certificates and Outcomes
            SyntheticQuery(
                id="SQ016",
                category="certification",
                query="Чи видається сертифікат після курсу?",
                variations=[
                    "Чи отримаю я сертифікат?",
                    "Документ про закінчення курсу",
                    "Сертифікація після навчання",
                    "Підтвердження проходження курсу"
                ],
                expected_intent="get_certification_info",
                expected_tools=["get_certification_info", "get_course_details"],
                metadata={"difficulty": "easy", "requires_context": False}
            ),
            SyntheticQuery(
                id="SQ017",
                category="certification",
                query="Які перспективи після закінчення курсу?",
                variations=[
                    "Куди можна влаштуватися після курсу?",
                    "Допомога з працевлаштуванням",
                    "Що робити після завершення навчання?",
                    "Кар'єрні можливості випускників"
                ],
                expected_intent="get_career_prospects",
                expected_tools=["get_career_info", "get_alumni_outcomes"],
                metadata={"difficulty": "medium", "requires_context": False}
            ),
            
            # Comparison Queries
            SyntheticQuery(
                id="SQ018",
                category="comparison",
                query="Яка різниця між курсами Python та JavaScript?",
                variations=[
                    "Python чи JavaScript - що обрати?",
                    "Порівняння Python та JavaScript курсів",
                    "Що краще вивчати: Python чи JavaScript?",
                    "В чому відмінність між цими курсами?"
                ],
                expected_intent="compare_courses",
                expected_tools=["get_course_details", "compare_courses"],
                metadata={"difficulty": "hard", "requires_context": False}
            ),
            SyntheticQuery(
                id="SQ019",
                category="comparison",
                query="Який курс підходить для початківця?",
                variations=[
                    "З чого краще почати навчання?",
                    "Найлегший курс для новачка",
                    "Рекомендації щодо першого курсу",
                    "Що вивчати спочатку?"
                ],
                expected_intent="get_recommendation_for_beginner",
                expected_tools=["recommend_course", "filter_courses"],
                metadata={"difficulty": "medium", "requires_context": False}
            ),
            
            # Support and Help
            SyntheticQuery(
                id="SQ020",
                category="support",
                query="Як зв'язатися з підтримкою?",
                variations=[
                    "Контакти служби підтримки",
                    "Як поставити питання?",
                    "Номер телефону підтримки",
                    "Email для звернень"
                ],
                expected_intent="get_support_contacts",
                expected_tools=["get_contact_info", "get_support_info"],
                metadata={"difficulty": "easy", "requires_context": False}
            ),
            
            # Conversational
            SyntheticQuery(
                id="SQ021",
                category="conversation",
                query="Дякую за інформацію",
                variations=[
                    "Спасибі",
                    "Дуже дякую",
                    "Вдячний за допомогу",
                    "Дякую, все зрозуміло"
                ],
                expected_intent="gratitude",
                expected_tools=[],
                metadata={"difficulty": "easy", "requires_context": False}
            ),
            SyntheticQuery(
                id="SQ022",
                category="conversation",
                query="Привіт!",
                variations=[
                    "Добрий день",
                    "Вітаю",
                    "Здрастуйте",
                    "Доброго дня"
                ],
                expected_intent="greeting",
                expected_tools=[],
                metadata={"difficulty": "easy", "requires_context": False}
            ),
        ]
    
    def get_all_queries(self, include_variations: bool = False) -> List[str]:
        """Get all queries including variations if specified"""
        queries = []
        for sq in self.synthetic_queries:
            queries.append(sq.query)
            if include_variations:
                queries.extend(sq.variations)
        return queries
    
    def get_queries_by_category(self, category: str) -> List[SyntheticQuery]:
        """Get queries filtered by category"""
        return [sq for sq in self.synthetic_queries if sq.category == category]
    
    def get_queries_by_difficulty(self, difficulty: str) -> List[SyntheticQuery]:
        """Get queries filtered by difficulty"""
        return [sq for sq in self.synthetic_queries if sq.metadata.get("difficulty") == difficulty]
    
    def export_queries(self, filepath: str = "evaluation/data/synthetic_queries.json"):
        """Export queries to JSON file"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        data = {
            "generated_at": datetime.now().isoformat(),
            "total_queries": len(self.synthetic_queries),
            "categories": list(set(sq.category for sq in self.synthetic_queries)),
            "queries": [asdict(sq) for sq in self.synthetic_queries]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Exported {len(self.synthetic_queries)} queries to {filepath}")


class ResponseCollector:
    """Collects agent responses for synthetic queries"""
    
    def __init__(self, endpoint: str, model: str, instructions: str):
        self.endpoint = endpoint
        self.model = model
        self.instructions = instructions
        
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
    
    async def collect_response(self, query: SyntheticQuery, agent: ChatAgent, 
                               thread: Any) -> AgentResponse:
        """Collect agent response for a single query"""
        print(f"\nCollecting response for: {query.query}")
        
        start_time = asyncio.get_event_loop().time()
        response_parts = []
        tools_used = []
        
        try:
            async for chunk in agent.run_stream([query.query], thread=thread):
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
            
            return AgentResponse(
                query_id=query.id,
                query=query.query,
                response=response,
                tools_used=tools_used,
                execution_time=execution_time,
                timestamp=datetime.now().isoformat(),
                metadata={
                    "category": query.category,
                    "expected_intent": query.expected_intent,
                    "expected_tools": query.expected_tools,
                    "query_metadata": query.metadata
                }
            )
            
        except Exception as e:
            print(f"\nError collecting response: {e}")
            execution_time = asyncio.get_event_loop().time() - start_time
            return AgentResponse(
                query_id=query.id,
                query=query.query,
                response=f"ERROR: {str(e)}",
                tools_used=[],
                execution_time=execution_time,
                timestamp=datetime.now().isoformat(),
                metadata={
                    "error": str(e),
                    "category": query.category
                }
            )
    
    async def collect_all_responses(self, queries: List[SyntheticQuery],
                                   max_queries: Optional[int] = None) -> TestDataset:
        """Collect responses for all queries"""
        if max_queries:
            queries = queries[:max_queries]
        
        print(f"\n{'='*70}")
        print(f"Collecting Agent Responses")
        print(f"Total Queries: {len(queries)}")
        print(f"{'='*70}\n")
        
        responses = []
        
        async with (
            DefaultAzureCredential() as credential,
            ChatAgent(
                chat_client=AzureAIAgentClient(
                    project_endpoint=self.endpoint,
                    model_deployment_name=self.model,
                    async_credential=credential,
                    agent_name="data-collection-agent",
                    agent_id=None,
                ),
                instructions=self.instructions,
                max_completion_tokens=4096,
                tools=self._create_mcp_tools(),
            ) as agent
        ):
            thread = agent.get_new_thread()
            
            for i, query in enumerate(queries, 1):
                print(f"\n[{i}/{len(queries)}] ", end="")
                response = await self.collect_response(query, agent, thread)
                responses.append(response)
                await asyncio.sleep(1)  # Brief pause between queries
        
        # Calculate statistics
        total_time = sum(r.execution_time for r in responses)
        avg_time = total_time / len(responses) if responses else 0
        
        category_stats = {}
        for response in responses:
            cat = response.metadata.get("category", "unknown")
            if cat not in category_stats:
                category_stats[cat] = {"count": 0, "total_time": 0}
            category_stats[cat]["count"] += 1
            category_stats[cat]["total_time"] += response.execution_time
        
        for cat in category_stats:
            category_stats[cat]["avg_time"] = (
                category_stats[cat]["total_time"] / category_stats[cat]["count"]
            )
        
        dataset = TestDataset(
            generated_at=datetime.now().isoformat(),
            total_queries=len(queries),
            queries=queries,
            responses=responses,
            statistics={
                "total_execution_time": total_time,
                "average_execution_time": avg_time,
                "category_breakdown": category_stats
            }
        )
        
        return dataset
    
    def save_dataset(self, dataset: TestDataset, filepath: str = None):
        """Save collected dataset to JSON file"""
        if filepath is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"evaluation/data/dataset_{timestamp}.json"
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Convert to dict
        dataset_dict = {
            "generated_at": dataset.generated_at,
            "total_queries": dataset.total_queries,
            "queries": [asdict(q) for q in dataset.queries],
            "responses": [asdict(r) for r in dataset.responses],
            "statistics": dataset.statistics
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(dataset_dict, f, indent=2, ensure_ascii=False)
        
        print(f"\n{'='*70}")
        print(f"Dataset saved to: {filepath}")
        print(f"Total queries: {dataset.total_queries}")
        print(f"Total responses: {len(dataset.responses)}")
        print(f"Average execution time: {dataset.statistics['average_execution_time']:.2f}s")
        print(f"{'='*70}")


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate test data and collect agent responses")
    parser.add_argument("--mode", choices=["generate", "collect", "both"], default="both",
                       help="Mode: generate queries only, collect responses only, or both")
    parser.add_argument("--max-queries", type=int, default=None,
                       help="Maximum number of queries to process")
    parser.add_argument("--category", type=str, default=None,
                       help="Filter by specific category")
    parser.add_argument("--include-variations", action="store_true",
                       help="Include query variations")
    
    args = parser.parse_args()
    
    generator = TestDataGenerator()
    
    if args.mode in ["generate", "both"]:
        print("\n" + "="*70)
        print("Generating Synthetic Test Queries")
        print("="*70)
        generator.export_queries()
        print(f"✓ Generated {len(generator.synthetic_queries)} base queries")
        
        # Show statistics
        categories = {}
        for sq in generator.synthetic_queries:
            categories[sq.category] = categories.get(sq.category, 0) + 1
        
        print("\nCategory breakdown:")
        for cat, count in sorted(categories.items()):
            print(f"  {cat}: {count} queries")
    
    if args.mode in ["collect", "both"]:
        endpoint = os.getenv("ENDPOINT")
        model = os.getenv("MODEL_DEPLOYMENT_NAME")
        instructions = os.getenv("AGENT_INSTRUCTIONS")
        
        if not all([endpoint, model, instructions]):
            print("ERROR: Missing required environment variables")
            return
        
        # Get queries to collect
        if args.category:
            queries = generator.get_queries_by_category(args.category)
            print(f"\nFiltered to category '{args.category}': {len(queries)} queries")
        else:
            queries = generator.synthetic_queries
        
        collector = ResponseCollector(endpoint, model, instructions)
        dataset = await collector.collect_all_responses(queries, args.max_queries)
        collector.save_dataset(dataset)
        
        print("\n✓ Data collection completed successfully!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nOperation interrupted by user")
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
