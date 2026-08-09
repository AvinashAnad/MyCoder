---
name: superpowers
description: Agentic development framework — brainstorm, plan, build, verify
type: prompt
---

Follow this workflow for any non-trivial task:

## 1. Brainstorm before building
- Ask what the user is really trying to do, not just what they asked for.
- Propose 2-3 approaches with tradeoffs and a recommendation.
- Get approval before writing code.

## 2. Plan before coding
- List every file that will be created or modified.
- Break work into small tasks, each independently testable.
- Each task: [what to do] → [how to verify].

## 3. Test-driven development
- Write the test first. Watch it fail. Write minimal code to pass.
- If you wrote code without a failing test, delete it and start over.
- No exceptions for "simple" changes.

## 4. Systematic debugging
- Never guess. Find root cause before proposing fixes.
- Phase 1: Reproduce the issue reliably.
- Phase 2: Locate the failing code path.
- Phase 3: Hypothesize, verify with evidence, then fix.
- Phase 4: Confirm the fix and check for regressions.

## 5. Verify before declaring done
- Run the full test suite.
- Check that the original requirement is actually met, not just that tests pass.
- Look for regressions in related functionality.
