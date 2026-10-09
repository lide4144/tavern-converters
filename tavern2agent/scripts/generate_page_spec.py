#!/usr/bin/env python3
"""从 card-ir.json 和 UI 语义生成 page-spec.json。

Usage:
    python3 generate_page_spec.py data/card-ir.json data/ui-semantics.json data/page-spec.json
"""

import copy
import json
import sys
from pathlib import Path


THEME_DEFAULTS = {
    "fantasy": {
        "id": "fantasy",
        "base": "fantasy",
        "colors": {
            "background": "#1a1510",
            "surface": "#2d2418",
            "primary": "#d4af37",
            "text": "#f3e5c8",
            "accent": "#8b0000",
        },
        "fonts": {"heading": "serif", "body": "serif"},
    },
    "scifi": {
        "id": "scifi",
        "base": "scifi",
        "colors": {
            "background": "#0a0a12",
            "surface": "#12121f",
            "primary": "#00f0ff",
            "text": "#e0f7ff",
            "accent": "#ff0055",
        },
        "fonts": {"heading": "sans-serif", "body": "monospace"},
    },
    "modern": {
        "id": "modern",
        "base": "modern",
        "colors": {
            "background": "#ffffff",
            "surface": "#f5f5f5",
            "primary": "#2563eb",
            "text": "#111827",
            "accent": "#db2777",
        },
        "fonts": {"heading": "sans-serif", "body": "sans-serif"},
    },
    "horror": {
        "id": "horror",
        "base": "horror",
        "colors": {
            "background": "#0c0c0c",
            "surface": "#1a1a1a",
            "primary": "#8b0000",
            "text": "#d4d4d4",
            "accent": "#4a0000",
        },
        "fonts": {"heading": "serif", "body": "sans-serif"},
    },
    "romance": {
        "id": "romance",
        "base": "romance",
        "colors": {
            "background": "#fff0f5",
            "surface": "#ffe4e1",
            "primary": "#e11d48",
            "text": "#4a0416",
            "accent": "#fb7185",
        },
        "fonts": {"heading": "serif", "body": "sans-serif"},
    },
}

GENRE_TO_THEME = {
    "奇幻": "fantasy",
    "科幻": "scifi",
    "现代": "modern",
    "恐怖": "horror",
    "恋爱": "romance",
}


def _pick_theme(ui: dict) -> dict:
    genres = ui.get("genreKeywords", [])
    styles = ui.get("styleKeywords", [])

    theme_id = "modern"
    for genre in genres:
        if genre in GENRE_TO_THEME:
            theme_id = GENRE_TO_THEME[genre]
            break

    theme = copy.deepcopy(THEME_DEFAULTS[theme_id])

    # 风格关键词覆盖
    style_overrides = {}
    if "赛博朋克" in styles and theme_id != "scifi":
        style_overrides = {"colors": {"primary": "#00f0ff", "accent": "#ff0055"}}
    elif "水彩" in styles:
        style_overrides = {"colors": {"background": "#fdfbf7", "surface": "#f7f3e8"}}
    elif "暗黑" in styles:
        style_overrides = {"colors": {"background": "#0c0c0c", "text": "#d4d4d4"}}

    if "colors" in style_overrides:
        theme["colors"].update(style_overrides["colors"])

    return theme


def _determine_complexity(ir: dict) -> str:
    mutable = ir.get("mutableConcepts", [])
    mechanics = ir.get("mechanics", [])
    if not mutable and not mechanics:
        return "prompt-only"
    if len(mutable) <= 2 and not any(m.get("formula") for m in mechanics):
        return "evented-light"
    return "evented-standard"


def _build_components(ir: dict, ui: dict, complexity: str, image_gen_enabled: bool) -> list[dict]:
    components = [
        {"id": "hero", "type": "Hero", "props": {"title": (ir.get("persona") or [{}])[0].get("name", "角色卡")}},
        {"id": "character", "type": "CharacterPanel", "props": {}},
    ]

    if complexity in ("evented-light", "evented-standard"):
        components.append({"id": "state", "type": "StatePanel", "props": {"readOnly": complexity == "evented-light"}})

    if complexity == "evented-standard":
        components.extend([
            {"id": "actions", "type": "ActionBar", "props": {}},
            {"id": "log", "type": "SceneLog", "props": {}},
        ])

    if image_gen_enabled:
        components.append({"id": "imageGen", "type": "ImageGenButton", "props": {}})
        components.append({"id": "gallery", "type": "Gallery", "props": {}})

    return components


def _build_image_gen_config(ui: dict) -> dict | None:
    rules = ui.get("imageGenRules", {})
    if not rules.get("driverMode") and not ui.get("rawSignals", {}).get("hasPicTag"):
        return None

    return {
        "enabled": False,  # 默认关闭，需要用户显式开启
        "provider": "comfyui",
        "endpoint": "http://127.0.0.1:8188",
        "modelType": "sd",
        "workflow": "workflows/comfyui-sd.json",
        "promptTemplate": "templates/comfyui-prompt-sd.txt",
        "promptNodeId": "3",
        "basePrompt": "masterpiece, best quality, highly detailed",
        "negativePrompt": "worst quality, low quality, blurry",
        "outputDir": "web/public/generated",
        "triggers": {
            "eventDriven": rules.get("eventDrivenTriggers", []),
            "stateDriven": rules.get("stateDrivenTriggers", []),
            "multiAngleFallback": rules.get("multiAngleTriggers", []),
        },
    }


def generate_page_spec(ir: dict, ui: dict) -> dict:
    complexity = _determine_complexity(ir)
    image_gen = _build_image_gen_config(ui)

    spec = {
        "version": 1,
        "source": {
            "cardName": (ir.get("persona") or [{}])[0].get("name", "角色卡"),
            "archetype": ir.get("source", {}).get("archetype", "unknown"),
            "complexity": complexity,
        },
        "theme": _pick_theme(ui),
        "layout": {
            "hero": True,
            "sidebar": complexity == "evented-standard",
            "tabs": ["剧情", "状态", "图库"] if image_gen else ["剧情", "状态"],
        },
        "components": _build_components(ir, ui, complexity, bool(image_gen)),
        "allowedTools": ["generate_image"] if image_gen else [],
        "stateProjection": {
            "visiblePaths": ["scene", "protagonist", "relationship", "economy"],
        },
    }
    if image_gen is not None:
        spec["imageGen"] = image_gen
    return spec


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    ir_path = sys.argv[1]
    ui_path = sys.argv[2]
    out_path = sys.argv[3] if len(sys.argv) > 3 else None

    try:
        with open(ir_path, "r", encoding="utf-8") as f:
            ir = json.load(f)
    except FileNotFoundError:
        print(f"Error: input file not found: {ir_path}", file=sys.stderr)
        sys.exit(2)
    except json.JSONDecodeError as exc:
        print(f"Error: invalid JSON in {ir_path}: {exc}", file=sys.stderr)
        sys.exit(3)

    try:
        with open(ui_path, "r", encoding="utf-8") as f:
            ui = json.load(f)
    except FileNotFoundError:
        print(f"Error: input file not found: {ui_path}", file=sys.stderr)
        sys.exit(2)
    except json.JSONDecodeError as exc:
        print(f"Error: invalid JSON in {ui_path}: {exc}", file=sys.stderr)
        sys.exit(3)

    spec = generate_page_spec(ir, ui)

    if out_path:
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(spec, f, ensure_ascii=False, indent=2)
            print(f"Saved to {out_path}")
        except OSError as exc:
            print(f"Error: failed to write {out_path}: {exc}", file=sys.stderr)
            sys.exit(4)
    else:
        print(json.dumps(spec, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
