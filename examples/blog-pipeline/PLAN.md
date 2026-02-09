# Multi-Agent Blog Post Pipeline

## Context

A learning project to explore Claude Agent SDK subagent patterns (parallel execution, sequential handoff, tool restriction, model differentiation) by building a pipeline of agents that collaborate to produce a blog post.

## Architecture

```
User provides topic
       │
       ▼
 [Orchestrator]  (sonnet, tools: Task only)
       │
       ├── parallel ──► [Researcher A] (haiku, tools: WebSearch/WebFetch/Write)
       │                      └── writes output/research/current_state.md
       ├── parallel ──► [Researcher B] (haiku, tools: WebSearch/WebFetch/Write)
       │                      └── writes output/research/future_trends.md
       ▼
 [Writer]  (sonnet, tools: Read/Glob/Write)
       └── reads research/, writes output/draft.md
       ▼
 [Editor]  (opus, tools: Read/Glob — read-only!)
       └── reads draft.md, returns feedback text
       ▼
 [Writer]  (re-invoked with editor feedback)
       └── writes output/final_post.md
```

## Key Patterns Demonstrated

| Pattern | How |
|---------|-----|
| **Sequential handoff** | research → write → edit → revise, each waits for the prior step |
| **Parallel execution** | Two researchers launched simultaneously by the orchestrator |
| **Tool restriction** | Editor has Read/Glob only — physically cannot modify files |
| **Model differentiation** | haiku (cheap research), sonnet (writing), opus (editorial judgment) |

## File Structure

```
examples/blog-pipeline/
├── blog_pipeline.py          # Main orchestrator script (~200 lines)
├── prompts/
│   ├── orchestrator.txt      # Pipeline flow instructions
│   ├── researcher.txt        # Research specialist prompt
│   ├── writer.txt            # Blog writer prompt
│   └── editor.txt            # Read-only editor prompt
├── output/                   # Runtime artifacts (gitignored)
│   └── .gitkeep
└── README.md                 # Learning guide
```

## Implementation Steps

### Step 1: Create directory structure
Create `prompts/` and `output/` subdirectories.

### Step 2: Write the 4 prompt files

- **`prompts/orchestrator.txt`** — Defines the 4-step pipeline: parallel research, write, edit, revise. Instructs the orchestrator to launch two researchers in the same turn for parallel execution.
- **`prompts/researcher.txt`** — Web search specialist. Find 3-5 sources, write structured notes to `output/research/`.
- **`prompts/writer.txt`** — Synthesizes research into an 800-1200 word blog post. Handles both initial drafting and revision based on editor feedback.
- **`prompts/editor.txt`** — Reviews draft against research notes. Returns numbered feedback only — cannot modify files.

### Step 3: Write `blog_pipeline.py`

The main script contains:

1. **Prompt loading** — Read `.txt` files from `prompts/` directory
2. **Agent definitions** — `AgentDefinition` for each role with:
   - Restricted `tools` list (least-privilege principle)
   - Specific `model` selection (cost/quality tradeoff)
   - `description` that tells the orchestrator when to use each agent
   - `prompt` loaded from the corresponding text file
3. **Orchestrator config** — `ClaudeAgentOptions` with:
   - `allowed_tools=["Task"]` — orchestrator can only delegate, not act directly
   - Registered agent definitions
   - `permission_mode="bypassPermissions"` for autonomous execution
   - `max_budget_usd=1.00` cost cap
4. **Message streaming** — `async for` loop printing pipeline progress:
   - Which agent is being delegated to
   - Tool calls being made
   - Final result and cost summary
5. **Entry point** — CLI arg for topic: `python blog_pipeline.py "Your topic"`

### Step 4: Write `README.md`

Learning guide that maps each code section to the subagent pattern it demonstrates, with:
- Run instructions
- Pattern-by-pattern walkthrough
- Expected output files
- Extension ideas (add a fact-checker agent, SEO optimizer, etc.)

### Step 5: Add `.gitignore`

Keep `output/.gitkeep` but ignore runtime artifacts (research notes, drafts, final posts).

### Step 6: Update root `README.md`

Add a row to the tips table linking to the blog-pipeline example.

## Agent Definitions Detail

### Orchestrator
- **Model**: sonnet
- **Tools**: `["Task"]` only
- **Role**: Coordinates the full pipeline. Its system prompt contains the step-by-step pipeline specification. It autonomously invokes subagents in the correct order.

### Researcher (x2, parallel)
- **Model**: haiku (fast, cheap — good for information extraction)
- **Tools**: `["WebSearch", "WebFetch", "Write"]`
- **Role**: Searches the web for information on assigned angle, writes structured notes to `output/research/`
- **Key constraint**: Cannot read other agents' output — focused solely on gathering new info

### Writer
- **Model**: sonnet (balanced quality/speed for long-form content)
- **Tools**: `["Read", "Glob", "Write"]`
- **Role**: Reads research notes, synthesizes into blog post. Invoked twice — once for initial draft, once for revision.
- **Key constraint**: Cannot search the web — works only from provided research

### Editor
- **Model**: opus (highest quality for nuanced editorial judgment)
- **Tools**: `["Read", "Glob"]` — **read-only**
- **Role**: Reviews draft against research notes, returns feedback as text
- **Key constraint**: Cannot modify any files — feedback flows back through the orchestrator to the writer

## Prerequisites

- **API key**: `export ANTHROPIC_API_KEY=...` (must have web search enabled for researchers)
- **Dependencies**: `pip install claude-agent-sdk python-dotenv`
- **Estimated cost**: ~$0.05-0.20 per run, capped at $1.00

## Verification

1. `pip install claude-agent-sdk python-dotenv` succeeds
2. Run: `python examples/blog-pipeline/blog_pipeline.py "The future of renewable energy"`
3. Console shows orchestrator delegating to researchers (in parallel), then writer, then editor, then writer again
4. `output/research/` contains 2 research note files
5. `output/draft.md` exists (first draft)
6. `output/final_post.md` exists (final revised post with editor feedback incorporated)
7. `final_post.md` is a coherent 800-1200 word blog post

## Notes

- The Claude Agent SDK is relatively new — we'll reference the latest docs during implementation and adjust API calls if needed.
- If WebSearch isn't available on your API key, researchers can be adapted to work with mock research notes for learning purposes.
- All models can be switched to `haiku` during development to minimize cost.
