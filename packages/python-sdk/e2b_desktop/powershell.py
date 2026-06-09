import json
from typing import Any


def ps_single_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def ps_json(value: Any) -> str:
    return f"({ps_single_quote(json.dumps(value))} | ConvertFrom-Json)"
