# Multi-Agent Blog Post Pipeline

A hands-on example of Claude Agent SDK subagent patterns: parallel execution, sequential handoff, tool restriction, and model differentiation.

## What It Does

Given a topic, four specialized agents collaborate to produce a blog post:

```
User provides topic
       |
       v
 [Orchestrator]  (sonnet, tools: Task only)
       |
       +-- parallel --> [Researcher A] (haiku) --> output/research/current_state.md
       +-- parallel --> [Researcher B] (haiku) --> output/research/future_trends.md
       v
 [Writer]  (sonnet) --> output/draft.md
       v
 [Editor]  (opus, read-only!) --> feedback text
       v
 [Writer]  (re-invoked) --> output/final_post.md
```

## Quick Start

```bash
# 1. Install dependencies
pip install claude-agent-sdk python-dotenv

# 2. Set your API key
export ANTHROPIC_API_KEY=sk-ant-...

# 3. Run the pipeline
python examples/blog-pipeline/blog_pipeline.py "The future of renewable energy"
```

Expected cost: ~$0.05-0.20 per run (capped at $1.00).

## Subagent Patterns

### 1. Parallel Execution

Two researcher agents are launched in the **same orchestrator turn**, so they run simultaneously:

```python
# In blog_pipeline.py — the orchestrator's prompt instructs it to
# launch both researchers in a single message
"researcher": AgentDefinition(
    ...
    tools=["WebSearch", "WebFetch", "Write"],
    model="haiku",  # cheap & fast for parallel work
)
```

The orchestrator prompt (`prompts/orchestrator.txt`) explicitly says: *"Launch BOTH researchers in the SAME message to achieve parallel execution."*

### 2. Sequential Handoff

Each pipeline stage waits for the previous one to complete:

| Step | Agent | Waits for |
|------|-------|-----------|
| 1 | Researcher A + B (parallel) | — |
| 2 | Writer (draft) | Both researchers |
| 3 | Editor | Writer |
| 4 | Writer (revise) | Editor |

This is enforced by the orchestrator's step-by-step prompt — it only invokes the next agent after confirming the previous one completed.

### 3. Tool Restriction

Each agent gets only the tools it needs:

| Agent | Tools | Why |
|-------|-------|-----|
| Orchestrator | `Task` | Can only delegate, not act directly |
| Researcher | `WebSearch`, `WebFetch`, `Write` | Gather info, save notes |
| Writer | `Read`, `Glob`, `Write` | Read research, write posts |
| Editor | `Read`, `Glob` | **Read-only** — cannot modify files |

The editor physically cannot change the draft. Its feedback flows back through the orchestrator to the writer as text.

### 4. Model Differentiation

Different models for different jobs:

| Agent | Model | Rationale |
|-------|-------|-----------|
| Orchestrator | sonnet | Good reasoning for coordination |
| Researcher | haiku | Fast and cheap — great for web search tasks |
| Writer | sonnet | Balanced quality for long-form content |
| Editor | opus | Highest quality for nuanced editorial judgment |

## File Structure

```
examples/blog-pipeline/
├── blog_pipeline.py          # Main script (~200 lines)
├── prompts/
│   ├── orchestrator.txt      # Pipeline flow instructions
│   ├── researcher.txt        # Research specialist prompt
│   ├── writer.txt            # Blog writer prompt
│   └── editor.txt            # Read-only editor prompt
├── output/                   # Created at runtime (gitignored)
│   ├── research/
│   │   ├── current_state.md  # Researcher A output
│   │   └── future_trends.md  # Researcher B output
│   ├── draft.md              # First draft
│   └── final_post.md         # Revised final post
└── README.md
```

## Code Walkthrough

### `blog_pipeline.py`

**`build_agents()`** — Defines the four specialist agents using `AgentDefinition`. Each gets a restricted tool set, specific model, and system prompt loaded from `prompts/`.

**`build_orchestrator_options()`** — Configures the orchestrator with `allowed_tools=["Task"]` (can only delegate), registers the subagents, sets `permission_mode="bypassPermissions"` for autonomous execution, and caps cost at `$1.00`.

**`run_pipeline()`** — Streams messages from the orchestrator using `async for message in query(...)`, printing color-coded progress as each agent is invoked.

**`_verify_outputs()`** — Post-run check that all expected files were created.

## Extension Ideas

- **Fact-checker agent**: Add a read-only agent that verifies claims against sources before the final draft
- **SEO optimizer**: An agent that suggests title/meta-description improvements
- **Multi-topic batch**: Loop over several topics with shared research agents
- **Cost tracker**: Log per-agent costs from `ResultMessage` to compare model efficiency
- **Switch all models to haiku**: Set every agent to `model="haiku"` for cheaper development runs

## Troubleshooting

**WebSearch not available**: If your API key doesn't have web search enabled, the researchers will fall back to their built-in knowledge. The pipeline still works — you just won't get live web results.

**Import errors**: Make sure you've installed `claude-agent-sdk` (not `claude-code-sdk` or `anthropic`):
```bash
pip install claude-agent-sdk
```

**Cost concerns**: The `max_budget_usd=1.00` cap prevents runaway costs. For development, switch all models to `"haiku"` to minimize spend.
