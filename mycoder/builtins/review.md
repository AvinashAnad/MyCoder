---
name: review
description: Code review checklist
type: prompt
---

Review the code for these issues, in order of severity:

1. **Correctness** — Logic errors, off-by-one, null/undefined access, race conditions.
2. **Security** — Injection (SQL, command, XSS), hardcoded secrets, path traversal, unsafe deserialization.
3. **Error handling** — Unhandled exceptions, silent failures, missing validation at boundaries.
4. **Performance** — N+1 queries, unnecessary allocations, blocking in async code.
5. **Readability** — Unclear names, unnecessary complexity, missing context for non-obvious logic.

Read the file(s) first. Report findings with file path, line number, severity, and a fix. Skip categories with no issues.
