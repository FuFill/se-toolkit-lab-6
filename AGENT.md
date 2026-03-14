# Agent Documentation

## Overview

This agent is an LLM-powered assistant that can explore the project wiki, read source code, and query the backend API to answer questions. It implements an agentic loop with three tools: `read_file`, `list_files`, and `query_api`. The agent can answer wiki-based questions, inspect source code for technical details, and query live API endpoints for data-dependent answers.

## Tools

- **`read_file(path)`** – Reads a file from the project repository. Path must be relative to the project root. Returns file contents or an error message. Enforces security by restricting access to files within the project root.

- **`list_files(path)`** – Lists files and directories at the given relative path. Returns a newline-separated list or an error. Also restricted to the project root.

- **`query_api(method, path, body, auth)`** – Queries the backend API with the specified HTTP method and path. 
  - `method`: GET, POST, PUT, DELETE, PATCH
  - `path`: API endpoint path (e.g., `/items/`, `/analytics/completion-rate`)
  - `body`: Optional JSON request body for POST/PUT
  - `auth`: Boolean (default true) – set to false to test unauthenticated responses
  
  Returns JSON with `status_code` and `body`. Uses `LMS_API_KEY` from `.env.docker.secret` for authentication when `auth=true`.

## Environment Variables

The agent reads configuration from environment variables:

| Variable | Source | Purpose |
|----------|--------|---------|
| `LLM_API_KEY` | `.env.agent.secret` | LLM provider API key |
| `LLM_API_BASE` | `.env.agent.secret` | LLM API endpoint URL |
| `LLM_MODEL` | `.env.agent.secret` | Model name |
| `LMS_API_KEY` | `.env.docker.secret` | Backend API authentication |
| `AGENT_API_BASE_URL` | `.env.docker.secret` or default | Backend base URL (default: `http://localhost:42002`) |

## Agentic Loop

1. The user question and system prompt are sent to the LLM along with tool definitions.
2. If the LLM responds with tool calls, each tool is executed and the results are appended as new messages with role `tool`.
3. The assistant's message with tool_calls is appended first, then tool results follow (required by OpenAI API).
4. The updated conversation is sent back to the LLM.
5. This repeats until the LLM responds with a text message (no tool calls) or until 25 iterations are reached.
6. The final text message is parsed to extract the answer and source.

## Source Extraction

The system prompt instructs the LLM to include a source line in the format:
`Source: <file-path>#<section>`

The agent splits the answer by lines, extracts any line starting with "Source:" as the source, and removes it from the answer text. If no such line is found, the source field is empty (acceptable for API-based answers).

## Decision Logic

The system prompt guides the LLM to choose the right tool:

- **Wiki questions**: Use `list_files` to explore wiki, then `read_file` on relevant files (e.g., `wiki/git-workflow.md` for merge conflicts, `wiki/github.md` for branch protection).
- **Source code questions**: Read specific files (e.g., `backend/app/main.py` for framework info, `backend/app/routers/` for API domains).
- **API data questions**: Use `query_api` (e.g., `GET /items/` for item count, `GET /analytics/completion-rate?lab=lab-XX` for analytics).
- **Bug diagnosis**: Use `query_api` to reproduce the error, then `read_file` to find the buggy code.
- **Request lifecycle**: Read `docker-compose.yml`, `Dockerfile`, `caddy/Caddyfile`, `backend/app/main.py`.
- **ETL idempotency**: Read `backend/app/etl.py` and look for `external_id` checks.

## Running the Agent

Ensure `.env.agent.secret` and `.env.docker.secret` are configured. Then:

```bash
uv run agent.py "How many items are in the database?"
```

## Lessons Learned

1. **Tool message ordering**: The OpenAI API requires that messages with role `tool` must follow the assistant's message with `tool_calls`. Initially, we appended tool results first, which caused 400 errors. Fixed by appending the assistant message first.

2. **UTF-8 on Windows**: The agent outputs Unicode characters (e.g., arrows, box-drawing characters from file contents). On Windows, stdout uses cp1251 by default, causing `UnicodeEncodeError`. Fixed with `sys.stdout.reconfigure(encoding='utf-8')`.

3. **API authentication**: The backend uses `Authorization: Bearer <LMS_API_KEY>` header, not `X-API-Key`. Initially used the wrong header format.

4. **LLM guidance**: The LLM needs explicit instructions in the system prompt to:
   - Stop exploring after gathering enough information
   - Provide complete answers immediately (not "Let me check...")
   - Use specific files for specific question types

5. **Iteration limits**: Too few iterations (5-10) caused incomplete answers for multi-file questions. Increased to 25 for complex reasoning questions.

6. **Tool schema clarity**: Adding detailed descriptions and examples in tool schemas helps the LLM choose the right tool and parameters.

## Benchmark Results

Final score: **10/10** on local benchmark (`run_eval.py`)

| # | Question Type | Tool(s) Used |
|---|---------------|--------------|
| 1 | Wiki: branch protection | `read_file` |
| 2 | Wiki: SSH/VM connection | `read_file` |
| 3 | Source: web framework | `read_file` |
| 4 | Source: API routers | `list_files`, `read_file` |
| 5 | API: item count | `query_api` |
| 6 | API: status code without auth | `query_api` (auth=false) |
| 7 | Bug: ZeroDivisionError | `query_api`, `read_file` |
| 8 | Bug: TypeError in sorted() | `query_api`, `read_file` |
| 9 | Reasoning: request lifecycle | `read_file` (4 files) |
| 10 | Reasoning: ETL idempotency | `read_file` |

Note: The autochecker bot tests 10 additional hidden questions and uses LLM-based judging for open-ended reasoning questions.
