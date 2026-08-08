---
name: typescript
description: TypeScript development with strict types and best practices
type: prompt
---

When writing TypeScript:
1. Use strict mode. Prefer `unknown` over `any`. Never use `any` unless absolutely necessary.
2. Define interfaces for data shapes. Use `type` for unions/intersections, `interface` for object shapes.
3. Use discriminated unions for state machines and variant types.
4. Leverage `as const` for literal types and readonly data.
5. Prefer `Record<K, V>` over `{ [key: string]: V }`.
6. Use generics to avoid code duplication, but don't over-abstract.
7. Handle null/undefined explicitly — use optional chaining and nullish coalescing.
8. Run `npx tsc --noEmit` after changes to catch type errors.

For existing projects:
- Read tsconfig.json first to understand the project's type strictness.
- Match existing patterns — if the project uses Zod schemas, use them too.
- Check for existing utility types before creating new ones.
