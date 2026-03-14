#!/usr/bin/env python3
"""
System Agent with tool calling (read_file, list_files, query_api).
Usage: uv run agent.py "Your question here"
"""

import json
import os
import sys
import urllib.request
import urllib.error
from openai import OpenAI
from dotenv import load_dotenv

# Load LLM config from .env.agent.secret
load_dotenv(".env.agent.secret")

API_KEY = os.getenv("LLM_API_KEY")
API_BASE = os.getenv("LLM_API_BASE")
MODEL = os.getenv("LLM_MODEL")

# Load LMS API config from .env.docker.secret
load_dotenv(".env.docker.secret", override=True)

LMS_API_KEY = os.getenv("LMS_API_KEY")
AGENT_API_BASE_URL = os.getenv("AGENT_API_BASE_URL", "http://localhost:42002")

if not API_KEY or not API_BASE or not MODEL:
    print(
        "Error: Missing LLM configuration. Check .env.agent.secret file.",
        file=sys.stderr,
    )
    sys.exit(1)

# Determine project root (directory containing this script)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Tool definitions for OpenAI function calling
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file from the project repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from project root (e.g., 'wiki/git-workflow.md').",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories at a given path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory path from project root (e.g., 'wiki').",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_api",
            "description": "Query the backend API with HTTP method and path. Use for data queries like item counts, analytics, status codes, or to test API behavior.",
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {
                        "type": "string",
                        "description": "HTTP method: GET, POST, PUT, DELETE, PATCH",
                    },
                    "path": {
                        "type": "string",
                        "description": "API path e.g., /items/, /analytics/completion-rate, /analytics/top-learners",
                    },
                    "body": {
                        "type": "string",
                        "description": "Optional JSON request body for POST/PUT requests",
                    },
                    "auth": {
                        "type": "boolean",
                        "description": "Whether to include authentication header (default true). Set to false to test unauthenticated responses.",
                    }
                },
                "required": ["method", "path"],
            },
        },
    },
]

# System prompt instructing the LLM
SYSTEM_PROMPT = """You are a documentation assistant for a software engineering toolkit project.
You have access to three tools:
- `list_files(path)`: lists files in a directory.
- `read_file(path)`: reads the content of a file.
- `query_api(method, path, body)`: queries the backend API with HTTP method and path.

Your goal is to answer the user's question using the project wiki, source code, or backend API.

Guidelines by question type:
1. Wiki questions: Use `list_files` to explore wiki, then `read_file` on relevant files.
   - For branch protection: read `wiki/github.md`.
   - For SSH/VM: read `wiki/vm.md` or `wiki/ssh.md`.
   - For merge conflicts: read `wiki/git-workflow.md`.
2. Source code questions: Read specific files.
   - Framework: read `backend/app/main.py` and look for `FastAPI`, `Flask`, `Django`.
   - API routers: use `list_files` on `backend/app/routers`, then read ALL router files in one turn and provide complete summary.
3. API data questions: Use `query_api` with GET method.
   - Item count: `GET /items/`
   - Status codes without auth: `GET /items/` with `auth: false` to see 401 response.
   - Analytics: `GET /analytics/completion-rate?lab=lab-XX`
4. Bug diagnosis: Use `query_api` to reproduce error, then `read_file` to find bug.
5. Request lifecycle questions: Read `docker-compose.yml`, `Dockerfile` (root directory), `caddy/Caddyfile`, `backend/app/main.py` to trace request path.
   After reading all files, provide a complete explanation of the request journey from browser → Caddy → FastAPI → database → back.
6. ETL idempotency questions: Read `backend/app/etl.py` and look for `external_id` checks.
   After reading the file, explain how duplicates are prevented.

CRITICAL: After using tools, ALWAYS provide a complete final answer. Never say "Let me check" or "Let me continue".
Provide the full answer with all information you have gathered.

When you have the answer, provide it in plain text with "Source: <file-path>" on a new line if from wiki/source.

For merge conflict questions: cite `wiki/git-workflow.md`.
For framework questions: cite `backend/app/main.py`.
For router questions: cite `backend/app/routers/`.
"""

def read_file(path: str) -> str:
    """Read file content, ensuring path is within project root."""
    try:
        # Resolve absolute path and check safety
        requested_path = os.path.abspath(os.path.join(PROJECT_ROOT, path))
        if os.path.commonpath([requested_path, PROJECT_ROOT]) != PROJECT_ROOT:
            return f"Error: Access denied - path '{path}' is outside the project directory."
        if not os.path.isfile(requested_path):
            return f"Error: File '{path}' does not exist."
        with open(requested_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"

def list_files(path: str) -> str:
    """List directory contents, ensuring path is within project root."""
    try:
        requested_path = os.path.abspath(os.path.join(PROJECT_ROOT, path))
        if os.path.commonpath([requested_path, PROJECT_ROOT]) != PROJECT_ROOT:
            return f"Error: Access denied - path '{path}' is outside the project directory."
        if not os.path.isdir(requested_path):
            return f"Error: Directory '{path}' does not exist."
        entries = os.listdir(requested_path)
        return "\n".join(entries)
    except Exception as e:
        return f"Error listing directory: {e}"

def query_api(method: str, path: str, body: str = None, auth: bool = True) -> str:
    """Make HTTP request to backend API. Use auth=False to test unauthenticated responses."""
    url = f"{AGENT_API_BASE_URL}{path}"
    headers = {"Authorization": f"Bearer {LMS_API_KEY}"} if (LMS_API_KEY and auth) else {}

    try:
        data = None
        if body:
            data = json.dumps(body).encode('utf-8')
            headers["Content-Type"] = "application/json"

        req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())

        with urllib.request.urlopen(req, timeout=10) as response:
            response_body = response.read().decode('utf-8')
            return json.dumps({
                "status_code": response.status,
                "body": json.loads(response_body) if response_body else {}
            })
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else ""
        return json.dumps({
            "status_code": e.code,
            "body": error_body if error_body else e.reason
        })
    except urllib.error.URLError as e:
        return json.dumps({"error": f"Connection error: {e.reason}"})
    except Exception as e:
        return json.dumps({"error": str(e)})

def call_llm(messages, tools=None):
    """Helper to call the LLM with given messages and tools."""
    client = OpenAI(api_key=API_KEY, base_url=API_BASE)
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            timeout=30,
        )
        return response.choices[0].message
    except Exception as e:
        print(f"Error calling LLM: {e}", file=sys.stderr)
        sys.exit(1)

def execute_tool_call(tool_call):
    """Execute a single tool call and return the result."""
    func_name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)
    if func_name == "read_file":
        result = read_file(args["path"])
    elif func_name == "list_files":
        result = list_files(args["path"])
    elif func_name == "query_api":
        result = query_api(args["method"], args["path"], args.get("body"), args.get("auth", True))
    else:
        result = f"Error: Unknown tool '{func_name}'"
    return {
        "tool": func_name,
        "args": args,
        "result": result,
    }

def extract_source_and_answer(final_message):
    """Parse the final answer to separate answer text and source."""
    lines = final_message.strip().split("\n")
    source = ""
    answer_lines = []
    for line in lines:
        if line.startswith("Source:"):
            source = line[7:].strip()  # after "Source:"
        else:
            answer_lines.append(line)
    answer = "\n".join(answer_lines).strip()
    return answer, source

def main():
    if len(sys.argv) != 2:
        print("Usage: uv run agent.py \"<question>\"", file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]

    # Initialize conversation
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    tool_calls_log = []  # store all tool calls made
    max_iterations = 25

    for _ in range(max_iterations):
        # Get LLM response
        message = call_llm(messages, tools=TOOLS)

        # If no tool calls, we have the final answer
        if not message.tool_calls:
            final_answer, source = extract_source_and_answer(message.content)
            # Build output
            output = {
                "answer": final_answer,
                "source": source,
                "tool_calls": tool_calls_log,
            }
            # Reconfigure stdout to support UTF-8 on Windows
            sys.stdout.reconfigure(encoding='utf-8')
            print(json.dumps(output, ensure_ascii=False))
            sys.exit(0)

        # Append the assistant's message with tool_calls first
        messages.append(message)

        # Handle tool calls
        for tool_call in message.tool_calls:
            # Execute tool
            entry = execute_tool_call(tool_call)
            tool_calls_log.append(entry)

            # Append tool result as a new message with role "tool"
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": entry["result"],
            })

    # If we exit the loop, we hit max iterations
    print("Error: Exceeded maximum tool calls (10).", file=sys.stderr)
    sys.exit(1)

if __name__ == "__main__":
    main()