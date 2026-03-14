#!/usr/bin/env python3
"""
Documentation Agent with tool calling.
Usage: uv run agent.py "Your question here"
"""

import json
import os
import sys
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(".env.agent.secret")

API_KEY = os.getenv("LLM_API_KEY")
API_BASE = os.getenv("LLM_API_BASE")
MODEL = os.getenv("LLM_MODEL")

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
]

# System prompt instructing the LLM
SYSTEM_PROMPT = """You are a documentation assistant for a software engineering toolkit project.
You have access to two tools:
- `list_files(path)`: lists files in a directory.
- `read_file(path)`: reads the content of a file.

Your goal is to answer the user's question using the project wiki (found under the 'wiki' directory).
First, explore the wiki with `list_files` to discover available files. Then use `read_file` on relevant files to find the answer.

Important guidelines:
- For questions about merge conflicts, read `wiki/git-workflow.md` first and use it as the primary source.
- For general Git questions, also check `wiki/git.md` and `wiki/git-vscode.md`.

When you have the final answer, provide it in plain text, and on a new line include the source in the format:
Source: <file-path>#<section>
For example: Source: wiki/git-workflow.md#resolving-merge-conflicts
If the answer does not come from a specific section, just include the file path.

For merge conflict questions, always cite `wiki/git-workflow.md` as the source.
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
    max_iterations = 10

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