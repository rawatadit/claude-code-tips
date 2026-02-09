"""Tests for blog_pipeline.py — 100% coverage via mocked SDK."""

import asyncio
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Mock the claude_agent_sdk module before importing blog_pipeline
# ---------------------------------------------------------------------------

# Create mock classes that behave like the real SDK types
mock_sdk = MagicMock()


class _AgentDefinition:
    def __init__(self, *, description, prompt, tools=None, model=None):
        self.description = description
        self.prompt = prompt
        self.tools = tools
        self.model = model


class _ClaudeAgentOptions:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class _TextBlock:
    def __init__(self, text):
        self.text = text


class _ToolUseBlock:
    def __init__(self, name, input_data):
        self.name = name
        self.input = input_data


class _AssistantMessage:
    def __init__(self, content):
        self.content = content


class _ResultMessage:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


mock_sdk.AgentDefinition = _AgentDefinition
mock_sdk.ClaudeAgentOptions = _ClaudeAgentOptions
mock_sdk.TextBlock = _TextBlock
mock_sdk.ToolUseBlock = _ToolUseBlock
mock_sdk.AssistantMessage = _AssistantMessage
mock_sdk.ResultMessage = _ResultMessage
mock_sdk.query = MagicMock()  # will be configured per-test

sys.modules["claude_agent_sdk"] = mock_sdk

# NOW we can import the module under test
import blog_pipeline as bp  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_dirs(tmp_path, monkeypatch):
    """Set up temporary prompt and output directories."""
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    output = tmp_path / "output"
    output.mkdir()

    for name in ("orchestrator", "researcher", "writer", "editor"):
        (prompts / f"{name}.txt").write_text(f"Prompt for {name}")

    monkeypatch.setattr(bp, "SCRIPT_DIR", tmp_path)
    monkeypatch.setattr(bp, "PROMPTS_DIR", prompts)
    monkeypatch.setattr(bp, "OUTPUT_DIR", output)

    return tmp_path, prompts, output


# ---------------------------------------------------------------------------
# load_prompt
# ---------------------------------------------------------------------------


class TestLoadPrompt:
    def test_loads_prompt_file(self, tmp_dirs):
        result = bp.load_prompt("researcher")
        assert result == "Prompt for researcher"

    def test_loads_all_prompts(self, tmp_dirs):
        for name in ("orchestrator", "researcher", "writer", "editor"):
            assert bp.load_prompt(name) == f"Prompt for {name}"

    def test_missing_prompt_raises(self, tmp_dirs):
        with pytest.raises(FileNotFoundError):
            bp.load_prompt("nonexistent")


# ---------------------------------------------------------------------------
# build_agents
# ---------------------------------------------------------------------------


class TestBuildAgents:
    def test_returns_three_agents(self, tmp_dirs):
        agents = bp.build_agents()
        assert set(agents.keys()) == {"researcher", "writer", "editor"}

    def test_researcher_config(self, tmp_dirs):
        agents = bp.build_agents()
        r = agents["researcher"]
        assert r.tools == ["WebSearch", "WebFetch", "Write"]
        assert r.model == "haiku"
        assert "research" in r.description.lower()

    def test_writer_config(self, tmp_dirs):
        agents = bp.build_agents()
        w = agents["writer"]
        assert w.tools == ["Read", "Glob", "Write"]
        assert w.model == "sonnet"
        assert "writer" in w.description.lower() or "draft" in w.description.lower()

    def test_editor_config(self, tmp_dirs):
        agents = bp.build_agents()
        e = agents["editor"]
        assert e.tools == ["Read", "Glob"]
        assert "Write" not in e.tools
        assert e.model == "opus"

    def test_agents_have_prompts(self, tmp_dirs):
        agents = bp.build_agents()
        for name, agent in agents.items():
            assert agent.prompt == f"Prompt for {name}"


# ---------------------------------------------------------------------------
# build_orchestrator_options
# ---------------------------------------------------------------------------


class TestBuildOrchestratorOptions:
    def test_returns_prompt_and_options(self, tmp_dirs):
        prompt, options = bp.build_orchestrator_options("test topic")
        assert isinstance(prompt, str)
        assert "test topic" in prompt

    def test_prompt_contains_working_dir(self, tmp_dirs):
        tmp_path = tmp_dirs[0]
        prompt, _ = bp.build_orchestrator_options("topic")
        assert str(tmp_path) in prompt

    def test_options_allowed_tools(self, tmp_dirs):
        _, options = bp.build_orchestrator_options("topic")
        assert options.allowed_tools == ["Task"]

    def test_options_model(self, tmp_dirs):
        _, options = bp.build_orchestrator_options("topic")
        assert options.model == "claude-sonnet-4-5-20250929"

    def test_options_permission_mode(self, tmp_dirs):
        _, options = bp.build_orchestrator_options("topic")
        assert options.permission_mode == "bypassPermissions"

    def test_options_budget_cap(self, tmp_dirs):
        _, options = bp.build_orchestrator_options("topic")
        assert options.max_budget_usd == 1.00

    def test_options_has_agents(self, tmp_dirs):
        _, options = bp.build_orchestrator_options("topic")
        assert "researcher" in options.agents
        assert "writer" in options.agents
        assert "editor" in options.agents

    def test_options_system_prompt(self, tmp_dirs):
        _, options = bp.build_orchestrator_options("topic")
        assert options.system_prompt == "Prompt for orchestrator"

    def test_options_cwd(self, tmp_dirs):
        tmp_path = tmp_dirs[0]
        _, options = bp.build_orchestrator_options("topic")
        assert options.cwd == str(tmp_path)


# ---------------------------------------------------------------------------
# print_colored
# ---------------------------------------------------------------------------


class TestPrintColored:
    def test_known_color(self, capsys):
        bp.print_colored("hello", "orchestrator")
        out = capsys.readouterr().out
        assert "hello" in out
        assert "\033[36m" in out  # cyan
        assert "\033[0m" in out  # reset

    def test_default_color(self, capsys):
        bp.print_colored("plain")
        out = capsys.readouterr().out
        assert "plain" in out
        assert "\033[0m" in out

    def test_unknown_color_falls_back(self, capsys):
        bp.print_colored("text", "nonexistent")
        out = capsys.readouterr().out
        assert "text" in out
        # Unknown color: COLORS.get returns empty string, still gets reset
        assert "\033[0m" in out

    def test_bold(self, capsys):
        bp.print_colored("title", "bold")
        out = capsys.readouterr().out
        assert "\033[1m" in out

    def test_dim(self, capsys):
        bp.print_colored("subtle", "dim")
        out = capsys.readouterr().out
        assert "\033[2m" in out


# ---------------------------------------------------------------------------
# _verify_outputs
# ---------------------------------------------------------------------------


class TestVerifyOutputs:
    def test_all_files_present(self, tmp_dirs, capsys):
        _, _, output = tmp_dirs
        research = output / "research"
        research.mkdir()
        (research / "current_state.md").write_text("research a")
        (research / "future_trends.md").write_text("research b")
        (output / "draft.md").write_text("draft content")
        (output / "final_post.md").write_text("one two three four five")

        bp._verify_outputs()
        out = capsys.readouterr().out
        assert "[OK]" in out
        assert "MISSING" not in out
        assert "5 words" in out

    def test_some_files_missing(self, tmp_dirs, capsys):
        _, _, output = tmp_dirs
        research = output / "research"
        research.mkdir()
        # Only create one file
        (research / "current_state.md").write_text("research a")

        bp._verify_outputs()
        out = capsys.readouterr().out
        assert "[OK]" in out
        assert "[MISSING]" in out
        # Word count should NOT appear when not all files exist
        assert "words" not in out

    def test_no_files_present(self, tmp_dirs, capsys):
        _, _, output = tmp_dirs
        (output / "research").mkdir()

        bp._verify_outputs()
        out = capsys.readouterr().out
        assert out.count("[MISSING]") == 4
        assert "words" not in out


# ---------------------------------------------------------------------------
# run_pipeline
# ---------------------------------------------------------------------------


class TestRunPipeline:
    def _make_async_gen(self, messages):
        """Create an async generator yielding the given messages."""
        async def gen(**kwargs):
            for msg in messages:
                yield msg
        return gen

    def test_text_block_message(self, tmp_dirs, capsys):
        msg = _AssistantMessage(content=[_TextBlock("Launching researchers")])
        result = _ResultMessage(
            total_cost_usd=0.05, num_turns=3, duration_ms=12000, subtype="success"
        )
        mock_sdk.query.side_effect = self._make_async_gen([msg, result])

        asyncio.run(bp.run_pipeline("test topic"))
        out = capsys.readouterr().out
        assert "Launching researchers" in out
        assert "Pipeline Complete!" in out
        assert "$0.0500" in out
        assert "Turns: 3" in out
        assert "12.0s" in out

    def test_tool_use_task_delegation(self, tmp_dirs, capsys):
        tool = _ToolUseBlock("Task", {"subagent_type": "researcher", "description": "research AI"})
        msg = _AssistantMessage(content=[tool])
        result = _ResultMessage(total_cost_usd=0.01, num_turns=1, duration_ms=5000)
        mock_sdk.query.side_effect = self._make_async_gen([msg, result])

        asyncio.run(bp.run_pipeline("AI"))
        out = capsys.readouterr().out
        assert "Delegating to researcher: research AI" in out

    def test_tool_use_unknown_agent_type(self, tmp_dirs, capsys):
        tool = _ToolUseBlock("Task", {"subagent_type": "custom_agent", "description": "do stuff"})
        msg = _AssistantMessage(content=[tool])
        result = _ResultMessage(total_cost_usd=0.01, num_turns=1, duration_ms=1000)
        mock_sdk.query.side_effect = self._make_async_gen([msg, result])

        asyncio.run(bp.run_pipeline("topic"))
        out = capsys.readouterr().out
        # Unknown agent type falls back to "dim" color
        assert "Delegating to custom_agent: do stuff" in out

    def test_non_task_tool_use_ignored(self, tmp_dirs, capsys):
        tool = _ToolUseBlock("Read", {"file_path": "/some/file"})
        msg = _AssistantMessage(content=[tool])
        result = _ResultMessage(total_cost_usd=0.0, num_turns=1, duration_ms=500)
        mock_sdk.query.side_effect = self._make_async_gen([msg, result])

        asyncio.run(bp.run_pipeline("topic"))
        out = capsys.readouterr().out
        assert "Delegating" not in out

    def test_result_without_optional_attrs(self, tmp_dirs, capsys):
        """ResultMessage may lack cost/turns/duration attributes."""
        result = MagicMock(spec=[])  # empty spec = no attributes
        # Make isinstance checks work
        result.__class__ = _ResultMessage
        mock_sdk.query.side_effect = self._make_async_gen([result])

        asyncio.run(bp.run_pipeline("topic"))
        out = capsys.readouterr().out
        assert "Pipeline Complete!" in out
        assert "Cost:" not in out
        assert "Turns:" not in out
        assert "Duration:" not in out

    def test_result_with_zero_values(self, tmp_dirs, capsys):
        """Zero-valued attrs should not print (falsy)."""
        result = _ResultMessage(
            total_cost_usd=0.0, num_turns=0, duration_ms=0
        )
        mock_sdk.query.side_effect = self._make_async_gen([result])

        asyncio.run(bp.run_pipeline("topic"))
        out = capsys.readouterr().out
        assert "Pipeline Complete!" in out
        assert "Cost:" not in out

    def test_creates_output_dirs(self, tmp_dirs):
        _, _, output = tmp_dirs
        research_dir = output / "research"
        # Ensure it doesn't exist yet
        assert not research_dir.exists()

        result = _ResultMessage(total_cost_usd=0.0, num_turns=0, duration_ms=0)
        mock_sdk.query.side_effect = self._make_async_gen([result])

        asyncio.run(bp.run_pipeline("topic"))
        assert research_dir.exists()

    def _make_async_gen(self, messages):
        async def gen(**kwargs):
            for msg in messages:
                yield msg
        return gen

    def test_banner_displayed(self, tmp_dirs, capsys):
        result = _ResultMessage(total_cost_usd=0.0, num_turns=0, duration_ms=0)
        mock_sdk.query.side_effect = self._make_async_gen([result])

        asyncio.run(bp.run_pipeline("renewable energy"))
        out = capsys.readouterr().out
        assert "Blog Pipeline: renewable energy" in out
        assert "=" * 60 in out


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


class TestMain:
    def test_no_args_exits(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["blog_pipeline.py"])
        with pytest.raises(SystemExit) as exc_info:
            bp.main()
        assert exc_info.value.code == 1

    def test_no_args_prints_usage(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["blog_pipeline.py"])
        with pytest.raises(SystemExit):
            bp.main()
        out = capsys.readouterr().out
        assert "Usage:" in out
        assert "Example:" in out

    def test_with_topic_runs_pipeline(self, monkeypatch, tmp_dirs):
        monkeypatch.setattr(sys, "argv", ["blog_pipeline.py", "AI safety"])

        async def fake_gen(**kwargs):
            result = _ResultMessage(total_cost_usd=0.0, num_turns=0, duration_ms=0)
            yield result

        mock_sdk.query.side_effect = fake_gen

        # Should not raise
        bp.main()


# ---------------------------------------------------------------------------
# COLORS dict
# ---------------------------------------------------------------------------


class TestColors:
    def test_all_expected_keys(self):
        expected = {"orchestrator", "researcher", "writer", "editor", "reset", "dim", "bold"}
        assert set(bp.COLORS.keys()) == expected

    def test_all_values_are_ansi(self):
        for key, value in bp.COLORS.items():
            assert value.startswith("\033["), f"COLORS[{key!r}] is not an ANSI code"


# ---------------------------------------------------------------------------
# __name__ == "__main__" guard
# ---------------------------------------------------------------------------


class TestMainGuard:
    def test_main_called_when_run_as_script(self, monkeypatch, tmp_dirs):
        """Cover line 252: if __name__ == '__main__': main()"""
        monkeypatch.setattr(sys, "argv", ["blog_pipeline.py", "test"])

        async def fake_gen(**kwargs):
            yield _ResultMessage(total_cost_usd=0.0, num_turns=0, duration_ms=0)

        mock_sdk.query.side_effect = fake_gen

        # Execute the module-level guard by running the file as a script
        import runpy

        runpy.run_path(str(Path(bp.__file__)), run_name="__main__")
