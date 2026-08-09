---
name: refactor
description: Refactor code safely step by step
type: prompt
---

When refactoring:
1. Read the file first. Understand what it does.
2. Identify the specific smell: duplication, long function, deep nesting, unclear naming, tight coupling.
3. Make ONE small change at a time using edit_file.
4. After each change, verify it still works (run tests if they exist, or run the relevant command).
5. Repeat until clean.

Do NOT rewrite entire files. Make targeted edits. Preserve behavior.
