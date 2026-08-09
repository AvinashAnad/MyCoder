---
name: fullstack
description: Full-stack development guidance across frontend, backend, and database
type: prompt
---

When working on a full-stack task:

## 1. Understand the stack
- Read package.json / pyproject.toml / go.mod to identify frameworks.
- Check for existing API patterns, auth setup, and database config.
- Identify the frontend framework (React, Vue, Svelte, etc.) and its conventions.

## 2. Work bottom-up
- **Database first** — define the schema or migration.
- **API next** — build the endpoint with validation and error handling.
- **Frontend last** — wire up the UI to the API.

## 3. Each layer should be testable independently
- Database: migration runs cleanly, seed data works.
- API: returns correct responses for valid and invalid inputs.
- Frontend: components render, user flows work end-to-end.

## 4. Integration checklist
- API contracts match between frontend and backend (field names, types, status codes).
- Error states are handled in the UI (loading, empty, error).
- Auth tokens are passed correctly through the stack.
- CORS is configured if frontend and backend are on different origins.
- Environment variables are set for all environments (dev, test, prod).

## 5. Don't forget
- Input validation at the API boundary — never trust the client.
- Database indexes for columns used in WHERE/JOIN/ORDER BY.
- Responsive design — test at mobile, tablet, and desktop widths.
