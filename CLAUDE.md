# CLAUDE.md

## Translations

When a change adds or alters translatable strings (sensor names, attributes, options and so on), run `python3 scripts/update_en_translation.py` but **leave the resulting changes to `src/sigenergy2mqtt/translations/*.yaml` uncommitted**. Commit everything else as usual.

The maintainer then runs `scripts/translations`, which only calls DeepL (`scripts/translate_missing.py`) when `git diff` shows uncommitted translation changes. Committing the English placeholders makes it skip translation.
