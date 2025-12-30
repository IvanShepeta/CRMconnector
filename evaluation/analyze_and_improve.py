"""
Agent Analysis and Improvement System

Analyzes test results and provides actionable recommendations for improving your agent.
"""

import json
import os
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from collections import Counter
import glob


@dataclass
class ImprovementRecommendation:
    """Single improvement recommendation"""
    priority: str  # HIGH, MEDIUM, LOW
    category: str
    issue: str
    recommendation: str
    example: str
    expected_impact: str


class AgentAnalyzer:
    """Analyzes agent performance and suggests improvements"""
    
    def __init__(self, dataset_path: str = None):
        """Initialize analyzer with dataset path"""
        self.dataset_path = dataset_path
        self.dataset = None
        self.recommendations: List[ImprovementRecommendation] = []
        
        if dataset_path:
            self.load_dataset(dataset_path)
    
    def load_dataset(self, path: str):
        """Load dataset from JSON file"""
        with open(path, 'r', encoding='utf-8') as f:
            self.dataset = json.load(f)
        print(f"✓ Loaded dataset: {path}")
        print(f"  Total queries: {len(self.dataset.get('responses', []))}")
    
    def load_latest_dataset(self, data_dir: str = "evaluation/data"):
        """Load the most recent dataset"""
        pattern = os.path.join(data_dir, "quick_test_*.json")
        files = glob.glob(pattern)
        
        if not files:
            pattern = os.path.join(data_dir, "dataset_*.json")
            files = glob.glob(pattern)
        
        if not files:
            raise FileNotFoundError(f"No dataset files found in {data_dir}")
        
        latest_file = max(files, key=os.path.getctime)
        self.load_dataset(latest_file)
        return latest_file
    
    def analyze_tool_usage(self) -> Dict[str, Any]:
        """Analyze which tools are being used and how often"""
        if not self.dataset:
            return {}
        
        responses = self.dataset.get('responses', [])
        
        tool_usage = Counter()
        queries_with_tools = 0
        queries_without_tools = 0
        missing_expected_tools = []
        
        for response in responses:
            tools_used = response.get('tools_used', [])
            
            if tools_used:
                queries_with_tools += 1
                for tool in tools_used:
                    tool_usage[tool] += 1
            else:
                queries_without_tools += 1
            
            # Check if expected tools were used
            metadata = response.get('metadata', {})
            expected_tools = metadata.get('expected_tools', [])
            
            if expected_tools and not any(exp in str(tools_used) for exp in expected_tools):
                missing_expected_tools.append({
                    'query': response.get('query', ''),
                    'expected': expected_tools,
                    'actual': tools_used
                })
        
        return {
            'tool_usage_count': dict(tool_usage),
            'queries_with_tools': queries_with_tools,
            'queries_without_tools': queries_without_tools,
            'tool_usage_rate': queries_with_tools / len(responses) if responses else 0,
            'missing_expected_tools': missing_expected_tools
        }
    
    def analyze_response_quality(self) -> Dict[str, Any]:
        """Analyze response quality metrics"""
        if not self.dataset:
            return {}
        
        responses = self.dataset.get('responses', [])
        
        response_lengths = [len(r.get('response', '')) for r in responses]
        short_responses = [r for r in responses if len(r.get('response', '')) < 50]
        empty_responses = [r for r in responses if not r.get('response', '').strip()]
        error_responses = [r for r in responses if 'ERROR' in r.get('response', '')]
        
        return {
            'avg_response_length': sum(response_lengths) / len(response_lengths) if response_lengths else 0,
            'min_response_length': min(response_lengths) if response_lengths else 0,
            'max_response_length': max(response_lengths) if response_lengths else 0,
            'short_responses_count': len(short_responses),
            'short_responses': short_responses[:3],  # Show first 3
            'empty_responses_count': len(empty_responses),
            'error_responses_count': len(error_responses),
            'error_responses': error_responses
        }
    
    def analyze_execution_time(self) -> Dict[str, Any]:
        """Analyze execution time patterns"""
        if not self.dataset:
            return {}
        
        responses = self.dataset.get('responses', [])
        
        execution_times = [r.get('execution_time', 0) for r in responses]
        slow_queries = [r for r in responses if r.get('execution_time', 0) > 5.0]
        
        # Group by category
        category_times = {}
        for response in responses:
            category = response.get('category', 'unknown')
            if category not in category_times:
                category_times[category] = []
            category_times[category].append(response.get('execution_time', 0))
        
        category_avg = {
            cat: sum(times) / len(times) if times else 0
            for cat, times in category_times.items()
        }
        
        return {
            'avg_execution_time': sum(execution_times) / len(execution_times) if execution_times else 0,
            'min_execution_time': min(execution_times) if execution_times else 0,
            'max_execution_time': max(execution_times) if execution_times else 0,
            'slow_queries_count': len(slow_queries),
            'slow_queries': slow_queries,
            'category_avg_times': category_avg
        }
    
    def analyze_by_category(self) -> Dict[str, Any]:
        """Analyze performance by category"""
        if not self.dataset:
            return {}
        
        responses = self.dataset.get('responses', [])
        
        categories = {}
        for response in responses:
            category = response.get('category', 'unknown')
            if category not in categories:
                categories[category] = {
                    'count': 0,
                    'with_tools': 0,
                    'avg_length': 0,
                    'avg_time': 0,
                    'responses': []
                }
            
            categories[category]['count'] += 1
            categories[category]['responses'].append(response)
            
            if response.get('tools_used', []):
                categories[category]['with_tools'] += 1
        
        # Calculate averages
        for cat, data in categories.items():
            responses_list = data['responses']
            data['avg_length'] = sum(len(r.get('response', '')) for r in responses_list) / len(responses_list)
            data['avg_time'] = sum(r.get('execution_time', 0) for r in responses_list) / len(responses_list)
            data['tool_usage_rate'] = data['with_tools'] / data['count'] if data['count'] > 0 else 0
            del data['responses']  # Remove to keep output clean
        
        return categories
    
    def generate_recommendations(self):
        """Generate improvement recommendations based on analysis"""
        if not self.dataset:
            print("No dataset loaded. Please load a dataset first.")
            return
        
        self.recommendations = []
        
        # Analyze different aspects
        tool_analysis = self.analyze_tool_usage()
        quality_analysis = self.analyze_response_quality()
        time_analysis = self.analyze_execution_time()
        category_analysis = self.analyze_by_category()
        
        # 1. Tool Usage Issues
        if tool_analysis['tool_usage_rate'] < 0.5:
            self.recommendations.append(ImprovementRecommendation(
                priority="HIGH",
                category="Tool Usage",
                issue=f"Low tool usage rate: {tool_analysis['tool_usage_rate']:.1%}",
                recommendation="Improve agent instructions to encourage tool usage. Add examples of when to use each tool.",
                example="""AGENT_INSTRUCTIONS=\
"Ти - асистент CRM системи курсів. 
ДЛЯ ВІДПОВІДІ НА ЗАПИТИ ПРО КУРСИ ЗАВЖДИ використовуй доступні інструменти:
- list_courses: для показу всіх курсів
- search_courses: для пошуку конкретного курсу
- get_course_details: для деталей курсу

Приклад: Якщо користувач питає 'Які курси є?', використай list_courses.\"""",
                expected_impact="Збільшення точності відповідей на 40-60%"
            ))
        
        # 2. Missing Expected Tools
        if tool_analysis['missing_expected_tools']:
            examples = tool_analysis['missing_expected_tools'][:2]
            self.recommendations.append(ImprovementRecommendation(
                priority="HIGH",
                category="Tool Selection",
                issue=f"{len(tool_analysis['missing_expected_tools'])} queries didn't use expected tools",
                recommendation="Review tool descriptions and improve agent's understanding of when to use each tool.",
                example=f"Problem queries:\n" + "\n".join(
                    f"- '{ex['query']}' (expected: {ex['expected']}, got: {ex['actual']})"
                    for ex in examples
                ),
                expected_impact="Підвищення релевантності відповідей на 30-50%"
            ))
        
        # 3. Short Responses
        if quality_analysis['short_responses_count'] > 2:
            self.recommendations.append(ImprovementRecommendation(
                priority="MEDIUM",
                category="Response Quality",
                issue=f"{quality_analysis['short_responses_count']} responses are too short (< 50 chars)",
                recommendation="Add instruction to provide detailed, helpful responses. Encourage elaboration.",
                example="""Add to instructions:
"Завжди надавай детальні відповіді:
- Мінімум 2-3 речення
- Конкретні дані (ціни, дати, список)
- Додаткова корисна інформація
- Питання для уточнення якщо потрібно\"""",
                expected_impact="Покращення задоволеності користувачів на 25%"
            ))
        
        # 4. Errors
        if quality_analysis['error_responses_count'] > 0:
            self.recommendations.append(ImprovementRecommendation(
                priority="HIGH",
                category="Error Handling",
                issue=f"{quality_analysis['error_responses_count']} queries resulted in errors",
                recommendation="Add error handling and fallback responses. Ensure MCP server is running correctly.",
                example="""1. Check MCP server status: curl http://localhost:3001/mcp
2. Add error handling in agent instructions:
   'Якщо інструмент недоступний, вибачся та запропонуй альтернативу.'
3. Verify tool configurations in AgentCode.py""",
                expected_impact="Зменшення помилок на 80-100%"
            ))
        
        # 5. Slow Performance
        if time_analysis['avg_execution_time'] > 4.0:
            self.recommendations.append(ImprovementRecommendation(
                priority="MEDIUM",
                category="Performance",
                issue=f"High average execution time: {time_analysis['avg_execution_time']:.2f}s",
                recommendation="Optimize tool implementations, add caching, or reduce token limits.",
                example="""1. In AgentCode.py, reduce max_completion_tokens:
   max_completion_tokens=2048  # instead of 4096

2. Add caching to frequently used queries

3. Optimize MCP server response time""",
                expected_impact="Зменшення часу відповіді на 30-40%"
            ))
        
        # 6. Category-Specific Issues
        for category, stats in category_analysis.items():
            if stats['tool_usage_rate'] < 0.3 and category != 'conversation':
                self.recommendations.append(ImprovementRecommendation(
                    priority="MEDIUM",
                    category=f"Category: {category}",
                    issue=f"Low tool usage in {category}: {stats['tool_usage_rate']:.1%}",
                    recommendation=f"Add specific examples for {category} queries in agent instructions.",
                    example=f"""Add to AGENT_INSTRUCTIONS:
"Для запитів категорії '{category}':
- Завжди використовуй відповідні інструменти
- Приклади запитів: [додай конкретні приклади]
- Очікувана поведінка: [опиши що має робити агент]\"""",
                    expected_impact=f"Покращення для {category} на 40%"
                ))
        
        # 7. Conversational Skills
        conversation_responses = [r for r in self.dataset.get('responses', []) 
                                 if r.get('category') == 'conversation']
        if conversation_responses:
            avg_conv_length = sum(len(r.get('response', '')) for r in conversation_responses) / len(conversation_responses)
            if avg_conv_length < 30:
                self.recommendations.append(ImprovementRecommendation(
                    priority="LOW",
                    category="Conversational Skills",
                    issue="Conversational responses are too brief",
                    recommendation="Train agent to be more friendly and engaging in conversations.",
                    example="""Add personality to agent:
"Будь дружнім та корисним. Приклади:
- 'Дякую' -> 'Будь ласка! Радий був допомогти. Якщо виникнуть ще питання - звертайся!'
- 'Привіт' -> 'Привіт! Я асистент CRM курсів. Чим можу допомогти?'\"""",
                    expected_impact="Покращення враження користувачів на 20%"
                ))
        
        # Sort by priority
        priority_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
        self.recommendations.sort(key=lambda x: priority_order[x.priority])
    
    def print_analysis(self):
        """Print complete analysis report"""
        if not self.dataset:
            print("No dataset loaded.")
            return
        
        print(f"\n{'='*80}")
        print(f"AGENT PERFORMANCE ANALYSIS")
        print(f"{'='*80}\n")
        
        # Tool Usage
        print("📊 TOOL USAGE ANALYSIS")
        print("─" * 80)
        tool_analysis = self.analyze_tool_usage()
        print(f"Tool Usage Rate: {tool_analysis['tool_usage_rate']:.1%}")
        print(f"Queries with tools: {tool_analysis['queries_with_tools']}")
        print(f"Queries without tools: {tool_analysis['queries_without_tools']}")
        
        if tool_analysis['tool_usage_count']:
            print("\nMost Used Tools:")
            for tool, count in sorted(tool_analysis['tool_usage_count'].items(), 
                                     key=lambda x: x[1], reverse=True)[:5]:
                print(f"  • {tool}: {count} times")
        
        if tool_analysis['missing_expected_tools']:
            print(f"\n⚠️  {len(tool_analysis['missing_expected_tools'])} queries missed expected tools")
        
        # Response Quality
        print(f"\n\n📝 RESPONSE QUALITY ANALYSIS")
        print("─" * 80)
        quality_analysis = self.analyze_response_quality()
        print(f"Average response length: {quality_analysis['avg_response_length']:.0f} chars")
        print(f"Short responses (< 50 chars): {quality_analysis['short_responses_count']}")
        print(f"Empty responses: {quality_analysis['empty_responses_count']}")
        print(f"Error responses: {quality_analysis['error_responses_count']}")
        
        # Execution Time
        print(f"\n\n⏱️  EXECUTION TIME ANALYSIS")
        print("─" * 80)
        time_analysis = self.analyze_execution_time()
        print(f"Average execution time: {time_analysis['avg_execution_time']:.2f}s")
        print(f"Fastest query: {time_analysis['min_execution_time']:.2f}s")
        print(f"Slowest query: {time_analysis['max_execution_time']:.2f}s")
        print(f"Slow queries (> 5s): {time_analysis['slow_queries_count']}")
        
        if time_analysis['category_avg_times']:
            print("\nAverage time by category:")
            for cat, avg_time in sorted(time_analysis['category_avg_times'].items(), 
                                       key=lambda x: x[1], reverse=True):
                print(f"  • {cat}: {avg_time:.2f}s")
        
        # Category Breakdown
        print(f"\n\n📁 CATEGORY BREAKDOWN")
        print("─" * 80)
        category_analysis = self.analyze_by_category()
        for category, stats in sorted(category_analysis.items()):
            print(f"\n{category.upper()}:")
            print(f"  Queries: {stats['count']}")
            print(f"  Tool usage: {stats['tool_usage_rate']:.1%}")
            print(f"  Avg response length: {stats['avg_length']:.0f} chars")
            print(f"  Avg execution time: {stats['avg_time']:.2f}s")
    
    def print_recommendations(self):
        """Print improvement recommendations"""
        if not self.recommendations:
            print("\nNo recommendations generated. Run generate_recommendations() first.")
            return
        
        print(f"\n\n{'='*80}")
        print(f"IMPROVEMENT RECOMMENDATIONS ({len(self.recommendations)} total)")
        print(f"{'='*80}\n")
        
        for i, rec in enumerate(self.recommendations, 1):
            priority_emoji = {'HIGH': '🔴', 'MEDIUM': '🟡', 'LOW': '🟢'}[rec.priority]
            
            print(f"{priority_emoji} RECOMMENDATION #{i} [{rec.priority} PRIORITY]")
            print("─" * 80)
            print(f"Category: {rec.category}")
            print(f"\nIssue:")
            print(f"  {rec.issue}")
            print(f"\nRecommendation:")
            print(f"  {rec.recommendation}")
            print(f"\nExample/Solution:")
            for line in rec.example.split('\n'):
                print(f"  {line}")
            print(f"\nExpected Impact:")
            print(f"  {rec.expected_impact}")
            print()
    
    def save_report(self, filepath: str = None):
        """Save analysis report to file"""
        if filepath is None:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"evaluation/reports/analysis_report_{timestamp}.json"
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        report = {
            'dataset_path': self.dataset_path,
            'analysis': {
                'tool_usage': self.analyze_tool_usage(),
                'response_quality': self.analyze_response_quality(),
                'execution_time': self.analyze_execution_time(),
                'category_breakdown': self.analyze_by_category()
            },
            'recommendations': [
                {
                    'priority': rec.priority,
                    'category': rec.category,
                    'issue': rec.issue,
                    'recommendation': rec.recommendation,
                    'example': rec.example,
                    'expected_impact': rec.expected_impact
                }
                for rec in self.recommendations
            ]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Analysis report saved to: {filepath}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze agent performance and get improvement recommendations")
    parser.add_argument('--dataset', type=str, default=None,
                       help='Path to dataset JSON file')
    parser.add_argument('--latest', action='store_true',
                       help='Use the latest dataset from evaluation/data')
    
    args = parser.parse_args()
    
    analyzer = AgentAnalyzer()
    
    try:
        if args.dataset:
            analyzer.load_dataset(args.dataset)
        elif args.latest:
            latest = analyzer.load_latest_dataset()
            print(f"Using latest dataset: {latest}\n")
        else:
            latest = analyzer.load_latest_dataset()
            print(f"Using latest dataset: {latest}\n")
    except Exception as e:
        print(f"Error loading dataset: {e}")
        print("\nPlease run quick_test.py first to generate data:")
        print("  python evaluation/quick_test.py")
        return
    
    # Perform analysis
    analyzer.print_analysis()
    
    # Generate and print recommendations
    analyzer.generate_recommendations()
    analyzer.print_recommendations()
    
    # Save report
    analyzer.save_report()
    
    print("\n" + "="*80)
    print("NEXT STEPS:")
    print("="*80)
    print("1. Review the recommendations above")
    print("2. Implement high-priority improvements first")
    print("3. Update AGENT_INSTRUCTIONS in your .env file")
    print("4. Re-run quick_test.py to measure improvements")
    print("5. Compare results using the saved reports")
    print("\n✓ Analysis complete!")


if __name__ == "__main__":
    main()
