---
"llama-cloud-services": minor
---

feat: support zod v4 & v3

Adds support for zod v4 while maintaining backward compatibility with v3.

- Updated zod peer dependency to accept both v3 and v4: `^3.25.76 || ^4.0.0`
- Migrated all import statements to use `zod/v4` import path for compatibility
