---
name: security-guidance
description: Security review checklist for code changes
type: prompt
---

Scan the code for these vulnerability classes, in order:

1. **Injection** — SQL, command, LDAP, XPath. Any user input reaching a query or shell without parameterization.
2. **XSS** — Raw innerHTML, unescaped template output, dangerouslySetInnerHTML with user data.
3. **SSRF** — User-controlled URLs passed to HTTP clients without allowlist.
4. **Hardcoded secrets** — API keys, passwords, tokens in source. Check .env files aren't committed.
5. **Path traversal** — User input in file paths without sanitization (../ attacks).
6. **Unsafe deserialization** — pickle.load, yaml.load (without SafeLoader), eval() on user data.
7. **Auth bypass** — Missing auth checks on endpoints, IDOR (direct object references without ownership validation).
8. **Dependency risks** — Known vulnerable versions, typosquatting package names.

For each finding: state the file, line, vulnerability class, and a concrete fix.
If no issues found, say so explicitly.
