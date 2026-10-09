"""Tests for the page-spec JSON Schema."""

import json
import pathlib

import jsonschema
import pytest

SCHEMA_PATH = pathlib.Path(__file__).resolve().parent.parent / "schemas" / "page-spec.json"


@pytest.fixture(scope="module")
def schema():
    with SCHEMA_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def _minimal_valid_spec():
    return {
        "version": 1,
        "source": {
            "cardName": "Test Card",
            "archetype": "protagonist",
            "complexity": "prompt-only",
        },
        "theme": {
            "id": "default",
            "colors": {
                "background": "#000000",
                "surface": "#111111",
                "primary": "#ffffff",
                "text": "#ffffff",
                "accent": "#ff00ff",
            },
            "fonts": {
                "heading": "sans-serif",
                "body": "sans-serif",
            },
        },
        "layout": {
            "hero": True,
            "sidebar": False,
            "tabs": ["剧情"],
        },
        "components": [
            {"id": "hero", "type": "Hero", "props": {"title": "Test Card"}},
            {"id": "character", "type": "CharacterPanel", "props": {}},
            {"id": "opening", "type": "OpeningScene", "props": {}},
        ],
    }


def test_valid_page_spec_passes(schema):
    """A minimal valid page spec should validate successfully."""
    jsonschema.validate(_minimal_valid_spec(), schema)


def test_missing_version_fails(schema):
    """Missing required 'version' should fail validation."""
    spec = _minimal_valid_spec()
    del spec["version"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(spec, schema)


def test_unknown_complexity_fails(schema):
    """Unknown 'complexity' value in source should fail validation."""
    spec = _minimal_valid_spec()
    spec["source"]["complexity"] = "invalid-complexity"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(spec, schema)


@pytest.mark.parametrize("bad_version", ["1", 2], ids=["string", "wrong-const"])
def test_invalid_version_fails(schema, bad_version):
    """'version' must be an integer equal to the schema's const value."""
    spec = _minimal_valid_spec()
    spec["version"] = bad_version
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(spec, schema)


def test_missing_theme_id_fails(schema):
    """Missing required 'theme.id' should fail validation."""
    spec = _minimal_valid_spec()
    del spec["theme"]["id"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(spec, schema)


def test_invalid_image_gen_model_type_fails(schema):
    """An unknown 'imageGen.modelType' enum value should fail validation."""
    spec = _minimal_valid_spec()
    spec["imageGen"] = {
        "enabled": True,
        "modelType": "unsupported-model",
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(spec, schema)


def test_missing_component_id_fails(schema):
    """A component without required 'id' should fail validation."""
    spec = _minimal_valid_spec()
    spec["components"].append({"type": "Hero", "props": {}})
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(spec, schema)


def test_unknown_component_type_fails(schema):
    """An unknown component 'type' should fail validation."""
    spec = _minimal_valid_spec()
    spec["components"].append({"id": "unknown", "type": "UnknownComponent", "props": {}})
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(spec, schema)
