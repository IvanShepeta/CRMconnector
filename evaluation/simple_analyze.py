"""Simplified Agent Analysis - shows key metrics and top recommendations"""

import json
import glob
import os
from collections import Counter
from typing import Dict, List, Any
from common import load_json, print_header


class SimpleAnalyzer:
    """Analyzes test results and provides simple recommendations"""
    
    def __init__(self, dataset_path: str = None):
        self.dataset = None
        if dataset_path:
            self.dataset = load_json(dataset_path)
        else:
            self.dataset = self._load_latest()
    
    def _load_latest(self) -> Dict:
        """Load latest test results"""
        patterns = [
            "evaluation/data/quick_test_*.json",
            "evaluation/data/dataset_*.json"
        ]
        
        files = []
        for pattern in patterns:
            files.extend(glob.glob(pattern))
        
        if not files:
            raise FileNotFoundError("No test results found. Run quick_test.py first")
        
        latest = max(files, key=os.path.getctime)
        print(f"Loading: {latest}\n")
        return load_json(latest)
    
    def analyze(self):
        """Run analysis and print results"""
        responses = self.dataset.get('results', self.dataset.get('responses', []))
        
        if not responses:
            print("No responses found in dataset")
            return
        
        print_header("AGENT ANALYSIS")
        
        # Basic stats
        total = len(responses)
        with_tools = sum(1 for r in responses if r.get('tools_used', []))
        avg_time = sum(r.get('execution_time', 0) for r in responses) / total
        avg_length = sum(len(r.get('response', '')) for r in responses) / total
        
        print(f"Total queries: {total}")
        print(f"Tool usage: {with_tools}/{total} ({with_tools/total*100:.0f}%)")
        print(f"Avg response time: {avg_time:.2f}s")
        print(f"Avg response length: {avg_length:.0f} chars")
        
        # Find issues
        errors = [r for r in responses if 'ERROR' in r.get('response', '')]
        short = [r for r in responses if len(r.get('response', '')) < 50]
        slow = [r for r in responses if r.get('execution_time', 0) > 5.0]
        
        print(f"\nIssues found:")
        print(f"  Errors: {len(errors)}")
        print(f"  Short responses: {len(short)}")
        print(f"  Slow queries (>5s): {len(slow)}")
        
        # Top tools
        all_tools = []
        for r in responses:
            all_tools.extend(r.get('tools_used', []))
        
        if all_tools:
            print(f"\nTop tools used:")
            for tool, count in Counter(all_tools).most_common(3):
                print(f"  • {tool}: {count}x")
        
        # Recommendations
        self._print_recommendations(with_tools/total, len(errors), len(short), avg_time)
    
    def _print_recommendations(self, tool_rate: float, errors: int, short: int, avg_time: float):
        """Print top 3 recommendations"""
        print_header("TOP RECOMMENDATIONS")
        
        recs = []
        
        # Check tool usage
        if tool_rate < 0.5:
            recs.append((
                "HIGH",
                "Low tool usage",
                f"Only {tool_rate*100:.0f}% of queries use tools. Add to AGENT_INSTRUCTIONS:\n"
                "  'For course queries ALWAYS use available tools: list_courses, search_courses, get_course_details'"
            ))
        
        # Check errors
        if errors > 0:
            recs.append((
                "HIGH",
                f"{errors} queries failed",
                "Check MCP server is running: curl http://localhost:3001/mcp\n"
                "Add error handling to agent instructions"
            ))
        
        # Check response quality
        if short > 2:
            recs.append((
                "MEDIUM",
                f"{short} responses too short",
                "Add to AGENT_INSTRUCTIONS:\n"
                "  'Always provide detailed answers: minimum 2-3 sentences with specific data'"
            ))
        
        # Check performance
        if avg_time > 4.0:
            recs.append((
                "MEDIUM",
                f"Slow responses (avg {avg_time:.1f}s)",
                "In AgentCode.py reduce max_completion_tokens:\n"
                "  max_completion_tokens=2048  # instead of 4096"
            ))
        
        # Print top 3
        for i, (priority, issue, fix) in enumerate(recs[:3], 1):
            emoji = {'HIGH': '🔴', 'MEDIUM': '🟡', 'LOW': '🟢'}[priority]
            print(f"{emoji} #{i} [{priority}] {issue}")
            print(f"\nFix:\n{fix}\n")
            print("-" * 70)
        
        if not recs:
            print("✅ Everything looks good! No major issues found.\n")
    
    def save_report(self, filepath: str = None):
        """Save simple report"""
        if not filepath:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"evaluation/reports/simple_report_{timestamp}.json"
        
        responses = self.dataset.get('results', self.dataset.get('responses', []))
        total = len(responses)
        
        report = {
            "timestamp": self.dataset.get('timestamp', ''),
            "total_queries": total,
            "tool_usage_rate": sum(1 for r in responses if r.get('tools_used', [])) / total if total else 0,
            "avg_time": sum(r.get('execution_time', 0) for r in responses) / total if total else 0,
            "issues": {
                "errors": len([r for r in responses if 'ERROR' in r.get('response', '')]),
                "short": len([r for r in responses if len(r.get('response', '')) < 50]),
                "slow": len([r for r in responses if r.get('execution_time', 0) > 5.0])
            }
        }
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Report saved: {filepath}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Simple agent analysis")
    parser.add_argument('--dataset', type=str, help='Path to dataset')
    parser.add_argument('--save', action='store_true', help='Save report')
    
    args = parser.parse_args()
    
    try:
        analyzer = SimpleAnalyzer(args.dataset)
        analyzer.analyze()
        
        if args.save:
            analyzer.save_report()
        
        print("\n" + "="*70)
        print("NEXT STEPS:")
        print("1. Fix high priority issues")
        print("2. Update AGENT_INSTRUCTIONS in .env")
        print("3. Run quick_test.py again")
        print("4. Compare results")
        print("="*70)
        
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("\nRun this first: python evaluation/quick_test.py")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
