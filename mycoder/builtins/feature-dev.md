---
name: feature-dev
description: Structured 5-phase feature development workflow
type: prompt
---

Build features in 5 phases. Do not skip phases.

## Phase 1: Discovery
- Clarify the feature request. Ask what problem it solves if unclear.
- Identify constraints: performance, compatibility, deadline.

## Phase 2: Codebase exploration
- Search for similar existing features. Read their implementation.
- Map the architecture: where does this feature plug in?
- List the key files that will be touched.

## Phase 3: Clarifying questions
- Identify edge cases, error handling needs, and integration points.
- Ask the user about anything ambiguous BEFORE coding.

## Phase 4: Implementation
- Write tests first if a test framework exists.
- Implement in small incremental steps. Commit logically.
- Follow existing patterns and style.

## Phase 5: Verification
- Run the test suite.
- Check for regressions in related functionality.
- Summarize what was built, what changed, and any follow-up items.
