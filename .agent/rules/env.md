---
trigger: always_on
---

# Environment Configuration
When executing Python commands, ALWAYS use the interpreter located at:
`.venv/bin/python` (or `.venv\Scripts\python.exe` on Windows).

Do not run `python` directly from the global path.

# Invoking pytest
When running pytest, always prefer to run with the `-n auto` option
unless single-threading is required to resolve test issues.