import json
import sys
from pathlib import Path

import jsonschema
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from generate_page_spec import generate_page_spec


@pytest.fixture(scope="module")
def schema():
    schema_path = Path(__file__).parent.parent / "schemas" / "page-spec.json"
    return json.loads(schema_path.read_text(encoding="utf-8"))


def test_generates_modern_theme_by_default():
    ir = {
        "version": 1,
        "persona": [{"name": "艾莉娅"}],
        "settingFacts": [],
        "mutableConcepts": [],
        "style": {"tone": "gentle"},
    }
    ui = {"version": 1, "genreKeywords": [], "styleKeywords": [], "uiPanels": [], "imageGenRules": {}}
    spec = generate_page_spec(ir, ui)
    assert spec["theme"]["base"] == "modern"
    assert any(c["type"] == "CharacterPanel" for c in spec["components"])


def test_romance_theme():
    ir = {"version": 1, "persona": [{"name": "艾莉娅"}], "mutableConcepts": [], "style": {}}
    ui = {"version": 1, "genreKeywords": ["恋爱"], "styleKeywords": [], "uiPanels": [], "imageGenRules": {}}
    spec = generate_page_spec(ir, ui)
    assert spec["theme"]["base"] == "romance"


def test_fantasy_theme():
    ir = {"version": 1, "persona": [{"name": "法师"}], "mutableConcepts": [], "style": {}}
    ui = {"version": 1, "genreKeywords": ["奇幻"], "styleKeywords": [], "uiPanels": [], "imageGenRules": {}}
    spec = generate_page_spec(ir, ui)
    assert spec["theme"]["base"] == "fantasy"


def test_evented_standard_adds_action_bar():
    ir = {
        "version": 1,
        "persona": [{"name": "战士"}],
        "mutableConcepts": [{"name": "hp"}, {"name": "mp"}, {"name": "gold"}],
        "style": {},
    }
    ui = {"version": 1, "genreKeywords": ["奇幻"], "styleKeywords": [], "uiPanels": [], "imageGenRules": {}}
    spec = generate_page_spec(ir, ui)
    assert any(c["type"] == "StatePanel" for c in spec["components"])
    assert any(c["type"] == "ActionBar" for c in spec["components"])


def test_evented_light_is_read_only():
    ir = {
        "version": 1,
        "persona": [{"name": "旅人"}],
        "mutableConcepts": [{"name": "mood"}],
        "mechanics": [],
        "style": {},
    }
    ui = {"version": 1, "genreKeywords": [], "styleKeywords": [], "uiPanels": [], "imageGenRules": {}}
    spec = generate_page_spec(ir, ui)
    assert spec["source"]["complexity"] == "evented-light"
    component_types = [c["type"] for c in spec["components"]]
    assert "StatePanel" in component_types
    assert "ActionBar" not in component_types
    assert "SceneLog" not in component_types
    state_panel = next(c for c in spec["components"] if c["type"] == "StatePanel")
    assert state_panel["props"]["readOnly"] is True


def test_image_gen_enabled_path():
    ir = {
        "version": 1,
        "persona": [{"name": "画师"}],
        "mutableConcepts": [],
        "style": {},
    }
    ui = {
        "version": 1,
        "genreKeywords": [],
        "styleKeywords": [],
        "uiPanels": [],
        "imageGenRules": {"driverMode": "manual"},
    }
    spec = generate_page_spec(ir, ui)
    assert "imageGen" in spec
    assert spec["imageGen"]["enabled"] is False
    component_types = [c["type"] for c in spec["components"]]
    assert "ImageGenButton" in component_types
    assert "Gallery" in component_types
    assert "generate_image" in spec["allowedTools"]


@pytest.mark.parametrize(
    "genre,expected_theme,mutable,image_gen_enabled",
    [
        ([], "modern", [], False),
        (["恋爱"], "romance", [], False),
        (["奇幻"], "fantasy", [], False),
        (["奇幻"], "fantasy", [{"name": "hp"}, {"name": "mp"}, {"name": "gold"}], False),
    ],
)
def test_generated_spec_matches_schema(schema, genre, expected_theme, mutable, image_gen_enabled):
    ir = {"version": 1, "persona": [{"name": "测试角色"}], "mutableConcepts": mutable, "style": {}}
    ui = {"version": 1, "genreKeywords": genre, "styleKeywords": [], "uiPanels": [], "imageGenRules": {}}
    spec = generate_page_spec(ir, ui)
    jsonschema.validate(spec, schema)
    assert spec["theme"]["base"] == expected_theme
    assert ("imageGen" in spec) is image_gen_enabled


def test_empty_persona_fallback():
    ir = {"version": 1, "persona": [], "mutableConcepts": [], "style": {}}
    ui = {"version": 1, "genreKeywords": [], "styleKeywords": [], "uiPanels": [], "imageGenRules": {}}
    spec = generate_page_spec(ir, ui)
    assert spec["source"]["cardName"] == "角色卡"
    hero = next(c for c in spec["components"] if c["type"] == "Hero")
    assert hero["props"]["title"] == "角色卡"
