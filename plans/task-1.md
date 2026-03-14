# Task 1 Plan: Call an LLM from Code

## LLM Provider and Model

I will use the **Qwen Code API** running on my VM, as recommended.  

- **Model:** `qwen3-coder-plus` (supports tool calling for later tasks)  
- **API base:** `http://<vm-ip>:<port>/v1` (set via `LLM_API_BASE`)  
- **API key:** Stored in `.env.agent.secret` as `LLM_API_KEY`

This provider gives 1000 free requests per day, works from Russia, and has strong tool‑calling capabilities.

## Agent Structure (`agent.py`)

The agent will:

1. **Load environment** – use `python-dotenv` to read `.env.agent.secret`.
2. **Parse command line** – the first argument is the user question.
3. **Call the LLM** – use the `openai` Python library (compatible with Qwen’s OpenAI‑style endpoint).  
   - System prompt: minimal, just instruct the model to answer concisely (to be extended later).
   - Timeout: set a generous timeout (<60 seconds overall).
4. **Handle output** – if the call succeeds, print a JSON object with `answer` (the model’s reply) and `tool_calls` (empty list) to **stdout**.
   - All debug/progress information goes to **stderr**.
   - If the call fails (API error, timeout, etc.), print an error message to stderr and exit with code 1.
5. **Exit code** – 0 on success, non‑zero on failure.

## Environment Variables (`.env.agent.secret`)

LLM_API_KEY=8774a89b791548be9cbe1113e78ab2ef
LLM_API_BASE=<http://10.93.25.110:8080/v1> #adjust port as needed
LLM_MODEL=qwen3-coder-plus

The script will use these to configure the OpenAI client.

## Testing Plan

One regression test will be written (e.g., `test_agent.py`) that:

- Runs `uv run agent.py "What is 2+2?"` as a subprocess.
- Parses the stdout JSON.
- Asserts that the JSON contains both `"answer"` (string) and `"tool_calls"` (list).
- Optionally checks that `tool_calls` is empty.

The test will be executed via `pytest` (already in `uv sync --dev` dependencies).

## Commit Strategy

1. Create branch `task-1-call-llm`.
2. Commit this plan first (`plans/task-1.md`).
3. Implement `agent.py`, `AGENT.md`, and the test.
4. Push and open a PR, request partner review.
5. Merge after approval.
