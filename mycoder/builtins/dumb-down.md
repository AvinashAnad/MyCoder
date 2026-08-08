---
name: dumb-down
description: Explain code simply for beginners
type: prompt
---

Explain as if teaching someone who just started programming:

1. **No jargon without definition.** If you use a technical term, define it in parentheses the first time.
2. **Use analogies.** Compare code concepts to real-world things.
3. **One concept at a time.** Don't stack multiple new ideas in one sentence.
4. **Show, then explain.** Show a small code example first, then explain what each line does.
5. **Use simple language.** "This function takes a number and gives back a bigger number" not "This function accepts an integer parameter and returns an incremented value."
6. **Start with WHY before HOW.** Why does this code exist? What problem does it solve?
7. **Skip edge cases initially.** Teach the happy path first, mention complications after.

If the user asks a follow-up, go one level deeper, not sideways. Build on what you already explained.
