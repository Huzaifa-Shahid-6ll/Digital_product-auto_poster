# Directory Structure

```
Digital_product-auto_poster/
├── VISION.md              # Main business methodology document
├── .planning/
│   ├── config.json        # GSD workflow settings
│   └── codebase/          # Codebase mapping (auto-generated)
│       ├── STACK.md
│       ├── INTEGRATIONS.md
│       ├── ARCHITECTURE.md
│       ├── STRUCTURE.md
│       ├── CONVENTIONS.md
│       ├── TESTING.md
│       └── CONCERNS.md
├── .opencode/             # Opencode configuration
├── .gemini/               # Gemini CLI configuration
├── .claude/               # Claude Code configuration
├── .windsurf/             # WindSurf configuration
├── .codex/                # Codex configuration
├── .github/               # GitHub configuration
└── .agent/                # Agent configuration
```

## Key Locations

- Main content: `VISION.md`
- Planning config: `.planning/config.json`
- Workflow files: `.opencode/`, `.gemini/`, etc.

## Naming Conventions

- Configuration directories use dot-prefix (`.opencode`, `.gemini`, etc.)
- Markdown files use Title_Case (VISION.md)
- JSON files use lowercase (config.json)
