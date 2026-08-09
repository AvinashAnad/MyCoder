---
name: context
description: Manage conversation context and reduce token usage
type: prompt
---

When context is getting long or the model seems to lose track:

1. **Summarize the conversation so far** — capture key decisions, files modified, and current state.
2. **Drop irrelevant history** — use /clear if the previous topic is unrelated to the current one.
3. **Be specific in requests** — "fix the bug on line 42 of app.py" uses fewer tokens than a vague description that requires clarification rounds.
4. **Read only what you need** — don't read entire large files when you only need a function.
5. **Batch related changes** — make all edits to one file in a single turn instead of spread across many.

Token-saving habits:
- Give file paths explicitly instead of asking the model to search.
- Paste error messages directly instead of describing them.
- Use /clear between unrelated tasks.
- Pick smaller, faster models for simple tasks (/model).
