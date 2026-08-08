---
name: github
description: GitHub operations — PRs, issues, actions, and workflows
type: prompt
---

For GitHub operations, use the `gh` CLI and git commands:

**Pull Requests:**
- Create: `gh pr create --title "..." --body "..."`
- List: `gh pr list`
- View: `gh pr view <number>`
- Review: `gh pr diff <number>`
- Merge: `gh pr merge <number>`

**Issues:**
- Create: `gh issue create --title "..." --body "..."`
- List: `gh issue list`
- Close: `gh issue close <number>`

**Actions/CI:**
- View runs: `gh run list`
- View logs: `gh run view <run-id> --log`
- Re-run: `gh run rerun <run-id>`

**Workflow:**
1. Always check `git status` and `git branch` first.
2. Create a feature branch: `git checkout -b feature/name`
3. Make changes, commit with clear messages.
4. Push and create PR: `git push -u origin HEAD && gh pr create`
5. Check CI status: `gh pr checks`

When reviewing PRs, read the diff with `gh pr diff` and check for the issues in the /review skill.
