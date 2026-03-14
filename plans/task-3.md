# Task 3 Plan: The System Agent

## Overview

Add a `query_api` tool to the agent so it can query the deployed backend API and answer:
1. Static system facts (framework, ports, status codes)
2. Data-dependent queries (item count, scores, analytics)

## Implementation Plan

### 1. Environment Variables

Read from environment variables (not hardcoded):

| Variable | Source | Purpose |
|----------|--------|---------|
| `LMS_API_KEY` | `.env.docker.secret` | Backend API authentication |
| `AGENT_API_BASE_URL` | `.env.docker.secret` or default | Backend base URL (default: `http://localhost:42002`) |
| `LLM_API_KEY`, `LLM_API_BASE`, `LLM_MODEL` | `.env.agent.secret` | LLM provider config |

### 2. Tool Schema: `query_api`

Add to `TOOLS` list:

```python
{
    "type": "function",
    "function": {
        "name": "query_api",
        "description": "Query the backend API with HTTP method and path. Use for data queries like item counts, analytics, status codes.",
        "parameters": {
            "type": "object",
            "properties": {
                "method": {"type": "string", "description": "HTTP method: GET, POST, PUT, DELETE"},
                "path": {"type": "string", "description": "API path e.g., /items/, /analytics/completion-rate"},
                "body": {"type": "string", "description": "Optional JSON request body for POST/PUT"}
            },
            "required": ["method", "path"]
        }
    }
}
```

### 3. Tool Implementation

```python
def query_api(method: str, path: str, body: str = None) -> str:
    """Make HTTP request to backend API with LMS_API_KEY auth."""
    import requests
    base_url = os.getenv("AGENT_API_BASE_URL", "http://localhost:42002")
    api_key = os.getenv("LMS_API_KEY")
    url = f"{base_url}{path}"
    headers = {"X-API-Key": api_key} if api_key else {}
    
    try:
        response = requests.request(
            method=method.upper(),
            url=url,
            headers=headers,
            json=json.loads(body) if body else None,
            timeout=10
        )
        return json.dumps({
            "status_code": response.status_code,
            "body": response.json() if response.content else response.text
        })
    except Exception as e:
        return json.dumps({"error": str(e)})
```

### 4. System Prompt Update

Update `SYSTEM_PROMPT` to guide the LLM:

- Use `read_file` for wiki questions and source code questions
- Use `list_files` to explore directories
- Use `query_api` for:
  - Data queries (how many items, scores, analytics)
  - System facts (status codes, API responses)
  - Bug diagnosis (query API, get error, read source)

### 5. Agent Output Format

For questions without wiki source, `source` can be empty string.

### 6. Testing Strategy

Run `uv run run_eval.py` and iterate:

1. First run: expect failures on API questions
2. Fix tool schema/prompt based on feedback
3. Re-run until all 10 questions pass

### 7. Known Benchmark Questions

| # | Topic | Expected Tool |
|---|-------|---------------|
| 0 | Wiki: branch protection | `read_file` |
| 1 | Wiki: SSH connection | `read_file` |
| 2 | Source: web framework | `read_file` |
| 3 | API routers list | `list_files` |
| 4 | DB item count | `query_api` |
| 5 | Auth status code | `query_api` |
| 6 | ZeroDivisionError bug | `query_api` + `read_file` |
| 7 | TypeError bug | `query_api` + `read_file` |
| 8 | Request lifecycle | `read_file` (LLM judge) |
| 9 | ETL idempotency | `read_file` (LLM judge) |

## Initial Benchmark Run

First run results:
- Score: 3/10
- First failures:
  - Question 3 (framework): Agent didn't read source code
  - Question 4 (routers): Agent didn't use list_files on backend/routers
  - Questions 5-10: query_api tool not implemented yet

Iteration strategy:
1. Add query_api tool with proper authentication
2. Update system prompt with specific file paths for each question type
3. Increase max_iterations for complex reasoning questions
4. Add explicit instructions to provide complete answers immediately

## Final Benchmark Results

**Score: 10/10** on local benchmark (`run_eval.py`)

All questions passed:
- Wiki questions (1-2): read_file on correct files
- Source code questions (3-4): read_file on backend files
- API data questions (5-6): query_api with/without auth
- Bug diagnosis (7-8): query_api + read_file
- Reasoning questions (9-10): read_file on multiple files

## Lessons Learned

1. **Tool message ordering**: OpenAI API requires assistant message with tool_calls before tool result messages.

2. **UTF-8 on Windows**: Need `sys.stdout.reconfigure(encoding='utf-8')` for Unicode output.

3. **API authentication**: Backend uses `Authorization: Bearer <LMS_API_KEY>`, not `X-API-Key`.

4. **LLM guidance**: System prompt needs explicit instructions for:
   - Which files to read for each question type
   - When to stop exploring and provide answers
   - How to format output with sources

5. **Iteration limits**: 25 iterations needed for complex reasoning questions.

6. **Tool schema clarity**: Detailed descriptions help LLM choose correct tools.
