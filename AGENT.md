# Agent Documentation

## Overview

This agent is an extension of Task 1, now capable of using tools to explore the project wiki and answer questions. It implements an agentic loop that can call `read_file` and `list_files` tools, feeding results back to the LLM until a final answer is reached.

## Tools

- **`read_file(path)`** – Reads a file from the project repository. Path must be relative to the project root. Returns file contents or an error message.
- **`list_files(path)`** – Lists files and directories at the given relative path. Returns a newline-separated list or an error.

Both tools enforce security: they will not access files outside the project root.

## Agentic Loop

1. The user question and system prompt are sent to the LLM along with tool definitions.
2. If the LLM responds with tool calls, each tool is executed and the results are appended as new messages with role `tool`.
3. The updated conversation is sent back to the LLM.
4. This repeats until the LLM responds with a text message (no tool calls) or until 10 iterations are reached.
5. The final text message is parsed to extract the answer and source (see below).

## Source Extraction

The system prompt instructs the LLM to include a source line at the end of its final answer in the format:
`Source: <file-path>#<section>`
The agent splits the answer by lines, takes the last line starting with "Source:" as the source, and removes it from the answer text. If no such line is found, the source field is empty.

## Running the Agent

Ensure `.env.agent.secret` is configured with your Qwen API details. Then:

```bash
uv run agent.py "How do you resolve a merge conflict?"
