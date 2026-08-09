---
name: simplify
description: Simplify and reduce code complexity
type: prompt
---

Review the code and simplify it:

1. **Read the file first.** Understand what it does before changing anything.
2. **Remove dead code** — unused imports, unreachable branches, commented-out blocks.
3. **Flatten nesting** — use early returns, guard clauses, and extract helpers to reduce indentation depth.
4. **Reduce duplication** — if 3+ lines repeat, extract a function. But don't abstract prematurely.
5. **Simplify conditionals** — replace complex boolean logic with named variables or helper functions.
6. **Use language idioms** — list comprehensions (Python), destructuring (JS/TS), pattern matching where available.
7. **Shorten names only if clearer** — `get_user_by_id` is fine, `getUserFromDatabaseById` is not.
8. **Remove unnecessary abstractions** — if a wrapper just calls through to one thing, remove it.

After each change, verify the code still works. Make one kind of simplification at a time.

Target: same behavior, fewer lines, less nesting, clearer intent.
