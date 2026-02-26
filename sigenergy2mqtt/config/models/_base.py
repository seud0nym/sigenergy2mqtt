from pydantic import ConfigDict

# Every sub-model accepts both alias (YAML kebab key) and field name
_SUB = ConfigDict(populate_by_name=True)
