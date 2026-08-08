---
name: ralph-loop
description: Iterative development loop — keep working until done
type: prompt
---

Work in an iterative loop until the task is complete:

1. **Understand the goal.** State what "done" looks like before starting.
2. **Make one change.**
3. **Verify it works** — run tests, check output, read the result.
4. **If not done, go to step 2.**
5. **When done, summarize** what was built and what was changed.

Rules for the loop:
- Each iteration should make measurable progress.
- If stuck for 2 iterations on the same issue, change approach.
- Run tests after every meaningful change.
- Commit working checkpoints so you can revert if needed.
- Maximum 15 iterations. If not done by then, summarize remaining work.

This is useful for:
- Building a feature end-to-end
- Fixing a chain of related bugs
- Iterating on test failures until all pass
- Refactoring step by step with tests as guardrails
