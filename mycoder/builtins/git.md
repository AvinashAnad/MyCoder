---
name: git
description: Git operations helper
type: prompt
---

For git operations:
- Always run `git status` before any destructive operation.
- Write clear commit messages: imperative mood, what changed and why.
- Prefer `git diff` to understand changes before committing.
- Never force-push to main/master without explicit confirmation.
- Stage specific files, not `git add .`, to avoid committing secrets or junk.
