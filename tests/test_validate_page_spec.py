import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from validate_page_spec import validate_page_spec


DATA_DIR = Path(__file__).parent.parent / "data"
SCRIPT_PATH = Path(__file__).parent.parent / "scripts" / "validate_page_spec.py"


def test_valid_spec():
    spec_path = DATA_DIR / "page-spec.example.json"
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    is_valid, messages = validate_page_spec(spec)
    assert is_valid is True
    assert messages == []


def test_missing_version():
    spec = {
        "theme": {"id": "modern", "colors": {}, "fonts": {}},
        "layout": {},
        "components": [],
    }
    is_valid, messages = validate_page_spec(spec)
    assert is_valid is False
    assert any("version" in msg for msg in messages)


def test_invalid_component_type():
    spec = {
        "version": 1,
        "theme": {"id": "modern", "colors": {}, "fonts": {}},
        "layout": {},
        "components": [{"id": "bad", "type": "NotARealComponent"}],
    }
    is_valid, messages = validate_page_spec(spec)
    assert is_valid is False
    assert any("NotARealComponent" in msg for msg in messages)


def test_cli_missing_file():
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), str(DATA_DIR / "does-not-exist.json")],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "找不到" in result.stderr or "File" in result.stderr


def test_cli_invalid_json():
    invalid_json_path = DATA_DIR / "invalid.json"
    invalid_json_path.write_text("{not valid json", encoding="utf-8")
    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), str(invalid_json_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 3
        assert "JSON" in result.stderr
    finally:
        invalid_json_path.unlink(missing_ok=True)
