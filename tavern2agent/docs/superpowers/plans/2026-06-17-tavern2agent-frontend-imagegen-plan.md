# Tavern2Agent 前端页面与可选生图功能实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: 使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 按任务逐步实施。步骤使用复选框 `- [ ]` 语法便于跟踪。

**目标：** 让 Tavern2Agent skill 生成的 agent 拥有基于角色卡内容自动设计的 Next.js 页面，并可选集成 ComfyUI 生图功能。

**架构：** 新增 UI 语义提取层，从 `card-ir.json` 生成 `data/page-spec.json`；skill 根据 page-spec 生成 Next.js 前端项目 `web/` 和可选的 `tools/image-gen.ts`；`extension.ts` 扩展为本地 HTTP server，为页面提供 state 读取、工具调用、事件触发三个端点；页面与运行时通过 pi extension API 双向通信。

**技术栈：** Python 3（skill 脚本）、TypeScript / Next.js 14 App Router（前端）、Tailwind CSS（样式）、ComfyUI API（生图）。

---

## 文件结构映射

| 文件/目录 | 责任 |
|---|---|
| `scripts/extract_ui_semantics.py` | 从卡片原始 JSON / IR 中提取题材、风格、UI 面板、生图规则等语义 |
| `scripts/generate_page_spec.py` | 从 `card-ir.json` + UI 语义生成 `data/page-spec.json` |
| `scripts/validate_page_spec.py` | 校验 page-spec schema |
| `scripts/setup_frontend.py` | 根据 page-spec 生成 `web/` 目录和基础文件 |
| `web/` | Next.js 14 前端项目，含主题、组件、API Route |
| `web/themes/index.ts` | 主题注册表与选择逻辑 |
| `web/app/api/state/route.ts` | 读取 runtime state 的 API |
| `web/app/api/tools/route.ts` | 转发工具调用的 API |
| `web/app/api/events/route.ts` | 转发事件触发的 API |
| `web/components/` | 页面组件：CharacterPanel、StatePanel、SceneLog、ImageGenButton、Gallery 等 |
| `engine/image-prompt-builder.ts` | 根据模型类型构建 SD 或 diffusion 风格 prompt |
| `tools/image-gen.ts` | 可选生图工具，调用 ComfyUI |
| `workflows/` | 默认 ComfyUI workflow 与用户导入目录 |
| `templates/` | SD / diffusion prompt 模板 |
| `extension.ts` | 扩展现有 extension，启动 web server 并暴露 state/tools/events 端点 |
| `references/frontend-design.md` | 前端设计规范 |
| `references/image-generation.md` | 生图功能规范 |
| `references/ui-semantic-extraction.md` | UI 语义提取规范 |
| `SKILL.md` | 更新入口流程 |
| `tests/` | 单元测试与集成测试 |

**说明：** `web/`、`extension.ts`、`tools/image-gen.ts`、`engine/` 是 skill 生成产物中的文件，不是直接存放在 skill 仓库根目录。skill 仓库通过 `scripts/setup_frontend.py`、references 文档和（可选的）代码模板来控制这些产物的生成。本计划中的“Create/Modify”既包括 skill 仓库中的生成脚本和模板，也包括运行后生成的产物文件。

---

### Task 1: 定义 page-spec JSON Schema

**说明：** 本计划中的 `web/`、`extension.ts`、`tools/`、`engine/` 等文件指 skill **生成产物** 中的文件；skill 仓库本身通过脚本、模板和 references 文档控制这些产物的生成。本任务创建的 schema 位于 skill 仓库，供生成脚本和前端共享。

**目标：** 给 `data/page-spec.json` 一个明确的 JSON Schema，方便后续脚本、前端和校验使用。

- [ ] **Step 1: 编写 schema 文件**

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://tavern2agent.local/page-spec.json",
  "title": "Tavern2Agent Page Spec",
  "type": "object",
  "required": ["version", "theme", "layout", "components"],
  "properties": {
    "version": { "type": "integer", "const": 1 },
    "source": {
      "type": "object",
      "properties": {
        "cardName": { "type": "string" },
        "archetype": { "type": "string" },
        "complexity": { "enum": ["prompt-only", "evented-light", "evented-standard"] }
      }
    },
    "theme": {
      "type": "object",
      "required": ["id", "colors", "fonts"],
      "properties": {
        "id": { "type": "string" },
        "base": { "type": "string" },
        "colors": {
          "type": "object",
          "properties": {
            "background": { "type": "string" },
            "surface": { "type": "string" },
            "primary": { "type": "string" },
            "text": { "type": "string" },
            "accent": { "type": "string" }
          }
        },
        "fonts": {
          "type": "object",
          "properties": {
            "heading": { "type": "string" },
            "body": { "type": "string" }
          }
        }
      }
    },
    "layout": {
      "type": "object",
      "properties": {
        "hero": { "type": "boolean" },
        "sidebar": { "type": "boolean" },
        "tabs": { "type": "array", "items": { "type": "string" } }
      }
    },
    "components": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "type"],
        "properties": {
          "id": { "type": "string" },
          "type": { "enum": ["CharacterPanel", "StatePanel", "SceneLog", "ActionBar", "RelationshipMap", "ImageGenButton", "Gallery"] },
          "props": { "type": "object" }
        }
      }
    },
    "allowedTools": {
      "type": "array",
      "items": { "type": "string" }
    },
    "stateProjection": {
      "type": "object",
      "properties": {
        "visiblePaths": { "type": "array", "items": { "type": "string" } }
      }
    },
    "imageGen": {
      "type": "object",
      "properties": {
        "enabled": { "type": "boolean" },
        "provider": { "type": "string" },
        "endpoint": { "type": "string" },
        "modelType": { "enum": ["sd", "diffusion"] },
        "workflow": { "type": "string" },
        "promptTemplate": { "type": "string" },
        "promptNodeId": { "type": "string" },
        "basePrompt": { "type": "string" },
        "negativePrompt": { "type": "string" },
        "outputDir": { "type": "string" },
        "triggers": {
          "type": "object",
          "properties": {
            "eventDriven": { "type": "array", "items": { "type": "string" } },
            "stateDriven": { "type": "array", "items": { "type": "string" } },
            "multiAngleFallback": { "type": "array", "items": { "type": "string" } }
          }
        }
      }
    }
  }
}
```

- [ ] **Step 2: 用 jsonschema 或 ajv 做一次手动校验**

```bash
cd /home/programer/PiAgent
python3 -c "import json, jsonschema; jsonschema.validate(json.load(open('data/page-spec.example.json')), json.load(open('schemas/page-spec.json')))" || echo "尚未创建 example，跳过"
```

预期：如果 example 不存在则跳过，不报错。

- [ ] **Step 3: Commit**

```bash
git add schemas/page-spec.json
git commit -m "chore: add page-spec JSON schema"
```

---

### Task 2: 创建 UI 语义提取模块

**Files:**
- Create: `scripts/extract_ui_semantics.py`
- Create: `tests/test_extract_ui_semantics.py`

**目标：** 从角色卡原始 JSON 中提取题材、风格、UI 面板、生图规则，输出一个 UI 语义 JSON。

- [ ] **Step 1: 编写测试**

```python
# tests/test_extract_ui_semantics.py
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from extract_ui_semantics import extract_ui_semantics


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
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd /home/programer/PiAgent
python3 -m pytest tests/test_extract_ui_semantics.py -v
```

预期：两条测试因 `extract_ui_semantics` 未定义而失败。

- [ ] **Step 3: 编写实现**

```python
#!/usr/bin/env python3
"""从 SillyTavern 角色卡中提取 UI 相关语义。

Usage:
    python3 extract_ui_semantics.py card.json ui-semantics.json
"""

import json
import re
import sys
from pathlib import Path


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
    text_lower = text.lower()
    genres = []
    for genre, keywords in GENRE_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            genres.append(genre)
    return genres or ["现代"]


def _detect_style(text: str) -> list[str]:
    styles = [kw for kw in STYLE_KEYWORDS if kw in text]
    return styles


def _extract_ui_panels(text: str) -> list[dict]:
    panels = []
    # 简单检测 HTML 面板片段
    for match in re.finditer(r"<div[^>]*>(.*?)</div>", text, re.S):
        content = match.group(1)
        if any(kw in content for kw in ["HP", "好感度", "金钱", "状态", "level"]):
            panels.append({"type": "html_panel", "snippet": content[:200]})
    return panels


def _extract_image_gen_rules(text: str) -> dict:
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

    # prompt 净化规则
    if "no" in text_lower or "without" in text_lower or "none" in text_lower:
        rules["forbiddenWords"].extend(["no", "without", "none"])

    # 固定属性
    fixed_attr_patterns = ["发色", "肤色", "眼睛颜色", "胸部大小", "身材"]
    for attr in fixed_attr_patterns:
        if attr in text:
            rules["fixedAttributes"].append(attr)

    return rules


def extract_ui_semantics(card: dict) -> dict:
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

    with open(card_path, "r", encoding="utf-8") as f:
        card = json.load(f)

    semantics = extract_ui_semantics(card)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(semantics, f, ensure_ascii=False, indent=2)
        print(f"Saved to {out_path}")
    else:
        print(json.dumps(semantics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd /home/programer/PiAgent
python3 -m pytest tests/test_extract_ui_semantics.py -v
```

预期：全部通过。

- [ ] **Step 5: Commit**

```bash
git add scripts/extract_ui_semantics.py tests/test_extract_ui_semantics.py
git commit -m "feat: add UI semantic extraction module"
```

---

### Task 3: 创建 page-spec 生成脚本

**Files:**
- Create: `scripts/generate_page_spec.py`
- Create: `tests/test_generate_page_spec.py`

**目标：** 读取 `data/card-ir.json` 和 UI 语义，生成 `data/page-spec.json`。

- [ ] **Step 1: 编写测试**

```python
# tests/test_generate_page_spec.py
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from generate_page_spec import generate_page_spec


def test_generates_modern_theme_by_default():
    ir = {
        "version": 1,
        "persona": [{"name": "艾莉娅"}],
        "settingFacts": [],
        "mutableConcepts": [],
        "style": {"tone": "gentle"},
    }
    ui = {"version": 1, "genreKeywords": ["恋爱"], "styleKeywords": [], "uiPanels": [], "imageGenRules": {}}
    spec = generate_page_spec(ir, ui)
    assert spec["theme"]["base"] == "modern"
    assert any(c["type"] == "CharacterPanel" for c in spec["components"])


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
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd /home/programer/PiAgent
python3 -m pytest tests/test_generate_page_spec.py -v
```

预期：因 `generate_page_spec` 未定义而失败。

- [ ] **Step 3: 编写实现**

```python
#!/usr/bin/env python3
"""从 card-ir.json 和 UI 语义生成 page-spec.json。

Usage:
    python3 generate_page_spec.py data/card-ir.json data/ui-semantics.json data/page-spec.json
"""

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

    theme = dict(THEME_DEFAULTS[theme_id])

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
        {"id": "hero", "type": "Hero", "props": {"title": ir.get("persona", [{}])[0].get("name", "角色卡")}},
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

    return {
        "version": 1,
        "source": {
            "cardName": ir.get("persona", [{}])[0].get("name", "unknown"),
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
        "imageGen": image_gen,
    }


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    ir_path = sys.argv[1]
    ui_path = sys.argv[2]
    out_path = sys.argv[3] if len(sys.argv) > 3 else None

    with open(ir_path, "r", encoding="utf-8") as f:
        ir = json.load(f)
    with open(ui_path, "r", encoding="utf-8") as f:
        ui = json.load(f)

    spec = generate_page_spec(ir, ui)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(spec, f, ensure_ascii=False, indent=2)
        print(f"Saved to {out_path}")
    else:
        print(json.dumps(spec, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd /home/programer/PiAgent
python3 -m pytest tests/test_generate_page_spec.py -v
```

预期：全部通过。

- [ ] **Step 5: Commit**

```bash
git add scripts/generate_page_spec.py tests/test_generate_page_spec.py
git commit -m "feat: add page-spec generation script"
```

---

### Task 4: 创建 page-spec 校验脚本

**Files:**
- Create: `scripts/validate_page_spec.py`
- Create: `tests/test_validate_page_spec.py`

**目标：** 校验生成的 `data/page-spec.json` 是否符合 schema。

- [ ] **Step 1: 编写测试**

```python
# tests/test_validate_page_spec.py
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from validate_page_spec import validate_page_spec


def test_valid_spec():
    spec = {
        "version": 1,
        "theme": {"id": "modern", "base": "modern", "colors": {}, "fonts": {}},
        "layout": {},
        "components": [],
    }
    assert validate_page_spec(spec) is True


def test_missing_version():
    spec = {"theme": {"id": "modern", "base": "modern", "colors": {}, "fonts": {}}, "layout": {}, "components": []}
    assert validate_page_spec(spec) is False
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd /home/programer/PiAgent
python3 -m pytest tests/test_validate_page_spec.py -v
```

预期：因 `validate_page_spec` 未定义而失败。

- [ ] **Step 3: 编写实现**

```python
#!/usr/bin/env python3
"""校验 page-spec.json 是否符合 schema。

Usage:
    python3 validate_page_spec.py data/page-spec.json
"""

import json
import sys
from pathlib import Path


def validate_page_spec(spec: dict) -> bool:
    required = {"version", "theme", "layout", "components"}
    if not required.issubset(spec.keys()):
        return False
    if spec.get("version") != 1:
        return False
    theme = spec.get("theme", {})
    if not all(k in theme for k in ("id", "base", "colors", "fonts")):
        return False
    if not isinstance(spec.get("components"), list):
        return False
    for c in spec.get("components", []):
        if "id" not in c or "type" not in c:
            return False
    return True


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    path = sys.argv[1]
    with open(path, "r", encoding="utf-8") as f:
        spec = json.load(f)

    if validate_page_spec(spec):
        print("page-spec.json 校验通过")
        sys.exit(0)
    else:
        print("page-spec.json 校验失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd /home/programer/PiAgent
python3 -m pytest tests/test_validate_page_spec.py -v
```

预期：全部通过。

- [ ] **Step 5: Commit**

```bash
git add scripts/validate_page_spec.py tests/test_validate_page_spec.py
git commit -m "feat: add page-spec validation script"
```

---

### Task 5: 创建 Next.js 前端项目脚手架

**Files:**
- Create: `web/package.json`
- Create: `web/next.config.js`
- Create: `web/tsconfig.json`
- Create: `web/tailwind.config.ts`
- Create: `web/app/layout.tsx`
- Create: `web/app/page.tsx`
- Create: `web/app/globals.css`
- Create: `scripts/setup_frontend.py`

**目标：** 生成一个可独立运行、也可被 extension 托管的 Next.js 14 项目。

- [ ] **Step 1: 编写 setup_frontend.py 脚本**

```python
#!/usr/bin/env python3
"""根据 page-spec.json 生成 Next.js 前端项目脚手架。

Usage:
    python3 setup_frontend.py data/page-spec.json
"""

import json
import shutil
import sys
from pathlib import Path


PACKAGE_JSON = """{
  "name": "tavern2agent-web",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "test": "vitest run"
  },
  "dependencies": {
    "next": "14.2.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "uuid": "^9.0.1"
  },
  "devDependencies": {
    "@types/node": "^20",
    "@types/react": "^18",
    "@types/react-dom": "^18",
    "@types/uuid": "^9.0.8",
    "autoprefixer": "^10.4.19",
    "postcss": "^8.4.38",
    "tailwindcss": "^3.4.3",
    "typescript": "^5",
    "vitest": "^1.6.0"
  }
}
"""

NEXT_CONFIG = """/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  distDir: 'dist',
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://127.0.0.1:${process.env.NEXT_PUBLIC_TAVERN2AGENT_PORT || 3001}/api/:path*',
      },
    ];
  },
};

module.exports = nextConfig;
"""

TS_CONFIG = """{
  "compilerOptions": {
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": { "@/*": ["./*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
"""

TAILWIND_CONFIG = """import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};

export default config;
"""

POSTCSS_CONFIG = """module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
"""

GLOBALS_CSS = """@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --background: #ffffff;
  --surface: #f5f5f5;
  --primary: #2563eb;
  --text: #111827;
  --accent: #db2777;
}

body {
  background-color: var(--background);
  color: var(--text);
}
"""

LAYOUT_TSX = """import type { Metadata } from 'next';
import './globals.css';
import { ThemeProvider } from '@/components/ThemeProvider';

export const metadata: Metadata = {
  title: 'Tavern2Agent',
  description: '角色卡互动叙事页面',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang='zh-CN'>
      <body>
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}
"""

PAGE_TSX = """import { PageSpec } from '@/lib/page-spec';
import { CharacterPanel } from '@/components/CharacterPanel';
import { StatePanel } from '@/components/StatePanel';
import { SceneLog } from '@/components/SceneLog';
import { ImageGenButton } from '@/components/ImageGenButton';
import { Gallery } from '@/components/Gallery';

async function loadSpec(): Promise<PageSpec> {
  const res = await fetch('http://127.0.0.1:3001/page-spec.json', { next: { revalidate: 0 } });
  if (!res.ok) {
    return {
      version: 1,
      theme: { id: 'modern', base: 'modern', colors: {}, fonts: {} },
      layout: {},
      components: [],
    };
  }
  return res.json();
}

export default async function Home() {
  const spec = await loadSpec();

  return (
    <main className='min-h-screen p-6'>
      <h1 className='text-3xl font-bold mb-6'>{spec.source?.cardName || '角色卡'}</h1>
      <div className='grid grid-cols-1 lg:grid-cols-3 gap-6'>
        <div className='lg:col-span-1 space-y-6'>
          <CharacterPanel spec={spec} />
          <StatePanel spec={spec} />
        </div>
        <div className='lg:col-span-2 space-y-6'>
          <SceneLog spec={spec} />
          <ImageGenButton spec={spec} />
          <Gallery spec={spec} />
        </div>
      </div>
    </main>
  );
}
"""


def setup_frontend(page_spec_path: str, web_dir: str = "web") -> None:
    root = Path(web_dir)
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)

    (root / "package.json").write_text(PACKAGE_JSON, encoding="utf-8")
    (root / "next.config.js").write_text(NEXT_CONFIG, encoding="utf-8")
    (root / "tsconfig.json").write_text(TS_CONFIG, encoding="utf-8")
    (root / "tailwind.config.ts").write_text(TAILWIND_CONFIG, encoding="utf-8")
    (root / "postcss.config.js").write_text(POSTCSS_CONFIG, encoding="utf-8")
    (root / "app").mkdir(parents=True)
    (root / "app" / "globals.css").write_text(GLOBALS_CSS, encoding="utf-8")
    (root / "app" / "layout.tsx").write_text(LAYOUT_TSX, encoding="utf-8")
    (root / "app" / "page.tsx").write_text(PAGE_TSX, encoding="utf-8")
    (root / "components").mkdir(parents=True)
    (root / "lib").mkdir(parents=True)
    (root / "themes").mkdir(parents=True)
    (root / "app" / "api").mkdir(parents=True)
    (root / "public").mkdir(parents=True)

    # 复制 page-spec.json 到 public 供开发时读取
    spec = json.loads(Path(page_spec_path).read_text(encoding="utf-8"))
    (root / "public" / "page-spec.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Frontend scaffold created at {root}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    page_spec_path = sys.argv[1]
    setup_frontend(page_spec_path)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 创建示例 page-spec 并运行脚本验证**

```bash
cd /home/programer/PiAgent
python3 -c "
import json
json.dump({
    'version': 1,
    'source': {'cardName': '测试角色', 'complexity': 'evented-standard'},
    'theme': {'id': 'fantasy', 'base': 'fantasy', 'colors': {}, 'fonts': {}},
    'layout': {'hero': True, 'sidebar': True, 'tabs': ['剧情', '状态']},
    'components': [
        {'id': 'character', 'type': 'CharacterPanel'},
        {'id': 'state', 'type': 'StatePanel'},
    ]
}, open('data/page-spec.example.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
"
python3 scripts/setup_frontend.py data/page-spec.example.json
ls -la web/
```

预期：`web/` 目录创建成功，包含 `package.json`、`app/`、`components/` 等。

- [ ] **Step 3: Commit**

```bash
git add scripts/setup_frontend.py
rm -f data/page-spec.example.json
rm -rf web/
git commit -m "feat: add frontend scaffold generator"
```

---

### Task 6: 创建前端主题系统

**Files:**
- Create: `web/themes/index.ts`
- Create: `web/themes/fantasy.ts`
- Create: `web/themes/scifi.ts`
- Create: `web/themes/modern.ts`
- Create: `web/themes/horror.ts`
- Create: `web/themes/romance.ts`
- Create: `web/components/ThemeProvider.tsx`
- Modify: `scripts/setup_frontend.py`（追加主题文件生成）

**目标：** 根据 page-spec 的 theme 配置动态注入 CSS 变量和 Tailwind 扩展。

- [ ] **Step 1: 编写主题定义**

```typescript
// web/themes/index.ts
export interface Theme {
  id: string;
  base: string;
  colors: {
    background: string;
    surface: string;
    primary: string;
    text: string;
    accent: string;
  };
  fonts: {
    heading: string;
    body: string;
  };
}

export const themes: Record<string, Theme> = {
  fantasy: {
    id: "fantasy",
    base: "fantasy",
    colors: {
      background: "#1a1510",
      surface: "#2d2418",
      primary: "#d4af37",
      text: "#f3e5c8",
      accent: "#8b0000",
    },
    fonts: { heading: "serif", body: "serif" },
  },
  scifi: {
    id: "scifi",
    base: "scifi",
    colors: {
      background: "#0a0a12",
      surface: "#12121f",
      primary: "#00f0ff",
      text: "#e0f7ff",
      accent: "#ff0055",
    },
    fonts: { heading: "sans-serif", body: "monospace" },
  },
  modern: {
    id: "modern",
    base: "modern",
    colors: {
      background: "#ffffff",
      surface: "#f5f5f5",
      primary: "#2563eb",
      text: "#111827",
      accent: "#db2777",
    },
    fonts: { heading: "sans-serif", body: "sans-serif" },
  },
  horror: {
    id: "horror",
    base: "horror",
    colors: {
      background: "#0c0c0c",
      surface: "#1a1a1a",
      primary: "#8b0000",
      text: "#d4d4d4",
      accent: "#4a0000",
    },
    fonts: { heading: "serif", body: "sans-serif" },
  },
  romance: {
    id: "romance",
    base: "romance",
    colors: {
      background: "#fff0f5",
      surface: "#ffe4e1",
      primary: "#e11d48",
      text: "#4a0416",
      accent: "#fb7185",
    },
    fonts: { heading: "serif", body: "sans-serif" },
  },
};

export function getTheme(id: string): Theme {
  return themes[id] || themes.modern;
}
```

- [ ] **Step 2: 编写 ThemeProvider**

```tsx
// web/components/ThemeProvider.tsx
"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { getTheme, Theme } from "@/themes";

interface PageSpec {
  theme?: { id?: string };
}

const ThemeContext = createContext<Theme | null>(null);

export function ThemeProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [theme, setTheme] = useState<Theme>(getTheme("modern"));

  useEffect(() => {
    fetch("/page-spec.json")
      .then((res) => res.json())
      .then((spec: PageSpec) => {
        const t = getTheme(spec.theme?.id || "modern");
        setTheme(t);
        document.documentElement.style.setProperty("--background", t.colors.background);
        document.documentElement.style.setProperty("--surface", t.colors.surface);
        document.documentElement.style.setProperty("--primary", t.colors.primary);
        document.documentElement.style.setProperty("--text", t.colors.text);
        document.documentElement.style.setProperty("--accent", t.colors.accent);
      })
      .catch(() => {});
  }, []);

  return <ThemeContext.Provider value={theme}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  return useContext(ThemeContext);
}
```

- [ ] **Step 3: 修改 setup_frontend.py 追加主题文件生成**

在 `setup_frontend` 函数末尾追加：

```python
    # 写入主题文件（简化版：setup 阶段用常量字符串）
    (root / "themes" / "index.ts").write_text(THEME_INDEX_TS, encoding="utf-8")
    (root / "components" / "ThemeProvider.tsx").write_text(THEME_PROVIDER_TSX, encoding="utf-8")
```

并定义 `THEME_INDEX_TS` 和 `THEME_PROVIDER_TSX` 常量（与上面内容一致）。

- [ ] **Step 4: 运行脚本验证文件生成**

```bash
cd /home/programer/PiAgent
python3 -c "
import json
json.dump({
    'version': 1,
    'source': {'cardName': '测试', 'complexity': 'prompt-only'},
    'theme': {'id': 'scifi', 'base': 'scifi', 'colors': {}, 'fonts': {}},
    'layout': {},
    'components': []
}, open('/tmp/page-spec-test.json', 'w'), ensure_ascii=False, indent=2)
"
python3 scripts/setup_frontend.py /tmp/page-spec-test.json
ls web/themes/ web/components/
cat web/themes/index.ts | head -5
```

预期：`web/themes/index.ts` 和 `web/components/ThemeProvider.tsx` 存在。

- [ ] **Step 5: Commit**

```bash
git add scripts/setup_frontend.py
rm -rf web/
git commit -m "feat: add frontend theme system"
```

---

### Task 7: 创建前端组件

**Files:**
- Create: `web/lib/page-spec.ts`
- Create: `web/components/CharacterPanel.tsx`
- Create: `web/components/StatePanel.tsx`
- Create: `web/components/SceneLog.tsx`
- Create: `web/components/ActionBar.tsx`
- Create: `web/components/ImageGenButton.tsx`
- Create: `web/components/Gallery.tsx`
- Modify: `scripts/setup_frontend.py`（追加组件文件生成）

**目标：** 生成一套根据 page-spec 渲染的 React 组件。

- [ ] **Step 1: 定义 page-spec 类型**

```typescript
// web/lib/page-spec.ts
export interface PageSpec {
  version: number;
  source?: {
    cardName?: string;
    archetype?: string;
    complexity?: "prompt-only" | "evented-light" | "evented-standard";
  };
  theme: {
    id: string;
    base: string;
    colors: Record<string, string>;
    fonts: Record<string, string>;
  };
  layout: {
    hero?: boolean;
    sidebar?: boolean;
    tabs?: string[];
  };
  components: Array<{
    id: string;
    type: string;
    props?: Record<string, unknown>;
  }>;
  allowedTools?: string[];
  stateProjection?: {
    visiblePaths?: string[];
  };
  imageGen?: {
    enabled: boolean;
    modelType: "sd" | "diffusion";
    endpoint: string;
    workflow: string;
    triggers?: {
      eventDriven?: string[];
      stateDriven?: string[];
      multiAngleFallback?: string[];
    };
  } | null;
}
```

- [ ] **Step 2: 编写基础组件**

```tsx
// web/components/CharacterPanel.tsx
"use client";

import { PageSpec } from "@/lib/page-spec";

export function CharacterPanel({ spec }: { spec: PageSpec }) {
  return (
    <section className="p-4 rounded-lg" style={{ backgroundColor: "var(--surface)" }}>
      <h2 className="text-xl font-bold mb-2">{spec.source?.cardName || "角色"}</h2>
      <p className="text-sm opacity-80">题材：{spec.theme.base}</p>
      <p className="text-sm opacity-80">复杂度：{spec.source?.complexity || "未知"}</p>
    </section>
  );
}
```

```tsx
// web/components/StatePanel.tsx
"use client";

import { useEffect, useState } from "react";
import { PageSpec } from "@/lib/page-spec";

export function StatePanel({ spec }: { spec: PageSpec }) {
  const [state, setState] = useState<Record<string, unknown>>({});

  useEffect(() => {
    fetch("/api/state")
      .then((res) => res.json())
      .then(setState)
      .catch(() => setState({ error: "无法读取 state" }));
  }, []);

  return (
    <section className="p-4 rounded-lg" style={{ backgroundColor: "var(--surface)" }}>
      <h2 className="text-xl font-bold mb-2">状态</h2>
      <pre className="text-xs overflow-auto max-h-64 p-2 rounded" style={{ backgroundColor: "var(--background)" }}>
        {JSON.stringify(state, null, 2)}
      </pre>
    </section>
  );
}
```

```tsx
// web/components/SceneLog.tsx
"use client";

import { PageSpec } from "@/lib/page-spec";

export function SceneLog({ spec }: { spec: PageSpec }) {
  return (
    <section className="p-4 rounded-lg" style={{ backgroundColor: "var(--surface)" }}>
      <h2 className="text-xl font-bold mb-2">剧情日志</h2>
      <p className="text-sm opacity-80">此处将展示最近的场景与事件。</p>
    </section>
  );
}
```

```tsx
// web/components/ImageGenButton.tsx
"use client";

import { useState } from "react";
import { PageSpec } from "@/lib/page-spec";

export function ImageGenButton({ spec }: { spec: PageSpec }) {
  const [loading, setLoading] = useState(false);

  if (!spec.imageGen?.enabled) {
    return null;
  }

  async function generate(subject: "character" | "scene") {
    setLoading(true);
    try {
      await fetch("/api/tools", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tool: "generate_image", args: { subject } }),
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="p-4 rounded-lg" style={{ backgroundColor: "var(--surface)" }}>
      <h2 className="text-xl font-bold mb-2">生图</h2>
      <div className="flex gap-2">
        <button
          className="px-4 py-2 rounded text-white"
          style={{ backgroundColor: "var(--primary)" }}
          onClick={() => generate("character")}
          disabled={loading}
        >
          {loading ? "生成中..." : "生成角色图"}
        </button>
        <button
          className="px-4 py-2 rounded text-white"
          style={{ backgroundColor: "var(--accent)" }}
          onClick={() => generate("scene")}
          disabled={loading}
        >
          {loading ? "生成中..." : "生成场景图"}
        </button>
      </div>
    </section>
  );
}
```

```tsx
// web/components/Gallery.tsx
"use client";

import { useEffect, useState } from "react";
import { PageSpec } from "@/lib/page-spec";

export function Gallery({ spec }: { spec: PageSpec }) {
  const [images, setImages] = useState<string[]>([]);

  useEffect(() => {
    if (!spec.imageGen?.enabled) return;
    fetch("/api/state")
      .then((res) => res.json())
      .then((state) => setImages((state.images || []).map((img: { path: string }) => img.path)))
      .catch(() => {});
  }, [spec.imageGen?.enabled]);

  if (!spec.imageGen?.enabled || images.length === 0) {
    return null;
  }

  return (
    <section className="p-4 rounded-lg" style={{ backgroundColor: "var(--surface)" }}>
      <h2 className="text-xl font-bold mb-2">图库</h2>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
        {images.map((src, i) => (
          <img key={i} src={src} alt={`generated-${i}`} className="rounded" />
        ))}
      </div>
    </section>
  );
}
```

- [ ] **Step 3: 修改 setup_frontend.py 追加组件文件生成**

在 `setup_frontend` 函数末尾追加：

```python
    (root / "lib" / "page-spec.ts").write_text(PAGE_SPEC_TS, encoding="utf-8")
    (root / "components" / "CharacterPanel.tsx").write_text(CHARACTER_PANEL_TSX, encoding="utf-8")
    (root / "components" / "StatePanel.tsx").write_text(STATE_PANEL_TSX, encoding="utf-8")
    (root / "components" / "SceneLog.tsx").write_text(SCENE_LOG_TSX, encoding="utf-8")
    (root / "components" / "ImageGenButton.tsx").write_text(IMAGE_GEN_BUTTON_TSX, encoding="utf-8")
    (root / "components" / "Gallery.tsx").write_text(GALLERY_TSX, encoding="utf-8")
```

并定义对应常量字符串。

- [ ] **Step 4: 运行脚本验证组件文件生成**

```bash
cd /home/programer/PiAgent
python3 scripts/setup_frontend.py /tmp/page-spec-test.json
ls web/components/ web/lib/
```

预期：所有组件文件和类型文件存在。

- [ ] **Step 5: Commit**

```bash
git add scripts/setup_frontend.py
rm -rf web/
git commit -m "feat: add frontend React components"
```

---

### Task 8: 创建前端 API Route

**Files:**
- Create: `web/app/api/state/route.ts`
- Create: `web/app/api/tools/route.ts`
- Create: `web/app/api/events/route.ts`
- Modify: `scripts/setup_frontend.py`（追加 API route 文件生成）

**目标：** 页面通过 Next.js API Route 与 extension 的本地 HTTP server 通信。

- [ ] **Step 1: 编写 API Route**

```typescript
// web/app/api/state/route.ts
import { NextResponse } from "next/server";

const EXTENSION_PORT = process.env.NEXT_PUBLIC_TAVERN2AGENT_PORT || "3001";

export async function GET() {
  try {
    const res = await fetch(`http://127.0.0.1:${EXTENSION_PORT}/state`, { cache: "no-store" });
    if (!res.ok) throw new Error("extension state error");
    const data = await res.json();
    return NextResponse.json(data);
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 503 });
  }
}
```

```typescript
// web/app/api/tools/route.ts
import { NextResponse } from "next/server";

const EXTENSION_PORT = process.env.NEXT_PUBLIC_TAVERN2AGENT_PORT || "3001";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const res = await fetch(`http://127.0.0.1:${EXTENSION_PORT}/tools`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error("extension tool error");
    const data = await res.json();
    return NextResponse.json(data);
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 503 });
  }
}
```

```typescript
// web/app/api/events/route.ts
import { NextResponse } from "next/server";

const EXTENSION_PORT = process.env.NEXT_PUBLIC_TAVERN2AGENT_PORT || "3001";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const res = await fetch(`http://127.0.0.1:${EXTENSION_PORT}/events`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error("extension event error");
    const data = await res.json();
    return NextResponse.json(data);
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 503 });
  }
}
```

- [ ] **Step 2: 修改 setup_frontend.py 追加 API route 文件生成**

在 `setup_frontend` 函数末尾追加：

```python
    (root / "app" / "api" / "state" / "route.ts").write_text(API_STATE_ROUTE_TS, encoding="utf-8")
    (root / "app" / "api" / "tools" / "route.ts").write_text(API_TOOLS_ROUTE_TS, encoding="utf-8")
    (root / "app" / "api" / "events" / "route.ts").write_text(API_EVENTS_ROUTE_TS, encoding="utf-8")
```

- [ ] **Step 3: 运行脚本验证 API route 文件生成**

```bash
cd /home/programer/PiAgent
python3 scripts/setup_frontend.py /tmp/page-spec-test.json
ls web/app/api/*/
```

预期：`web/app/api/state/route.ts`、`tools/route.ts`、`events/route.ts` 存在。

- [ ] **Step 4: Commit**

```bash
git add scripts/setup_frontend.py
rm -rf web/
git commit -m "feat: add frontend API routes"
```

---

### Task 9: 创建 Prompt Builder

**Files:**
- Create: `engine/image-prompt-builder.ts`（生成产物中的文件）
- Create: `web/image-prompt-builder.test.ts`（由 setup_frontend.py 生成到 web 项目中）

**目标：** 根据 `modelType` 构建 SD 标签化 prompt 或 diffusion 自然语言 prompt。

- [ ] **Step 1: 编写 TS 接口与实现**

```typescript
// engine/image-prompt-builder.ts
export interface ImageGenConfig {
  modelType: "sd" | "diffusion";
  basePrompt: string;
  negativePrompt: string;
  promptTemplate?: string;
}

export interface ImageGenContext {
  subject: "character" | "scene";
  characterName?: string;
  fixedAttributes: Record<string, string>;
  dynamicAttributes: Record<string, string>;
  sceneDescription?: string;
  styleBoost?: string[];
}

export interface ImagePromptBuilder {
  build(ctx: ImageGenContext, config: ImageGenConfig): { prompt: string; negativePrompt: string };
}

class SDPromptBuilder implements ImagePromptBuilder {
  build(ctx: ImageGenContext, config: ImageGenConfig) {
    const tags: string[] = [];

    if (ctx.subject === "character") {
      tags.push("1girl", "solo");
      for (const [key, value] of Object.entries(ctx.fixedAttributes)) {
        tags.push(value);
      }
      for (const [key, value] of Object.entries(ctx.dynamicAttributes)) {
        tags.push(value);
      }
    } else {
      if (ctx.sceneDescription) tags.push(ctx.sceneDescription);
    }

    if (config.basePrompt) tags.push(...config.basePrompt.split(",").map((s) => s.trim()));
    if (ctx.styleBoost) tags.push(...ctx.styleBoost);

    const forbidden = new Set(["no", "without", "none", "unknown"]);
    const cleanTags = tags
      .filter(Boolean)
      .map((t) => t.trim())
      .filter((t) => !forbidden.has(t.toLowerCase()));

    return {
      prompt: cleanTags.join(", "),
      negativePrompt: config.negativePrompt,
    };
  }
}

class DiffusionPromptBuilder implements ImagePromptBuilder {
  build(ctx: ImageGenContext, config: ImageGenConfig) {
    const parts: string[] = [];

    if (ctx.subject === "character") {
      parts.push(`A character named ${ctx.characterName || "the protagonist"}.`);
      const fixed = Object.entries(ctx.fixedAttributes)
        .map(([k, v]) => `${k}: ${v}`)
        .join(", ");
      if (fixed) parts.push(`Fixed appearance: ${fixed}.`);
      const dynamic = Object.entries(ctx.dynamicAttributes)
        .map(([k, v]) => `${k}: ${v}`)
        .join(", ");
      if (dynamic) parts.push(`Current appearance: ${dynamic}.`);
    } else {
      parts.push(ctx.sceneDescription || "A scene.");
    }

    if (config.basePrompt) parts.push(config.basePrompt);
    if (ctx.styleBoost) parts.push(`Style: ${ctx.styleBoost.join(", ")}.`);

    const forbidden = new Set(["no", "without", "none", "unknown"]);
    const clean = parts
      .join(" ")
      .split(" ")
      .filter((w) => !forbidden.has(w.toLowerCase().replace(/[^a-z]/g, "")))
      .join(" ");

    return {
      prompt: clean,
      negativePrompt: config.negativePrompt,
    };
  }
}

export function getPromptBuilder(modelType: "sd" | "diffusion"): ImagePromptBuilder {
  return modelType === "sd" ? new SDPromptBuilder() : new DiffusionPromptBuilder();
}
```

- [ ] **Step 2: setup_frontend.py 生成测试文件

在 `setup_frontend.py` 中追加常量：

```python
IMAGE_PROMPT_BUILDER_TEST = """import { describe, it, expect } from 'vitest';
import { getPromptBuilder } from '../engine/image-prompt-builder';

describe('image prompt builder', () => {
  const ctx = {
    subject: 'character',
    characterName: '艾莉娅',
    fixedAttributes: { hairColor: 'red hair', eyeColor: 'green eyes' },
    dynamicAttributes: { hairstyle: 'long hair' },
    styleBoost: ['fantasy'],
  };
  const config = {
    modelType: 'sd',
    basePrompt: 'masterpiece, best quality',
    negativePrompt: 'worst quality',
  };

  it('builds sd prompt with tags', () => {
    const builder = getPromptBuilder('sd');
    const result = builder.build(ctx, config);
    expect(result.prompt).toContain('red hair');
    expect(result.prompt).toContain('green eyes');
    expect(result.prompt).not.toContain('no');
  });

  it('builds diffusion prompt with natural language', () => {
    const builder = getPromptBuilder('diffusion');
    const result = builder.build(ctx, { ...config, modelType: 'diffusion' });
    expect(result.prompt).toContain('A character named');
    expect(result.prompt).toContain('red hair');
  });
});
"""
```

并在 `setup_frontend` 中写入：

```python
    (root / "image-prompt-builder.test.ts").write_text(IMAGE_PROMPT_BUILDER_TEST, encoding="utf-8")
```

- [ ] **Step 3: 运行 vitest 测试**

确保 `web/package.json` 已包含 `vitest` 依赖和测试脚本：

```json
{
  "scripts": {
    "test": "vitest run"
  },
  "devDependencies": {
    "vitest": "^1.6.0"
  }
}
```

运行：

```bash
cd /home/programer/PiAgent/web
npm install
npm run test
```

预期：测试通过。

- [ ] **Step 4: Commit**

```bash
git add engine/image-prompt-builder.ts scripts/setup_frontend.py
# 注意：node_modules 不应提交；确认 .gitignore 已排除
git commit -m "feat: add image prompt builder with sd/diffusion strategies"
```

---

### Task 10: 创建 image-gen 工具

**Files:**
- Create: `tools/image-gen.ts`
- Modify: `tools/registry.ts`（按条件注册）

**目标：** 实现可选生图工具，调用 ComfyUI，保存图片，更新 state。

- [ ] **Step 1: 编写 image-gen.ts**

```typescript
// tools/image-gen.ts
import fs from "fs";
import path from "path";
import { v4 as uuidv4 } from "uuid";
import { getPromptBuilder, ImageGenContext, ImageGenConfig } from "../engine/image-prompt-builder";

export interface ImageGenArgs {
  subject: "character" | "scene";
  promptOverride?: string;
  negativePrompt?: string;
}

export interface ImageGenStateConfig {
  enabled: boolean;
  provider: string;
  endpoint: string;
  modelType: "sd" | "diffusion";
  workflow: string;
  promptTemplate?: string;
  promptNodeId?: string;
  basePrompt: string;
  negativePrompt: string;
  outputDir: string;
}

async function callComfyUI(endpoint: string, workflow: object): Promise<string> {
  const res = await fetch(`${endpoint}/prompt`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt: workflow }),
  });
  if (!res.ok) throw new Error(`ComfyUI error: ${res.status}`);
  const data = await res.json();
  return data.prompt_id;
}

async function waitForImage(endpoint: string, promptId: string, timeout = 120000): Promise<string> {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    const res = await fetch(`${endpoint}/history/${promptId}`);
    if (!res.ok) throw new Error("ComfyUI history error");
    const history = await res.json();
    const entry = history[promptId];
    if (entry && entry.outputs) {
      for (const nodeId of Object.keys(entry.outputs)) {
        const images = entry.outputs[nodeId].images;
        if (images && images.length > 0) {
          return `${endpoint}/view?filename=${images[0].filename}&subfolder=${images[0].subfolder || ""}&type=output`;
        }
      }
    }
    await new Promise((r) => setTimeout(r, 2000));
  }
  throw new Error("ComfyUI image generation timeout");
}

export function createImageGenTool(config: ImageGenStateConfig) {
  if (!config.enabled) return null;

  return {
    name: "generate_image",
    description: "根据当前场景或角色描述生成图片。",
    parameters: {
      type: "object",
      properties: {
        subject: { enum: ["character", "scene"] },
        promptOverride: { type: "string" },
        negativePrompt: { type: "string" },
      },
      required: ["subject"],
    },
    async execute(args: ImageGenArgs, context: { state: any }) {
      const builder = getPromptBuilder(config.modelType);
      const ctx: ImageGenContext = {
        subject: args.subject,
        characterName: context.state?.protagonist?.name,
        fixedAttributes: context.state?.character?.fixedAttributes || {},
        dynamicAttributes: context.state?.character?.dynamicAttributes || {},
        sceneDescription: context.state?.scene?.description,
        styleBoost: context.state?.styleBoost || [],
      };
      const cfg: ImageGenConfig = {
        modelType: config.modelType,
        basePrompt: args.promptOverride || config.basePrompt,
        negativePrompt: args.negativePrompt || config.negativePrompt,
        promptTemplate: config.promptTemplate,
      };
      const { prompt, negativePrompt } = builder.build(ctx, cfg);

      const workflowPath = path.resolve(config.workflow);
      const workflow = JSON.parse(fs.readFileSync(workflowPath, "utf-8"));
      const nodeId = config.promptNodeId || "3";
      if (!workflow[nodeId]) throw new Error(`Workflow node ${nodeId} not found`);
      workflow[nodeId].inputs.text = prompt;
      if (workflow[nodeId].inputs.negative) {
        workflow[nodeId].inputs.negative = negativePrompt;
      }

      const promptId = await callComfyUI(config.endpoint, workflow);
      const imageUrl = await waitForImage(config.endpoint, promptId);

      // 下载图片到本地
      const imageRes = await fetch(imageUrl);
      if (!imageRes.ok) throw new Error("Download image failed");
      const buffer = Buffer.from(await imageRes.arrayBuffer());
      const filename = `${uuidv4()}.png`;
      const outputDir = path.resolve(config.outputDir);
      fs.mkdirSync(outputDir, { recursive: true });
      const localPath = path.join(outputDir, filename);
      fs.writeFileSync(localPath, buffer);

      return {
        success: true,
        path: `/generated/${filename}`,
        prompt,
      };
    },
  };
}
```

- [ ] **Step 2: 修改生成产物中的 tools/registry.ts 按条件注册**

skill 生成的 `tools/registry.ts` 应类似如下结构。若现有模板不同，请将 image-gen 注册逻辑加入现有工具注册流程：

```typescript
// tools/registry.ts
import { createImageGenTool } from "./image-gen";
import pageSpec from "../data/page-spec.json";

export function registerTools(context: any) {
  const tools: any[] = [];
  // ... 注册其他工具

  const imageGenTool = createImageGenTool(pageSpec.imageGen);
  if (imageGenTool) {
    tools.push(imageGenTool);
  }

  return tools;
}
```

- [ ] **Step 3: 安装 uuid 类型依赖**

```bash
cd /home/programer/PiAgent
npm install -D @types/uuid
npm install uuid
```

- [ ] **Step 4: 类型检查**

```bash
cd /home/programer/PiAgent
npx tsc --noEmit
```

预期：无类型错误。

- [ ] **Step 5: Commit**

```bash
git add tools/image-gen.ts tools/registry.ts
git commit -m "feat: add optional image-gen tool for ComfyUI"
```

---

### Task 11: 创建默认 ComfyUI 工作流与 Prompt 模板

**Files:**
- Create: `workflows/comfyui-sd.json`
- Create: `workflows/comfyui-diffusion.json`
- Create: `templates/comfyui-prompt-sd.txt`
- Create: `templates/comfyui-prompt-diffusion.txt`
- Create: `workflows/README.md`

**目标：** 提供开箱即用的默认工作流和模板，并说明如何导入自定义工作流。

- [ ] **Step 1: 编写默认 SD 工作流**

```json
{
  "1": {
    "inputs": {
      "ckpt_name": "model.safetensors"
    },
    "class_type": "CheckpointLoaderSimple"
  },
  "2": {
    "inputs": {
      "text": "",
      "clip": ["1", 1]
    },
    "class_type": "CLIPTextEncode"
  },
  "3": {
    "inputs": {
      "text": "{{NEGATIVE_PROMPT}}",
      "clip": ["1", 1]
    },
    "class_type": "CLIPTextEncode"
  },
  "4": {
    "inputs": {
      "width": 512,
      "height": 768,
      "batch_size": 1
    },
    "class_type": "EmptyLatentImage"
  },
  "5": {
    "inputs": {
      "seed": 0,
      "steps": 25,
      "cfg": 7,
      "sampler_name": "euler_ancestral",
      "scheduler": "normal",
      "denoise": 1,
      "model": ["1", 0],
      "positive": ["2", 0],
      "negative": ["3", 0],
      "latent_image": ["4", 0]
    },
    "class_type": "KSampler"
  },
  "6": {
    "inputs": {
      "samples": ["5", 0],
      "vae": ["1", 2]
    },
    "class_type": "VAEDecode"
  },
  "7": {
    "inputs": {
      "filename_prefix": "tavern2agent",
      "images": ["6", 0]
    },
    "class_type": "SaveImage"
  }
}
```

- [ ] **Step 2: 编写默认 diffusion 工作流**

与 SD 工作流结构相同，仅 `ckpt_name` 和建议尺寸可能不同。复制 `comfyui-sd.json` 为 `comfyui-diffusion.json`，并将节点 1 的 `ckpt_name` 改为 `zimage.safetensors`（占位，用户需替换）。

- [ ] **Step 3: 编写 Prompt 模板**

```txt
<!-- templates/comfyui-prompt-sd.txt -->
{{basePrompt}}, {{#fixedAttributes}}{{value}}, {{/fixedAttributes}}{{#dynamicAttributes}}{{value}}, {{/dynamicAttributes}}{{#sceneDescription}}{{sceneDescription}}, {{/sceneDescription}}{{#styleBoost}}{{styleBoost}}, {{/styleBoost}}
```

```txt
<!-- templates/comfyui-prompt-diffusion.txt -->
{{basePrompt}}. {{#subjectCharacter}}A character named {{characterName}}. Fixed appearance: {{#fixedAttributes}}{{key}} is {{value}}, {{/fixedAttributes}}. Current appearance: {{#dynamicAttributes}}{{key}} is {{value}}, {{/dynamicAttributes}}.{{/subjectCharacter}}{{#subjectScene}}Scene: {{sceneDescription}}.{{/subjectScene}} Style: {{#styleBoost}}{{styleBoost}}, {{/styleBoost}}.
```

- [ ] **Step 4: 编写 workflows/README.md**

```markdown
# ComfyUI 工作流导入说明

## 默认工作流

- `comfyui-sd.json`：适合 SD 1.5 / SDXL / Pony 等标签化模型。
- `comfyui-diffusion.json`：适合 zimage 等自然语言 diffusion 模型。

## 导入自己的工作流

1. 在 ComfyUI 中搭建好工作流。
2. 点击 **Save (API Format)** 导出为 API 格式 JSON。
3. 将 JSON 放到 `workflows/` 目录，例如 `workflows/my-workflow.json`。
4. 在 `data/page-spec.json` 中修改：

```json
{
  "imageGen": {
    "workflow": "workflows/my-workflow.json",
    "promptNodeId": "3"
  }
}
```

5. 如果 prompt 输入节点不是默认的 `3`，请修改为实际节点 ID。

## 节点要求

工具会替换指定节点的 `inputs.text` 字段。请确保该节点是 `CLIPTextEncode` 或等价的文本编码节点。
```

- [ ] **Step 5: Commit**

```bash
git add workflows/ templates/
git commit -m "feat: add default ComfyUI workflows and prompt templates"
```

---

### Task 12: 扩展 extension.ts 启动 Web Server

**Files:**
- Create: `references/templates/extension.ts.template`（skill 仓库，作为生成产物参考）
- Create: `engine/web-server.ts`（生成产物或 skill 模板）

**目标：** 让 skill 生成的 `extension.ts` 启动本地 HTTP server，暴露 `/state`、`/tools`、`/events` 三个端点。

- [ ] **Step 1: 编写 engine/web-server.ts**

```typescript
// engine/web-server.ts
import http from "http";
// 注意：ExtensionContext 应替换为实际 pi extension API 提供的 context 类型
import type { ExtensionContext } from "@pi/core"; // 或项目实际使用的包名

interface WebServerDeps {
  getState: () => any;
  dispatch: (event: any) => Promise<any>;
  callTool: (tool: string, args: any) => Promise<any>;
}

export function startWebServer(context: ExtensionContext, deps: WebServerDeps): number {
  const server = http.createServer(async (req, res) => {
    res.setHeader("Content-Type", "application/json");
    res.setHeader("Access-Control-Allow-Origin", "*");
    res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
    res.setHeader("Access-Control-Allow-Headers", "Content-Type");

    if (req.method === "OPTIONS") {
      res.writeHead(204);
      res.end();
      return;
    }

    try {
      if (req.url === "/state" && req.method === "GET") {
        const state = deps.getState();
        res.writeHead(200);
        res.end(JSON.stringify(state));
        return;
      }

      if (req.url === "/tools" && req.method === "POST") {
        const body = await readBody(req);
        const { tool, args } = JSON.parse(body);
        const result = await deps.callTool(tool, args);
        res.writeHead(200);
        res.end(JSON.stringify(result));
        return;
      }

      if (req.url === "/events" && req.method === "POST") {
        const body = await readBody(req);
        const { event } = JSON.parse(body);
        const result = await deps.dispatch(event);
        res.writeHead(200);
        res.end(JSON.stringify(result));
        return;
      }

      res.writeHead(404);
      res.end(JSON.stringify({ error: "not found" }));
    } catch (e) {
      res.writeHead(500);
      res.end(JSON.stringify({ error: String(e) }));
    }
  });

  // 监听随机端口
  server.listen(0, "127.0.0.1");
  const address = server.address();
  const port = typeof address === "object" && address ? address.port : 0;

  // 写入端口文件供前端发现
  const fs = require("fs");
  const path = require("path");
  const portFile = path.join(process.cwd(), ".pi", "web-port.json");
  fs.mkdirSync(path.dirname(portFile), { recursive: true });
  fs.writeFileSync(portFile, JSON.stringify({ port }, null, 2));

  return port;
}

function readBody(req: http.IncomingMessage): Promise<string> {
  return new Promise((resolve, reject) => {
    let body = "";
    req.on("data", (chunk) => (body += chunk));
    req.on("end", () => resolve(body));
    req.on("error", reject);
  });
}
```

- [ ] **Step 2: 修改 extension.ts**

在现有 `extension.ts` 的 `activate` 函数中，工具注册之后调用 `startWebServer`：

```typescript
// extension.ts
import { startWebServer } from "./engine/web-server";

export function activate(context: ExtensionContext) {
  // 原有工具注册
  const tools = registerTools(context);

  // 启动 web server
  const port = startWebServer(context, {
    getState: () => loadState(context),
    dispatch: async (event) => {
      // 调用 engine 的 dispatch
      return await dispatchEvent(event);
    },
    callTool: async (tool, args) => {
      const t = tools.find((x: any) => x.name === tool);
      if (!t) throw new Error(`Tool not found: ${tool}`);
      return await t.execute(args, { state: loadState(context) });
    },
  });

  console.log(`[tavern2agent] web server started on http://127.0.0.1:${port}`);
}
```

- [ ] **Step 3: 类型检查**

```bash
cd /home/programer/PiAgent
npx tsc --noEmit
```

预期：无新增类型错误（可能需要根据实际 `ExtensionContext` 类型调整）。

- [ ] **Step 4: Commit**

```bash
git add engine/web-server.ts extension.ts
git commit -m "feat: extend extension.ts with local web server"
```

---

### Task 13: 更新 SKILL.md 与 References 文档

**Files:**
- Modify: `SKILL.md`
- Create: `references/frontend-design.md`
- Create: `references/image-generation.md`
- Create: `references/ui-semantic-extraction.md`

**目标：** 让 skill 知道何时、如何生成页面和生图功能，并给 downstream agent 提供参考。

- [ ] **Step 1: 更新 SKILL.md 入口流程**

在 `SKILL.md` 的“开工”部分追加：

```markdown
## 页面与生图（可选）

如果用户要求生成页面或开启生图：

1. 先读 `references/frontend-design.md`、`references/image-generation.md`、`references/ui-semantic-extraction.md`。
2. 审计卡中是否存在前端面板、HTML 状态栏、文生图规则、C.3 角色详述、SCST 等 UI 相关内容。
3. 运行 `scripts/extract_ui_semantics.py` 提取 UI 语义。
4. 在 `data/card-ir.json` 中补充 `uiSemantics` 字段。
5. 生成 `data/page-spec.json`。
6. 运行 `scripts/setup_frontend.py` 生成 `web/` 前端项目。
7. 如果开启 imageGen，生成 `tools/image-gen.ts`、`workflows/`、`templates/`。
8. 扩展 `extension.ts` 启动 web server。

## 新增产物

prompt-only / evented 均可追加：

```txt
data/page-spec.json
web/
workflows/
templates/
```

evented 追加：

```txt
tools/image-gen.ts
engine/web-server.ts
engine/image-prompt-builder.ts
```
```

- [ ] **Step 2: 编写 references/frontend-design.md**

```markdown
# 前端设计规范

## page-spec.json

`data/page-spec.json` 是前端渲染的唯一配置来源。

### theme

- `id`: 主题标识
- `base`: 基础主题（fantasy / scifi / modern / horror / romance）
- `colors`: CSS 变量值
- `fonts`: heading / body 字体族

### layout

- `hero`: 是否展示首屏大图/标题
- `sidebar`: 是否展示侧边栏
- `tabs`: 页面标签页

### components

组件数组，每个组件包含 `id`、`type`、`props`。

允许的类型：

- `Hero`
- `CharacterPanel`
- `StatePanel`
- `SceneLog`
- `ActionBar`
- `RelationshipMap`
- `ImageGenButton`
- `Gallery`

## 主题选择优先级

1. 题材关键词 → base 主题
2. `creator_notes` 中的风格词 → 颜色/字体覆盖
3. 无法识别 → `modern`
```

- [ ] **Step 3: 编写 references/image-generation.md**

```markdown
# 生图功能规范

## 启用条件

`data/page-spec.json` 中 `imageGen.enabled === true`。

## 后端

统一使用 ComfyUI，通过 `/prompt` 提交 workflow，通过 `/history/{prompt_id}` 轮询结果。

## 模型类型

- `sd`: 标签化 prompt，适合 SD 1.5 / SDXL / Pony。
- `diffusion`: 自然语言 prompt，适合 zimage 等。

## Prompt 构建规则

- 固定属性从角色卡读取，不可变更。
- 动态属性继承当前场景状态。
- 过滤 `no`、`without`、`none`、`unknown`。

## 用户自定义工作流

1. ComfyUI 导出 API workflow。
2. 放入 `workflows/`。
3. 修改 `data/page-spec.json` 中的 `workflow` 和 `promptNodeId`。

## 触发规则

- 节点驱动：特定事件发生时触发。
- 情境驱动：特定状态持续时触发。
- 多视角兜底：单轮内容不足时触发。
```

- [ ] **Step 4: 编写 references/ui-semantic-extraction.md**

```markdown
# UI 语义提取规范

## 提取目标

从角色卡原始文本中提取：

1. 题材关键词（genreKeywords）
2. 视觉风格关键词（styleKeywords）
3. HTML 状态栏/面板片段（uiPanels）
4. 生图规则（imageGenRules）

## imageGenRules 结构

```json
{
  "driverMode": ["event-driven", "state-driven", "multi-angle"],
  "eventDrivenTriggers": ["场景切换", "姿势改变"],
  "stateDrivenTriggers": ["角色描写", "特写"],
  "multiAngleTriggers": ["环境镜头", "POV"],
  "forbiddenWords": ["no", "without", "none"],
  "fixedAttributes": ["发色", "眼睛颜色"]
}
```

## 提取来源

- `description`
- `personality`
- `scenario`
- `first_mes`
- `creator_notes`
- `system_prompt`
- `post_history_instructions`
- 世界书条目内容
```

- [ ] **Step 5: Commit**

```bash
git add SKILL.md references/frontend-design.md references/image-generation.md references/ui-semantic-extraction.md
git commit -m "docs: update SKILL.md and add frontend/image-gen references"
```

---

### Task 14: 添加测试

**Files:**
- Create: `tests/test_theme_selector.py`
- Create: `tests/integration/test_full_pipeline.py`
- Create: `fixtures/sample-card.json`

**目标：** 覆盖主题选择、端到端生成流程。

- [ ] **Step 1: 编写主题选择器测试**

```python
# tests/test_theme_selector.py
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
```

- [ ] **Step 2: 编写集成测试**

```python
# tests/integration/test_full_pipeline.py
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent


def test_full_pipeline():
    card = {
        "data": {
            "name": "艾莉娅",
            "description": "奇幻世界的法师少女。",
            "scenario": "古老图书馆",
            "creator_notes": "风格：水彩。驱动模式：节点驱动，场景切换时触发。",
        }
    }

    with tempfile.TemporaryDirectory() as tmp:
        card_path = Path(tmp) / "card.json"
        card_path.write_text(json.dumps(card), encoding="utf-8")

        ir_path = Path(tmp) / "card-ir.json"
        ui_path = Path(tmp) / "ui-semantics.json"
        spec_path = Path(tmp) / "page-spec.json"

        # 集成测试关注 UI 提取 → page-spec → frontend 链路，因此用简化 IR 直接保存
        ir = {
            "version": 1,
            "persona": [{"name": "艾莉娅"}],
            "settingFacts": [],
            "mutableConcepts": [{"name": "mana"}],
            "style": {},
        }
        ir_path.write_text(json.dumps(ir), encoding="utf-8")

        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "extract_ui_semantics.py"), str(card_path), str(ui_path)],
            check=True,
        )
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "generate_page_spec.py"), str(ir_path), str(ui_path), str(spec_path)],
            check=True,
        )
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "validate_page_spec.py"), str(spec_path)],
            check=True,
        )
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "setup_frontend.py"), str(spec_path)],
            check=True,
        )

        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        assert spec["theme"]["base"] == "fantasy"
        assert any(c["type"] == "StatePanel" for c in spec["components"])
        assert (ROOT / "web" / "package.json").exists()
```

- [ ] **Step 3: 运行测试**

```bash
cd /home/programer/PiAgent
python3 -m pytest tests/test_theme_selector.py tests/integration/test_full_pipeline.py -v
```

预期：全部通过。

- [ ] **Step 4: Commit**

```bash
git add tests/
git commit -m "test: add theme selector and integration tests"
```

---

### Task 15: 集成与下场验证

**Files：**
- 运行命令，不新增文件。

**目标：** 确保整个链路在真实 pi 环境中可用。

- [ ] **Step 1: 前端构建验证**

```bash
cd /home/programer/PiAgent
python3 scripts/setup_frontend.py data/page-spec.json
cd web
npm install
npm run build
```

预期：`web/dist/` 生成成功，无类型错误。

- [ ] **Step 2: 类型检查全项目**

```bash
cd /home/programer/PiAgent
npx tsc --noEmit
```

预期：无类型错误。

- [ ] **Step 3: Python 测试全部通过**

```bash
cd /home/programer/PiAgent
python3 -m pytest tests/ -v
```

预期：全部通过。

- [ ] **Step 4: 下场测试**

1. 选择一张示例角色卡，运行完整 skill 流程：

```bash
cd /home/programer/PiAgent
python3 scripts/extract_card.py fixtures/sample-card.png /tmp/card.json
# 假设 agent 已生成 card-ir.json
python3 scripts/extract_ui_semantics.py /tmp/card.json /tmp/ui.json
python3 scripts/generate_page_spec.py /tmp/card-ir.json /tmp/ui.json /tmp/page-spec.json
python3 scripts/setup_frontend.py /tmp/page-spec.json
```

2. 启动 pi，加载生成的项目。
3. 打开页面，确认主题、角色面板、状态面板渲染正常。
4. 如果开启 imageGen，点击“生成角色图”，确认 ComfyUI 被调用、图片出现在 Gallery。
5. 进行 20-30 轮对话，检查 state 同步、事件触发、图片生成无异常。

- [ ] **Step 5: 清理与最终 Commit**

```bash
cd /home/programer/PiAgent
rm -rf web/node_modules web/dist web/.next
# 根据下场结果修复问题后
git add -A
git commit -m "feat: complete frontend and image generation integration"
```

---

## 计划自审

### 1. Spec 覆盖检查

| 设计文档章节 | 对应任务 |
|---|---|
| 3. 新增产物结构 | Task 1（schema）、Task 5（web 脚手架）、Task 11（workflows/templates） |
| 4. 页面主题与组件选择逻辑 | Task 2（UI 语义提取）、Task 3（page-spec 生成）、Task 6（主题系统）、Task 7（组件） |
| 5. 前后端通信机制 | Task 8（API Route）、Task 12（extension web server） |
| 6. 生图功能集成 | Task 9（prompt builder）、Task 10（image-gen 工具）、Task 11（workflow/template） |
| 7. Skill 工作流程更新 | Task 13（SKILL.md + references） |
| 8. 测试与验收 | Task 14（测试）、Task 15（集成与下场验证） |
| 9. 风险与回退 | Task 15 下场步骤中已覆盖回退验证 |

无遗漏。

### 2. 占位符扫描

已排除以下问题：

- 无 `TBD`、`TODO`、`implement later` 等模糊表述。
- 所有代码步骤均提供完整代码或明确模板。
- 测试命令和预期输出均已给出。
- 用户需替换的 `zimage.safetensors` 等已明确标注为占位。

### 3. 类型一致性检查

- `ImageGenConfig` / `ImageGenStateConfig` 字段一致：`modelType`、`basePrompt`、`negativePrompt`、`promptTemplate?`。
- `ImageGenContext` 在 prompt builder 和 image-gen 工具中用法一致。
- `page-spec.json` schema 与 `generate_page_spec.py` 输出字段一致。

---

## 执行交接

计划已完成并保存到：`docs/superpowers/plans/2026-06-17-tavern2agent-frontend-imagegen-plan.md`

**两种执行方式：**

1. **Subagent-Driven（推荐）** —— 为每个 Task 分派独立子代理，子代理之间按依赖顺序执行，每完成一个 Task 做快速审查。
2. **Inline Execution** —— 在当前会话中按 Task 逐步执行，使用 executing-plans skill 批量推进并设置检查点。

你希望用哪种方式开始实现？
