import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from generate_page_spec import _pick_theme


def test_fantasy_theme():
    ui = {"genreKeywords": ["奇幻"], "styleKeywords": []}
    theme = _pick_theme(ui)
    assert theme["base"] == "fantasy"


def test_scifi_override():
    ui = {"genreKeywords": ["现代"], "styleKeywords": ["赛博朋克"]}
    theme = _pick_theme(ui)
    assert theme["base"] == "modern"
    assert theme["colors"]["primary"] == "#00f0ff"


def test_fallback_modern():
    ui = {"genreKeywords": [], "styleKeywords": []}
    theme = _pick_theme(ui)
    assert theme["base"] == "modern"
