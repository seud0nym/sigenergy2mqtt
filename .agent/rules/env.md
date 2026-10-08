---
trigger: always_on
---

# Environment Configuration
When executing Python commands, ALWAYS use the interpreter located at:
`.venv/bin/python` (or `.venv\Scripts\python.exe` on Windows).

Do not run `python` directly from the global path.

# Linting
Run linters on all code, unless just making documentation changes.

# Test Coverage
If not specified in any instructions, default behaviour should be to 
create or update test coverage for all code added or modified.

# Invoking pytest
When running pytest, always prefer to run with the `-n auto` option
unless single-threading is required to resolve test issues.
