# Agent Documentation

## Overview

This agent (`agent.py`) is a simple command‑line interface that sends a user question to an LLM and returns a structured JSON answer. It is the foundation for later tasks where tool calling and an agentic loop will be added.

## LLM Provider

The agent uses the **Qwen Code API** running on a VM, as set up in the lab instructions.  

- **Model:** `qwen3-coder-plus` (configured via `LLM_MODEL`)  
- **API endpoint:** `http://<vm-ip>:<port>/v1` (set via `LLM_API_BASE`)  
- **Authentication:** Bearer token stored as `LLM_API_KEY`

All these values are read from the `.env.agent.secret` file (not committed to Git).

## How It Works

1. The script loads environment variables from `.env.agent.secret`.
2. It takes the first command‑line argument as the user question.
3. It creates an OpenAI client pointing to the Qwen API base URL.
4. It sends a chat completion request with a minimal system prompt and the user question.
5. On success, it prints a JSON object to **stdout**:

   ```json
   {"answer": "model response", "tool_calls": []}
