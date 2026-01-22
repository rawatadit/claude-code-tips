# Custom Status Bar

Add a rich status bar showing model, git status, and context usage.

## Features

- Current model name
- Working directory
- Git branch, uncommitted files, sync status
- Context window usage (visual bar + percentage)

## Installation

**Requirements:** `jq` (`brew install jq` on macOS)

```bash
mkdir -p ~/.claude/scripts
curl -o ~/.claude/scripts/context-bar.sh https://raw.githubusercontent.com/rawatadit/claude-code-tips/main/scripts/context-bar.sh
chmod +x ~/.claude/scripts/context-bar.sh
```

Add to `~/.claude/settings.json`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "~/.claude/scripts/context-bar.sh"
  }
}
```

Restart Claude Code.

## Customization

Edit `~/.claude/scripts/context-bar.sh` and change `COLOR="blue"` to any of:

- gray
- orange
- blue (default)
- teal
- green
- lavender
- rose
- gold
- slate
- cyan
