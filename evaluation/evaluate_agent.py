"""
Agent Evaluation System for CRM Connector

This module provides comprehensive evaluation capabilities for testing
the CRM connector agent's performance on various tasks.
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
class TestCase:
    """Represents a single test case for agent evaluation"""
    id: str
    query: str
    expected_tools: List[str]
    expected_behavior: str
    success_criteria: Dict[str, Any]
    category: str


@dataclass
class EvaluationResult:
    """Results from evaluating a single test case"""
    test_id: str
    query: str
    success: bool
    response: str
    tools_called: List[str]
    execution_time: float
    error: Optional[str]
    score: float
    details: Dict[str, Any]


@dataclass
class EvaluationReport:
    """Complete evaluation report"""
    timestamp: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    average_score: float
    average_execution_time: float
    results: List[EvaluationResult]
    summary: Dict[str, Any]


class AgentEvaluator:
    """Evaluates agent performance on predefined test cases"""
    
    def __init__(self, endpoint: str, model: str, instructions: str):
        self.endpoint = endpoint
        self.model = model
        self.instructions = instructions
        self.test_cases = self._load_test_cases()
        
        # Setup observability
        otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
        setup_observability(otlp_endpoint=otlp_endpoint, enable_sensitive_data="true")
    
    def _load_test_cases(self) -> List[TestCase]:
        """Load predefined test cases"""
        return [
            TestCase(
                id="TC001",
                query="Привіт, чи є зараз курси по Python?",
                expected_tools=["search_courses", "get_available_courses"],
                expected_behavior="Should search for Python courses and return availability",
                success_criteria={
                    "contains_course_info": True,
                    "tool_used": True,
                    "response_length_min": 50
                },
                category="course_search"
            ),
            TestCase(
                id="TC002",
                query="Які курси доступні для початківців?",
                expected_tools=["list_courses", "filter_courses"],
                expected_behavior="Should list beginner-level courses",
                success_criteria={
                    "contains_course_info": True,
                    "mentions_level": True,
                    "tool_used": True
                },
                category="course_search"
            ),
            TestCase(
                id="TC003",
                query="Скільки коштує курс Python?",
                expected_tools=["get_course_price", "get_course_details"],
                expected_behavior="Should provide pricing information for Python course",
                success_criteria={
                    "contains_price": True,
                    "tool_used": True,
                    "response_length_min": 30
                },
                category="pricing"
            ),
            TestCase(
                id="TC004",
                query="Коли починається наступний набір на курси?",
                expected_tools=["get_course_schedule", "get_enrollment_dates"],
                expected_behavior="Should provide enrollment schedule information",
                success_criteria={
                    "contains_date_info": True,
                    "tool_used": True
                },
                category="scheduling"
            ),
            TestCase(
                id="TC005",
                query="Хочу записатися на курс JavaScript",
                expected_tools=["enroll_student", "create_enrollment"],
                expected_behavior="Should initiate enrollment process for JavaScript course",
                success_criteria={
                    "mentions_enrollment": True,
                    "tool_used": True,
                    "asks_for_details": True
                },
                category="enrollment"
            ),
            TestCase(
                id="TC006",
                query="Дякую за інформацію",
                expected_tools=[],
                expected_behavior="Should respond politely without using tools",
                success_criteria={
                    "polite_response": True,
                    "no_tool_used": True,
                    "response_length_min": 10
                },
                category="conversation"
            ),
            TestCase(
                id="TC007",
                query="Які теми охоплює курс Python?",
                expected_tools=["get_course_details", "get_course_curriculum"],
                expected_behavior="Should provide curriculum/syllabus information",
                success_criteria={
                    "contains_curriculum_info": True,
                    "tool_used": True,
                    "response_length_min": 100
                },
                category="course_details"
            ),
            TestCase(
                id="TC008",
                query="Чи потрібні попередні знання для курсу?",
                expected_tools=["get_course_prerequisites", "get_course_details"],
                expected_behavior="Should provide prerequisite information",
                success_criteria={
                    "mentions_prerequisites": True,
                    "tool_used": True
                },
                category="course_details"
            ),
        ]
    
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
    
    def _evaluate_response(self, test_case: TestCase, response: str, 
                          tools_called: List[str], execution_time: float) -> EvaluationResult:
        """Evaluate a single test response against success criteria"""
        score = 0.0
        max_score = len(test_case.success_criteria)
        details = {}
        error = None
        
        try:
            # Check each success criterion
            for criterion, expected_value in test_case.success_criteria.items():
                if criterion == "contains_course_info":
                    if any(word in response.lower() for word in ["курс", "course", "навчання"]):
                        score += 1
                        details[criterion] = "PASS"
                    else:
                        details[criterion] = "FAIL"
                
                elif criterion == "contains_price":
                    if any(word in response.lower() for word in ["грн", "гривень", "коштує", "ціна", "вартість"]):
                        score += 1
                        details[criterion] = "PASS"
                    else:
                        details[criterion] = "FAIL"
                
                elif criterion == "contains_date_info":
                    if any(word in response.lower() for word in ["дата", "дні", "місяць", "час", "розклад"]):
                        score += 1
                        details[criterion] = "PASS"
                    else:
                        details[criterion] = "FAIL"
                
                elif criterion == "tool_used":
                    if len(tools_called) > 0 and expected_value:
                        score += 1
                        details[criterion] = f"PASS (tools: {tools_called})"
                    elif len(tools_called) == 0 and not expected_value:
                        score += 1
                        details[criterion] = "PASS (no tools as expected)"
                    else:
                        details[criterion] = f"FAIL (tools: {tools_called})"
                
                elif criterion == "no_tool_used":
                    if len(tools_called) == 0 and expected_value:
                        score += 1
                        details[criterion] = "PASS"
                    else:
                        details[criterion] = f"FAIL (unexpected tools: {tools_called})"
                
                elif criterion == "response_length_min":
                    if len(response) >= expected_value:
                        score += 1
                        details[criterion] = f"PASS (length: {len(response)})"
                    else:
                        details[criterion] = f"FAIL (length: {len(response)}, required: {expected_value})"
                
                elif criterion == "polite_response":
                    if any(word in response.lower() for word in ["будь ласка", "дякую", "раді", "звертайтесь"]):
                        score += 1
                        details[criterion] = "PASS"
                    else:
                        details[criterion] = "FAIL"
                
                elif criterion == "mentions_enrollment":
                    if any(word in response.lower() for word in ["запис", "реєстрація", "enrollment"]):
                        score += 1
                        details[criterion] = "PASS"
                    else:
                        details[criterion] = "FAIL"
                
                elif criterion == "asks_for_details":
                    if "?" in response or any(word in response.lower() for word in ["потрібно", "необхідно", "вкажіть"]):
                        score += 1
                        details[criterion] = "PASS"
                    else:
                        details[criterion] = "FAIL"
                
                elif criterion == "mentions_level":
                    if any(word in response.lower() for word in ["початкові", "beginner", "рівень"]):
                        score += 1
                        details[criterion] = "PASS"
                    else:
                        details[criterion] = "FAIL"
                
                elif criterion == "contains_curriculum_info":
                    if any(word in response.lower() for word in ["теми", "програма", "модуль", "topics"]):
                        score += 1
                        details[criterion] = "PASS"
                    else:
                        details[criterion] = "FAIL"
                
                elif criterion == "mentions_prerequisites":
                    if any(word in response.lower() for word in ["потрібні", "необхідні", "знання", "prerequisites"]):
                        score += 1
                        details[criterion] = "PASS"
                    else:
                        details[criterion] = "FAIL"
            
            normalized_score = score / max_score if max_score > 0 else 0.0
            success = normalized_score >= 0.7  # 70% threshold for success
            
        except Exception as e:
            error = str(e)
            success = False
            normalized_score = 0.0
        
        return EvaluationResult(
            test_id=test_case.id,
            query=test_case.query,
            success=success,
            response=response,
            tools_called=tools_called,
            execution_time=execution_time,
            error=error,
            score=normalized_score,
            details=details
        )
    
    async def run_single_test(self, test_case: TestCase, agent: ChatAgent, 
                             thread: Any) -> EvaluationResult:
        """Run a single test case"""
        print(f"\n{'='*70}")
        print(f"Running Test: {test_case.id} - {test_case.category}")
        print(f"Query: {test_case.query}")
        print(f"{'='*70}")
        
        start_time = asyncio.get_event_loop().time()
        response_parts = []
        tools_called = []
        
        try:
            async for chunk in agent.run_stream([test_case.query], thread=thread):
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
                                tools_called.append(tool_call.function.name)
            
            print()  # New line after response
            
            execution_time = asyncio.get_event_loop().time() - start_time
            response = "".join(response_parts)
            
            result = self._evaluate_response(test_case, response, tools_called, execution_time)
            
            # Print evaluation summary
            print(f"\n{'─'*70}")
            print(f"Result: {'✓ PASS' if result.success else '✗ FAIL'} (Score: {result.score:.2%})")
            print(f"Tools Called: {tools_called if tools_called else 'None'}")
            print(f"Execution Time: {execution_time:.2f}s")
            print(f"Details: {json.dumps(result.details, indent=2)}")
            
            return result
            
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            print(f"\n✗ ERROR: {str(e)}")
            return EvaluationResult(
                test_id=test_case.id,
                query=test_case.query,
                success=False,
                response="",
                tools_called=[],
                execution_time=execution_time,
                error=str(e),
                score=0.0,
                details={"error": str(e)}
            )
    
    async def run_all_tests(self) -> EvaluationReport:
        """Run all test cases and generate report"""
        print(f"\n{'='*70}")
        print(f"Starting Agent Evaluation")
        print(f"Total Test Cases: {len(self.test_cases)}")
        print(f"{'='*70}\n")
        
        results = []
        
        async with (
            DefaultAzureCredential() as credential,
            ChatAgent(
                chat_client=AzureAIAgentClient(
                    project_endpoint=self.endpoint,
                    model_deployment_name=self.model,
                    async_credential=credential,
                    agent_name="evaluation-agent",
                    agent_id=None,
                ),
                instructions=self.instructions,
                max_completion_tokens=4096,
                tools=self._create_mcp_tools(),
            ) as agent
        ):
            thread = agent.get_new_thread()
            
            for test_case in self.test_cases:
                result = await self.run_single_test(test_case, agent, thread)
                results.append(result)
                await asyncio.sleep(1)  # Brief pause between tests
        
        # Generate report
        timestamp = datetime.now().isoformat()
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r.success)
        failed_tests = total_tests - passed_tests
        average_score = sum(r.score for r in results) / total_tests if total_tests > 0 else 0.0
        average_execution_time = sum(r.execution_time for r in results) / total_tests if total_tests > 0 else 0.0
        
        # Category breakdown
        category_stats = {}
        for result in results:
            test_case = next(tc for tc in self.test_cases if tc.id == result.test_id)
            category = test_case.category
            if category not in category_stats:
                category_stats[category] = {"total": 0, "passed": 0, "scores": []}
            category_stats[category]["total"] += 1
            if result.success:
                category_stats[category]["passed"] += 1
            category_stats[category]["scores"].append(result.score)
        
        summary = {
            "pass_rate": f"{(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "0%",
            "category_breakdown": {
                cat: {
                    "pass_rate": f"{(stats['passed']/stats['total']*100):.1f}%",
                    "avg_score": f"{(sum(stats['scores'])/len(stats['scores'])*100):.1f}%"
                }
                for cat, stats in category_stats.items()
            }
        }
        
        report = EvaluationReport(
            timestamp=timestamp,
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            average_score=average_score,
            average_execution_time=average_execution_time,
            results=results,
            summary=summary
        )
        
        return report
    
    def save_report(self, report: EvaluationReport, filepath: str = None):
        """Save evaluation report to JSON file"""
        if filepath is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"evaluation/reports/evaluation_report_{timestamp}.json"
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        report_dict = asdict(report)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)
        
        print(f"\n{'='*70}")
        print(f"Report saved to: {filepath}")
        print(f"{'='*70}")
    
    def print_summary(self, report: EvaluationReport):
        """Print evaluation summary"""
        print(f"\n{'='*70}")
        print(f"EVALUATION SUMMARY")
        print(f"{'='*70}")
        print(f"Timestamp: {report.timestamp}")
        print(f"Total Tests: {report.total_tests}")
        print(f"Passed: {report.passed_tests} | Failed: {report.failed_tests}")
        print(f"Pass Rate: {report.summary['pass_rate']}")
        print(f"Average Score: {report.average_score:.2%}")
        print(f"Average Execution Time: {report.average_execution_time:.2f}s")
        print(f"\nCategory Breakdown:")
        for category, stats in report.summary['category_breakdown'].items():
            print(f"  {category}: Pass Rate: {stats['pass_rate']}, Avg Score: {stats['avg_score']}")
        print(f"{'='*70}\n")


async def main():
    """Main evaluation entry point"""
    endpoint = os.getenv("ENDPOINT")
    model = os.getenv("MODEL_DEPLOYMENT_NAME")
    instructions = os.getenv("AGENT_INSTRUCTIONS")
    
    if not all([endpoint, model, instructions]):
        print("ERROR: Missing required environment variables (ENDPOINT, MODEL_DEPLOYMENT_NAME, AGENT_INSTRUCTIONS)")
        return
    
    evaluator = AgentEvaluator(endpoint, model, instructions)
    
    # Run all tests
    report = await evaluator.run_all_tests()
    
    # Print summary
    evaluator.print_summary(report)
    
    # Save report
    evaluator.save_report(report)
    
    print("Evaluation completed successfully!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nEvaluation interrupted by user")
    except Exception as e:
        print(f"An error occurred during evaluation: {e}")
        import traceback
        traceback.print_exc()
