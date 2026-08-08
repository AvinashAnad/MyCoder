---
name: test
description: Write tests for code
type: prompt
---

When writing tests:
1. Read the source file to understand what to test.
2. Identify the testing framework already in use (look for existing test files, package.json, pyproject.toml, etc). Use the same framework.
3. Test the public interface, not internals.
4. Cover: happy path, edge cases (empty input, null, boundaries), and error cases.
5. Each test should be independent — no shared mutable state.
6. Use descriptive test names that say what behavior is expected.
7. Write the test file, then run the test suite to verify.
