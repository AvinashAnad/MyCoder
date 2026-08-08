---
name: claude-md
description: Create and manage project CLAUDE.md documentation
type: prompt
---

CLAUDE.md is a project-level instruction file that AI coding tools read for context.

When creating or updating CLAUDE.md:

1. **Read the project first** — check package.json, pyproject.toml, Makefile, README, directory structure.
2. **Include these sections:**
   - Project description (one sentence)
   - Tech stack and key dependencies
   - Build/run/test commands
   - Code conventions (naming, style, patterns used)
   - Architecture overview (where things live)
   - Common pitfalls or gotchas
3. **Keep it concise** — under 200 lines. This is a reference, not documentation.
4. **Be specific** — "Use snake_case for Python functions" not "Follow good naming conventions."
5. **Update, don't rewrite** — when adding info, preserve what's already there.

Place at the project root. For monorepos, add per-package CLAUDE.md files too.
