# Agent Evaluation System

Comprehensive evaluation framework for testing the CRM Connector agent's performance.

## Overview

This evaluation system provides automated testing capabilities to measure your agent's performance across different categories of tasks including course search, pricing inquiries, enrollment, and general conversation handling.

## Features

- **Automated Test Cases**: 8 predefined test cases covering various scenarios
- **Multi-criteria Evaluation**: Each test evaluates multiple success criteria
- **Detailed Reporting**: JSON reports with scores, execution times, and detailed feedback
- **Category Analysis**: Performance breakdown by task category
- **Tool Usage Tracking**: Monitors which tools the agent uses for each query

## Test Categories

1. **Course Search** - Finding and listing available courses
2. **Pricing** - Retrieving course pricing information
3. **Scheduling** - Getting enrollment dates and schedules
4. **Enrollment** - Handling student registration requests
5. **Course Details** - Providing curriculum and prerequisite information
6. **Conversation** - General conversational responses

## Installation

No additional dependencies are required beyond those already in your `pyproject.toml`.

## Usage

### Running Evaluation

```bash
python evaluation/evaluate_agent.py
```

### Environment Variables

Ensure these variables are set in your `.env` file:

```env
ENDPOINT=your_azure_endpoint
MODEL_DEPLOYMENT_NAME=your_model_name
AGENT_INSTRUCTIONS=your_agent_instructions
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

### Prerequisites

1. Your CRM connector MCP server must be running at `http://localhost:3001/mcp`
2. Azure credentials must be configured
3. OTLP trace collector should be running (optional but recommended)

## Test Cases

### TC001: Python Course Availability
**Query**: "Привіт, чи є зараз курси по Python?"
- Tests: Course search functionality
- Expected: Should return Python course availability
- Tools: search_courses, get_available_courses

### TC002: Beginner Courses
**Query**: "Які курси доступні для початківців?"
- Tests: Course filtering by level
- Expected: List beginner-level courses
- Tools: list_courses, filter_courses

### TC003: Course Pricing
**Query**: "Скільки коштує курс Python?"
- Tests: Price retrieval
- Expected: Return pricing information
- Tools: get_course_price, get_course_details

### TC004: Enrollment Schedule
**Query**: "Коли починається наступний набір?"
- Tests: Schedule information
- Expected: Provide enrollment dates
- Tools: get_course_schedule, get_enrollment_dates

### TC005: Course Enrollment
**Query**: "Хочу записатися на курс JavaScript"
- Tests: Enrollment process initiation
- Expected: Start enrollment and ask for details
- Tools: enroll_student, create_enrollment

### TC006: Polite Response
**Query**: "Дякую за інформацію"
- Tests: Conversational capability without tools
- Expected: Polite response without tool usage
- Tools: None

### TC007: Course Curriculum
**Query**: "Які теми охоплює курс Python?"
- Tests: Curriculum information retrieval
- Expected: Detailed course topics
- Tools: get_course_details, get_course_curriculum

### TC008: Course Prerequisites
**Query**: "Чи потрібні попередні знання?"
- Tests: Prerequisites information
- Expected: List required knowledge
- Tools: get_course_prerequisites, get_course_details

## Evaluation Criteria

Each test case is evaluated against multiple criteria:

- **Tool Usage**: Correct tools are called
- **Response Content**: Contains expected information
- **Response Length**: Meets minimum length requirements
- **Behavioral Checks**: Follows expected patterns (e.g., asks for details, polite responses)

**Success Threshold**: 70% of criteria must pass for a test to be marked as successful.

## Report Format

Reports are saved in `evaluation/reports/` with the following structure:

```json
{
  "timestamp": "2025-12-30T12:00:00",
  "total_tests": 8,
  "passed_tests": 7,
  "failed_tests": 1,
  "average_score": 0.85,
  "average_execution_time": 3.2,
  "summary": {
    "pass_rate": "87.5%",
    "category_breakdown": {
      "course_search": {
        "pass_rate": "100%",
        "avg_score": "95%"
      }
    }
  },
  "results": [...]
}
```

## Customization

### Adding New Test Cases

Edit `evaluate_agent.py` and add test cases to the `_load_test_cases()` method:

```python
TestCase(
    id="TC009",
    query="Your test query",
    expected_tools=["tool_name"],
    expected_behavior="Description of expected behavior",
    success_criteria={
        "your_criterion": True,
        "response_length_min": 50
    },
    category="your_category"
)
```

### Adding New Success Criteria

Implement new criteria in the `_evaluate_response()` method:

```python
elif criterion == "your_new_criterion":
    if your_condition:
        score += 1
        details[criterion] = "PASS"
    else:
        details[criterion] = "FAIL"
```

## Interpreting Results

### Score Interpretation

- **90-100%**: Excellent performance
- **70-89%**: Good performance
- **50-69%**: Needs improvement
- **Below 50%**: Poor performance, requires attention

### Common Issues

1. **Low Tool Usage**: Agent not calling appropriate tools
   - Check agent instructions
   - Verify MCP server is running
   - Review tool descriptions

2. **Missing Information**: Responses lack expected content
   - Improve agent instructions
   - Verify MCP server data
   - Check tool implementations

3. **Execution Timeouts**: Tests taking too long
   - Optimize tool implementations
   - Check network connectivity
   - Review token limits

## Continuous Evaluation

For continuous testing during development:

```bash
# Run evaluation after code changes
python evaluation/evaluate_agent.py

# Compare reports
diff evaluation/reports/evaluation_report_*.json
```

## Best Practices

1. **Baseline Establishment**: Run initial evaluation to establish baseline performance
2. **Regular Testing**: Evaluate after significant changes to agent or tools
3. **Trend Analysis**: Track scores over time to identify improvements or regressions
4. **Category Focus**: Use category breakdown to identify specific areas needing improvement
5. **Tool Monitoring**: Ensure correct tools are being called for each task type

## Troubleshooting

### MCP Server Connection Issues

```bash
# Verify server is running
curl http://localhost:3001/mcp

# Check logs
tail -f logs/mcp_server.log
```

### Azure Authentication Issues

```bash
# Test Azure credentials
az account show

# Re-authenticate if needed
az login
```

### Missing Environment Variables

```bash
# Verify .env file
cat .env

# Check loaded variables
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('ENDPOINT'))"
```

## Future Enhancements

- [ ] Add performance benchmarking
- [ ] Implement A/B testing for different agent configurations
- [ ] Add multi-language test cases
- [ ] Create visualization dashboard for results
- [ ] Implement automated regression testing
- [ ] Add load testing capabilities

## Contributing

To contribute new test cases or evaluation criteria:

1. Add test cases following the existing pattern
2. Document expected behavior
3. Test thoroughly before committing
4. Update this README with new test descriptions

## License

Same as parent project.
