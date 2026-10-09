#!/usr/bin/env python3
"""从 SillyTavern 角色卡中提取 UI 相关语义。

Usage:
    python3 extract_ui_semantics.py card.json ui-semantics.json
"""

import json
import re
import sys


GENRE_KEYWORDS = {
    "奇幻": ["魔法", "剑与魔法", "法师", "龙", "地下城", "中世纪", "魔导"],
    "科幻": ["未来", "太空", "机甲", "赛博朋克", "星际", "AI", "机器人"],
    "现代": ["校园", "都市", "日常", "职场", "现代"],
    "恐怖": ["恐怖", "灵异", "丧尸", "克苏鲁", "黑暗", "惊悚"],
    "恋爱": ["恋爱", "约会", "告白", "情侣", "甜宠"],
}

STYLE_KEYWORDS = [
    "赛博朋克", "水彩", "像素", "暗黑", "梦幻", "复古", "蒸汽朋克",
    "极简", "日系", "欧美", "写实", "二次元"
]

DRIVER_MODE_PATTERNS = {
    "event-driven": ["节点驱动", "事件驱动", "场景切换", "姿势改变"],
    "state-driven": ["情境驱动", "状态驱动", "角色描写"],
    "multi-angle": ["多视角", "多视角绘图"],
}

EVENT_TRIGGERS = ["场景切换", "姿势改变", "高潮", "射精", "战斗开始", "战斗结束"]
STATE_TRIGGERS = ["角色描写", "情绪延续", "特写", "环境描写"]
MULTI_ANGLE_TRIGGERS = ["环境镜头", "POV", "细节特写", "后果延续"]


def _detect_genre(text: str) -> list[str]:
    """根据关键词匹配文本中的题材/类型标签。"""
    text_lower = text.lower()
    genres = []
    for genre, keywords in GENRE_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            genres.append(genre)
    return genres or ["现代"]


def _detect_style(text: str) -> list[str]:
    """根据关键词匹配文本中的视觉风格标签。"""
    styles = [kw for kw in STYLE_KEYWORDS if kw in text]
    return styles


def _extract_ui_panels(text: str) -> list[dict]:
    """从文本中提取可能的 HTML 面板片段。"""
    panels = []
    # 简单检测 HTML 面板片段
    for match in re.finditer(r"<div[^>]*>(.*?)</div>", text, re.S):
        content = match.group(1)
        if any(kw in content for kw in ["HP", "好感度", "金钱", "状态", "level"]):
            panels.append({"type": "html_panel", "snippet": content[:200]})
    return panels


def _extract_image_gen_rules(text: str) -> dict:
    """从文本中提取图像生成规则（驱动模式、触发器、禁用词、固定属性）。"""
    rules = {
        "driverMode": [],
        "eventDrivenTriggers": [],
        "stateDrivenTriggers": [],
        "multiAngleTriggers": [],
        "forbiddenWords": [],
        "fixedAttributes": [],
    }
    text_lower = text.lower()

    for mode, patterns in DRIVER_MODE_PATTERNS.items():
        if any(p in text for p in patterns):
            rules["driverMode"].append(mode)

    for trigger in EVENT_TRIGGERS:
        if trigger in text:
            rules["eventDrivenTriggers"].append(trigger)

    for trigger in STATE_TRIGGERS:
        if trigger in text:
            rules["stateDrivenTriggers"].append(trigger)

    for trigger in MULTI_ANGLE_TRIGGERS:
        if trigger in text:
            rules["multiAngleTriggers"].append(trigger)

    # prompt 净化规则：使用单词边界匹配独立英文单词
    forbidden_words = ["no", "without", "none"]
    found_forbidden = [
        word for word in forbidden_words
        if re.search(rf"\b{re.escape(word)}\b", text_lower)
    ]
    rules["forbiddenWords"].extend(found_forbidden)

    # 固定属性
    fixed_attr_patterns = ["发色", "肤色", "眼睛颜色", "胸部大小", "身材"]
    for attr in fixed_attr_patterns:
        if attr in text:
            rules["fixedAttributes"].append(attr)

    return rules


def extract_ui_semantics(card: dict) -> dict:
    """从 SillyTavern 角色卡字典中提取 UI 相关语义。"""
    data = card.get("data", card)

    combined_text = "\n".join(
        str(data.get(k, "")) for k in [
            "description", "personality", "scenario", "first_mes",
            "creator_notes", "system_prompt", "post_history_instructions"
        ]
    )

    return {
        "version": 1,
        "genreKeywords": _detect_genre(combined_text),
        "styleKeywords": _detect_style(combined_text),
        "uiPanels": _extract_ui_panels(combined_text),
        "imageGenRules": _extract_image_gen_rules(combined_text),
        "rawSignals": {
            "hasPicTag": "<pic>" in combined_text,
            "hasHtmlPanel": "<div" in combined_text,
        },
    }


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    card_path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        with open(card_path, "r", encoding="utf-8") as f:
            card = json.load(f)
    except FileNotFoundError:
        print(f"Error: file not found: {card_path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: invalid JSON in {card_path}: {e}", file=sys.stderr)
        sys.exit(1)

    semantics = extract_ui_semantics(card)

    if out_path:
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(semantics, f, ensure_ascii=False, indent=2)
            print(f"Saved to {out_path}")
        except OSError as e:
            print(f"Error: could not write to {out_path}: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(json.dumps(semantics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
