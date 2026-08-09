---
name: skill-creator
description: Create new OpenCode skills
type: prompt
---

To create a new skill:

1. **Define the purpose** — what specific task does this skill guide? One skill = one job.
2. **Choose the type:**
   - `always` — runs on every prompt (use sparingly, costs context tokens)
   - `prompt` — activated with /skillname (most skills should be this)
3. **Write the skill file** at `~/.opencode/skills/my-skill.md`:

```markdown
---
name: my-skill
description: One-line description of what it does
type: prompt
---

Clear, actionable instructions here.
Numbered steps work best for procedures.
Bullet points for checklists.
Keep it under 50 lines — models have limited context.
```

4. **Test it** — run `/reload` then `/my-skill` with a real task.
5. **Iterate** — if the model ignores parts, make those instructions shorter and more direct.

**Guidelines:**
- Be specific. "Check for SQL injection" beats "review security."
- Use imperative mood. "Read the file" not "You should read the file."
- Don't repeat what the base system prompt already says.
- Shorter is better. Every token of skill text is context the model can't use for your actual task.
