# Task 2 Plan: The Documentation Agent

## Overview

Extend the CLI agent from Task 1 with two tools (`read_file`, `list_files`) and an agentic loop. The agent will use these tools to explore the project wiki and answer questions, finally outputting JSON with `answer`, `source`, and `tool_calls`.

## Tool Definitions

We'll use OpenAI‑compatible function calling. The tools are defined as JSON schemas:

- **`read_file`**:  
  - Description: "Read the contents of a file from the project repository."  
  - Parameters: `path` (string) – relative path from project root.  
  - Returns: file content or error message.

- **`list_files`**:  
  - Description: "List files and directories at a given path."  
  - Parameters: `path` (string) – relative directory path from project root.  
  - Returns: newline‑separated listing or error.

## Agentic Loop

1. Initialize messages with system prompt and user question.
2. For up to 10 iterations:
   - Call LLM with messages and tools.
   - If response contains `tool_calls`:
     - For each tool call, execute the corresponding function (with security checks).
     - Append a new message with role `tool`, containing the result, and reference the tool call ID.
     - Continue loop.
   - If response has no tool calls, treat it as final answer.
3. Parse final answer to extract `source` (see below).
4. Output JSON with `answer`, `source`, and the list of all tool calls (with their args and results).

## Source Extraction

The system prompt instructs the LLM to end its final answer with a line in the format:  
`Source: <file-path>#<section>`  
(e.g., `Source: wiki/git-workflow.md#resolving-merge-conflicts`).

We'll split the answer by lines, take the last line that starts with "Source:" as the source, and remove it from the answer text. If no such line, `source` is an empty string.

## Security

All file operations must be confined to the project root. We'll:

- Determine the project root as the directory containing `agent.py`.
- For any given path, compute its absolute path using `os.path.abspath(os.path.join(project_root, path))`.
- Verify that the resolved path starts with `project_root` (using `os.path.commonpath`). If not, return an error message.

## System Prompt Strategy

The system prompt will:

- Explain the available tools and their purpose.
- Instruct the LLM to use `list_files` to discover wiki contents, then `read_file` to retrieve relevant information.
- Remind it to include the source reference (file + section) at the end of the final answer.
- Emphasize that the answer should be concise and directly address the user's question.

## Testing

We'll add two regression tests (using `pytest`):

1. **Merge conflict question** – runs agent with "How do you resolve a merge conflict?" and checks that:
   - `tool_calls` contains at least one `read_file` call.
   - `source` contains `git-workflow.md`.
2. **List files question** – runs agent with "What files are in the wiki?" and checks that:
   - `tool_calls` contains a `list_files` call.
   - The answer mentions some files (e.g., "git-workflow.md").

The tests will use the actual wiki files present in the repository.

## Implementation Steps

1. Update `agent.py` to define the two tool functions and the agentic loop.
2. Modify the LLM call to include `tools` parameter.
3. Implement path security.
4. Add source parsing.
5. Update `AGENT.md` with documentation.
6. Create two test functions in `test_agent.py`.
7. Commit plan first, then code.
