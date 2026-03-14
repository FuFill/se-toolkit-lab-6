import subprocess
import json
import sys


def test_agent_outputs_valid_json():
    """Run agent.py with a simple question and check the JSON output."""
    result = subprocess.run(
        [sys.executable, "agent.py", "What is the capital of France?"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Agent failed with stderr:\n{result.stderr}"
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        assert False, f"stdout is not valid JSON: {result.stdout}"
    assert "answer" in output
    assert "source" in output
    assert "tool_calls" in output
    assert isinstance(output["answer"], str)
    assert isinstance(output["source"], str)
    assert isinstance(output["tool_calls"], list)


def test_merge_conflict_question():
    """Agent should use read_file and refer to git-workflow.md."""
    question = "How do you resolve a merge conflict?"
    result = subprocess.run(
        [sys.executable, "agent.py", question],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Agent failed: {result.stderr}"
    output = json.loads(result.stdout)
    # Check that tool_calls contains at least one read_file
    read_file_calls = [
        tc for tc in output["tool_calls"]
        if tc["tool"] == "read_file" and "git-workflow.md" in tc["args"].get("path", "")
    ]
    assert len(read_file_calls) > 0, "Expected read_file of git-workflow.md"
    # Source should mention git-workflow.md
    assert "git-workflow.md" in output["source"], f"Source missing git-workflow.md: {output['source']}"
    # Answer should be non-empty
    assert output["answer"], "Answer is empty"


def test_list_files_question():
    """Agent should use list_files on wiki directory."""
    question = "What files are in the wiki directory?"
    result = subprocess.run(
        [sys.executable, "agent.py", question],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Agent failed: {result.stderr}"
    output = json.loads(result.stdout)
    # Check that tool_calls contains list_files
    list_calls = [tc for tc in output["tool_calls"] if tc["tool"] == "list_files"]
    assert len(list_calls) > 0, "Expected list_files tool call"
    # The answer should mention some files (e.g., git-workflow.md)
    assert any(filename in output["answer"] for filename in ["git-workflow.md", "qwen.md", "github.md"]), \
        "Answer does not mention any wiki files"