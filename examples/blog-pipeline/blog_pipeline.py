#!/usr/bin/env python3
"""
Multi-Agent Blog Post Pipeline

Demonstrates Claude Agent SDK subagent patterns:
- Parallel execution (two researchers run simultaneously)
- Sequential handoff (research → write → edit → revise)
- Tool restriction (editor is read-only)
- Model differentiation (haiku/sonnet/opus for different roles)

Usage:
    python blog_pipeline.py "The future of renewable energy"
"""

import asyncio
import sys
from pathlib import Path

from claude_agent_sdk import (
    AgentDefinition,
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    query,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent
PROMPTS_DIR = SCRIPT_DIR / "prompts"
OUTPUT_DIR = SCRIPT_DIR / "output"


def load_prompt(name: str) -> str:
    """Load a prompt template from the prompts/ directory."""
    return (PROMPTS_DIR / f"{name}.txt").read_text()


# ---------------------------------------------------------------------------
# Agent definitions
# ---------------------------------------------------------------------------


def build_agents() -> dict[str, AgentDefinition]:
    """
    Define the four specialist agents.

    Each agent has:
    - A restricted tool set (least-privilege principle)
    - A specific model (cost/quality tradeoff)
    - A system prompt loaded from prompts/
    - A description the orchestrator uses to decide when to invoke it
    """
    return {
        # ── Researcher ────────────────────────────────────────────────
        # Cheap, fast model for information gathering.
        # Can search the web and write files, but nothing else.
        "researcher": AgentDefinition(
            description=(
                "Research specialist. Use this agent to gather information "
                "on a specific topic and angle. It will search the web and "
                "write structured research notes to a file you specify."
            ),
            prompt=load_prompt("researcher"),
            tools=["WebSearch", "WebFetch", "Write"],
            model="haiku",
        ),
        # ── Writer ────────────────────────────────────────────────────
        # Balanced model for long-form content creation.
        # Can read research and write drafts, but cannot search the web.
        "writer": AgentDefinition(
            description=(
                "Blog writer. Use this agent to draft or revise a blog post. "
                "For an initial draft, tell it to read research notes and "
                "write to output/draft.md. For revision, include the editor's "
                "feedback and tell it to write to output/final_post.md."
            ),
            prompt=load_prompt("writer"),
            tools=["Read", "Glob", "Write"],
            model="sonnet",
        ),
        # ── Editor ────────────────────────────────────────────────────
        # Highest-quality model for nuanced editorial judgment.
        # READ-ONLY: can read files but physically cannot modify them.
        "editor": AgentDefinition(
            description=(
                "Senior editor. Use this agent to review a draft blog post. "
                "It will read the draft and research notes, then return "
                "numbered editorial feedback. It cannot modify any files."
            ),
            prompt=load_prompt("editor"),
            tools=["Read", "Glob"],  # read-only!
            model="opus",
        ),
    }


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def build_orchestrator_options(topic: str) -> tuple[str, ClaudeAgentOptions]:
    """
    Configure the orchestrator agent.

    The orchestrator can ONLY use the Task tool — it delegates all real work
    to the specialist agents defined above.
    """
    orchestrator_prompt = load_prompt("orchestrator")

    prompt = (
        f"Produce a blog post about: {topic}\n\n"
        f"Follow your pipeline instructions exactly. "
        f"The working directory for all file operations is: {SCRIPT_DIR}"
    )

    options = ClaudeAgentOptions(
        # The orchestrator's system prompt defines the pipeline steps
        system_prompt=orchestrator_prompt,
        # ONLY the Task tool — forces delegation to subagents
        allowed_tools=["Task"],
        # Register the specialist agents
        agents=build_agents(),
        # Use sonnet for orchestration (good balance of reasoning/cost)
        model="claude-sonnet-4-5-20250929",
        # Autonomous execution — no human approval needed
        permission_mode="bypassPermissions",
        # Cost cap to prevent runaway spending
        max_budget_usd=1.00,
        # Work from the script directory so relative paths resolve
        cwd=str(SCRIPT_DIR),
    )

    return prompt, options


# ---------------------------------------------------------------------------
# Streaming output
# ---------------------------------------------------------------------------

# ANSI color codes for terminal output
COLORS = {
    "orchestrator": "\033[36m",  # cyan
    "researcher": "\033[33m",  # yellow
    "writer": "\033[32m",  # green
    "editor": "\033[35m",  # magenta
    "reset": "\033[0m",
    "dim": "\033[2m",
    "bold": "\033[1m",
}


def print_colored(text: str, color: str = "reset") -> None:
    """Print text with ANSI color codes."""
    print(f"{COLORS.get(color, '')}{text}{COLORS['reset']}")


async def run_pipeline(topic: str) -> None:
    """Run the full blog post pipeline and stream progress."""

    # Ensure output directories exist
    (OUTPUT_DIR / "research").mkdir(parents=True, exist_ok=True)

    prompt, options = build_orchestrator_options(topic)

    print_colored(f"\n{'='*60}", "bold")
    print_colored(f"  Blog Pipeline: {topic}", "bold")
    print_colored(f"{'='*60}\n", "bold")

    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print_colored(f"  {block.text}", "orchestrator")
                elif isinstance(block, ToolUseBlock):
                    # Show when the orchestrator delegates to a subagent
                    if block.name == "Task":
                        agent_type = block.input.get("subagent_type", "unknown")
                        desc = block.input.get("description", "")
                        print_colored(
                            f"\n  >> Delegating to {agent_type}: {desc}",
                            agent_type if agent_type in COLORS else "dim",
                        )

        elif isinstance(message, ResultMessage):
            print_colored(f"\n{'='*60}", "bold")
            print_colored("  Pipeline Complete!", "bold")
            print_colored(f"{'='*60}", "bold")

            if hasattr(message, "total_cost_usd") and message.total_cost_usd:
                print_colored(f"  Cost: ${message.total_cost_usd:.4f}", "dim")
            if hasattr(message, "num_turns") and message.num_turns:
                print_colored(f"  Turns: {message.num_turns}", "dim")
            if hasattr(message, "duration_ms") and message.duration_ms:
                duration_s = message.duration_ms / 1000
                print_colored(f"  Duration: {duration_s:.1f}s", "dim")

            print()

    # Verify outputs
    _verify_outputs()


def _verify_outputs() -> None:
    """Check that expected output files were created."""
    expected = [
        OUTPUT_DIR / "research" / "current_state.md",
        OUTPUT_DIR / "research" / "future_trends.md",
        OUTPUT_DIR / "draft.md",
        OUTPUT_DIR / "final_post.md",
    ]

    print_colored("\n  Output files:", "bold")
    all_ok = True
    for path in expected:
        exists = path.exists()
        status = "OK" if exists else "MISSING"
        color = "dim" if exists else "editor"
        relative = path.relative_to(SCRIPT_DIR)
        print_colored(f"    [{status}] {relative}", color)
        if not exists:
            all_ok = False

    if all_ok:
        final = OUTPUT_DIR / "final_post.md"
        word_count = len(final.read_text().split())
        print_colored(f"\n  Final post: {word_count} words", "dim")
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python blog_pipeline.py \"Your blog topic\"")
        print("Example: python blog_pipeline.py \"The future of renewable energy\"")
        sys.exit(1)

    topic = sys.argv[1]
    asyncio.run(run_pipeline(topic))


if __name__ == "__main__":
    main()
