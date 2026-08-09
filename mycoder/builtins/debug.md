---
name: debug
description: Systematic debugging approach
type: prompt
---

Debug systematically:
1. **Reproduce** — Understand the exact error. Read the relevant file and any error output.
2. **Locate** — Search for the error message or failing function. Trace the call path.
3. **Hypothesize** — Form a specific theory about what's wrong.
4. **Verify** — Read the suspected code. Add a diagnostic command if needed (print, log, test).
5. **Fix** — Make the minimal change that fixes the root cause, not the symptom.
6. **Confirm** — Run the code or test again to verify the fix works.

Don't guess. Read the code. Trace the data flow.
