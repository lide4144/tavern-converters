#!/usr/bin/env python3
"""校验 page-spec.json 是否符合 schemas/page-spec.json。

Usage:
    python3 validate_page_spec.py <path-to-page-spec.json>
"""

import json
import sys
from pathlib import Path

import jsonschema


SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "page-spec.json"


def load_schema() -> dict:
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_page_spec(spec: dict) -> tuple[bool, list[str]]:
    """校验 page-spec 对象。

    Returns:
        (is_valid, error_messages)
    """
    schema = load_schema()
    validator = jsonschema.Draft7Validator(schema)
    errors = sorted(validator.iter_errors(spec), key=lambda e: e.json_path)
    if errors:
        messages = [f"{err.json_path}: {err.message}" for err in errors]
        return False, messages
    return True, []


def main():
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    try:
        with open(path, "r", encoding="utf-8") as f:
            spec = json.load(f)
    except FileNotFoundError:
        print(f"错误：找不到文件 {path}", file=sys.stderr)
        sys.exit(2)
    except PermissionError:
        print(f"错误：没有权限读取文件 {path}", file=sys.stderr)
        sys.exit(4)
    except json.JSONDecodeError as exc:
        print(f"错误：{path} 不是合法的 JSON（{exc}）", file=sys.stderr)
        sys.exit(3)

    is_valid, messages = validate_page_spec(spec)
    if is_valid:
        print("page-spec.json 校验通过")
        sys.exit(0)

    for msg in messages:
        print(msg)
    sys.exit(1)


if __name__ == "__main__":
    main()
