---
name: playwright
description: Write and run Playwright end-to-end tests
type: prompt
---

When writing Playwright tests:

1. **Check setup first** — look for playwright.config.ts and existing test files.
2. **Use recommended patterns:**
   - Use `page.getByRole()`, `page.getByText()`, `page.getByLabel()` over CSS selectors.
   - Use `await expect(locator).toBeVisible()` for assertions.
   - Use `test.describe()` to group related tests.
   - One assertion per test when possible.
3. **Handle async properly:**
   - Always `await` page actions and assertions.
   - Use `waitForResponse` or `waitForURL` for navigation-dependent tests.
   - Use `page.waitForSelector()` sparingly — prefer auto-waiting locators.
4. **Test structure:**
   - Arrange: navigate and set up state.
   - Act: perform the user action.
   - Assert: verify the result.
5. **Run tests:** `npx playwright test` or `npx playwright test --ui` for the interactive runner.
6. **Debug failures:** `npx playwright test --debug` opens the inspector.

Keep tests independent. Don't share state between tests. Use `test.beforeEach` for common setup.
