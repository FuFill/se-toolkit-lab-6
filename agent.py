import json
import os
import sys
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env.agent.secret
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


def call_llm(question: str) -> str:
    """Send question to LLM and return the answer text."""
    client = OpenAI(api_key=API_KEY, base_url=API_BASE)

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant. Answer the user's question concisely.",
                },
                {"role": "user", "content": question},
            ],
            temperature=0.7,
            timeout=30,  # seconds; overall script must stay under 60s
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error calling LLM: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    if len(sys.argv) != 2:
        print("Usage: uv run agent.py \"<question>\"", file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]
    answer = call_llm(question)

    # Build required JSON structure
    output = {"answer": answer, "tool_calls": []}
    # Print only valid JSON to stdout
    print(json.dumps(output, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()