import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from extract_ui_semantics import extract_ui_semantics


REQUIRED_TOP_LEVEL_KEYS = {
    "version",
    "genreKeywords",
    "styleKeywords",
    "uiPanels",
    "imageGenRules",
    "rawSignals",
}


def test_extracts_genre_and_style():
    card = {
        "data": {
            "name": "艾莉娅",
            "description": "一个来自魔法学院的少女，生活在奇幻世界中。",
            "scenario": "你在古老的图书馆遇见她，周围是漂浮的魔法书。",
            "creator_notes": "视觉风格：水彩、柔和、梦幻",
            "personality": "温柔、好奇",
            "first_mes": "你好，欢迎来到星辉图书馆。",
        }
    }
    result = extract_ui_semantics(card)
    assert "奇幻" in result["genreKeywords"]
    assert "水彩" in result["styleKeywords"]


def test_extracts_image_gen_rules():
    card = {
        "data": {
            "creator_notes": "【驱动模式】节点驱动：场景切换、姿势改变时触发。",
            "description": "<pic>角色立绘</pic>\n红发绿眼的少女。"
        }
    }
    result = extract_ui_semantics(card)
    assert result["imageGenRules"]["driverMode"] == ["event-driven"]
    assert "场景切换" in result["imageGenRules"]["eventDrivenTriggers"]


def test_no_ui_panels():
    card = {"data": {"description": "简单的角色设定。"}}
    result = extract_ui_semantics(card)
    assert result["uiPanels"] == []


def test_top_level_fields_without_data_key():
    card = {
        "description": "魔法学院的学生，使用剑与魔法。",
        "creator_notes": "风格：赛博朋克、像素",
    }
    result = extract_ui_semantics(card)
    assert "奇幻" in result["genreKeywords"]
    assert "赛博朋克" in result["styleKeywords"]
    assert "像素" in result["styleKeywords"]


def test_html_panel_extraction():
    card = {
        "data": {
            "description": (
                '<div class="status">HP: 100/100 好感度: 50 金钱: 1000</div>'
                '<div>普通说明文字</div>'
            )
        }
    }
    result = extract_ui_semantics(card)
    assert len(result["uiPanels"]) == 1
    assert result["uiPanels"][0]["type"] == "html_panel"
    assert "HP" in result["uiPanels"][0]["snippet"]


def test_multiple_driver_modes():
    card = {
        "data": {
            "creator_notes": "节点驱动：场景切换时触发。情境驱动：角色描写时触发。",
        }
    }
    result = extract_ui_semantics(card)
    assert "event-driven" in result["imageGenRules"]["driverMode"]
    assert "state-driven" in result["imageGenRules"]["driverMode"]


def test_empty_card_fields_fallback():
    card = {"data": {}}
    result = extract_ui_semantics(card)
    assert result["genreKeywords"] == ["现代"]
    assert result["styleKeywords"] == []
    assert result["uiPanels"] == []
    assert result["imageGenRules"]["driverMode"] == []
    assert result["rawSignals"] == {"hasPicTag": False, "hasHtmlPanel": False}


def test_forbidden_word_boundary_detection():
    card = {
        "data": {
            "description": "I know some information about this character.",
            "creator_notes": "Do not use explicit content. no NSFW, without violence, none of that.",
        }
    }
    result = extract_ui_semantics(card)
    forbidden = result["imageGenRules"]["forbiddenWords"]
    assert "no" in forbidden
    assert "without" in forbidden
    assert "none" in forbidden
    assert "know" not in forbidden
    assert "information" not in forbidden


def test_output_contract_has_required_top_level_keys():
    card = {"data": {"description": "一个现代校园恋爱故事。"}}
    result = extract_ui_semantics(card)
    assert set(result.keys()) == REQUIRED_TOP_LEVEL_KEYS
    assert isinstance(result["version"], int)
    assert isinstance(result["genreKeywords"], list)
    assert isinstance(result["styleKeywords"], list)
    assert isinstance(result["uiPanels"], list)
    assert isinstance(result["imageGenRules"], dict)
    assert isinstance(result["rawSignals"], dict)
