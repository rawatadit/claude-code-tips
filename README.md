# Claude Code Tips & Tricks

A collection of tips, scripts, and configurations to enhance your Claude Code experience.

## Tips

### 1. Custom Status Bar

Add a rich status bar showing model, git status, and context usage.

![Status Bar Example](https://img.shields.io/badge/Opus_4.5_|_📁_myproject_|_🔀_main_(synced)_|_18%25_of_200k-blue)

**Features:**
- Current model name
- Working directory
- Git branch, uncommitted files, sync status
- Context window usage (visual bar + percentage)

**Install:**

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

**Customize color:** Edit the script and change `COLOR="blue"` to: gray, orange, teal, green, lavender, rose, gold, slate, or cyan.

**Requirements:** `jq` (install via `brew install jq` on macOS)

---

### 2. Keyboard Shortcuts

Essential shortcuts for faster navigation:

| Shortcut | Action |
|----------|--------|
| `Ctrl+C` | Cancel current request |
| `Ctrl+L` | Clear screen |
| `Escape` | Cancel current input |
| `Up/Down` | Navigate command history |

---

### 3. Useful Slash Commands

| Command | Description |
|---------|-------------|
| `/help` | Show all available commands |
| `/clear` | Clear conversation context |
| `/compact` | Summarize and compact conversation |
| `/memory` | View/edit persistent memory |
| `/config` | Open configuration |

---

### 4. Project Instructions

Create a `CLAUDE.md` file in your project root to give Claude context about your codebase:

```markdown
# Project Name

## Tech Stack
- Language/framework info

## Key Files
- Important file descriptions

## Conventions
- Coding style preferences
```

Claude automatically reads this file when working in your project.

---

## Contributing

Found a useful tip? PRs welcome!

## License

MIT
