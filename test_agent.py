import subprocess
import json
import sys


def test_agent_outputs_valid_json():
    """Run agent.py with a simple question and check the JSON output."""
    # Use the same interpreter that would run the agent
    result = subprocess.run(
        [sys.executable, "agent.py", "What is the capital of France?"],
        capture_output=True,
        text=True,
    )

    # Check exit code (should be 0 on success)
    assert result.returncode == 0, f"Agent failed with stderr:\n{result.stderr}"

    # Parse stdout as JSON
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        assert False, f"stdout is not valid JSON: {result.stdout}"

    # Verify required fields
    assert "answer" in output, "JSON missing 'answer' field"
    assert "tool_calls" in output, "JSON missing 'tool_calls' field"
    assert isinstance(output["answer"], str), "'answer' must be a string"
    assert isinstance(output["tool_calls"], list), "'tool_calls' must be a list"
    # For task 1, tool_calls should be empty
    assert len(output["tool_calls"]) == 0, "'tool_calls' should be empty in task 1"