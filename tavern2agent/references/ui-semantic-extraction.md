# UI 语义提取规范

## 提取目标

从角色卡原始文本中提取：

1. **题材关键词**（`genreKeywords`）：奇幻、科幻、现代、恐怖、恋爱等。
2. **视觉风格关键词**（`styleKeywords`）：赛博朋克、水彩、像素、暗黑、梦幻等。
3. **HTML 状态栏/面板片段**（`uiPanels`）：包含 HP、好感度、金钱、状态、等级等字段的 HTML 片段。
4. **生图规则**（`imageGenRules`）：驱动模式、触发时机、固定属性、净化规则等。

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

以下字段按顺序合并为提取文本：

- `description`
- `personality`
- `scenario`
- `first_mes`
- `creator_notes`
- `system_prompt`
- `post_history_instructions`
- 世界书条目内容（启用与禁用均审计）

## 题材关键词

| 题材 | 信号词 |
|---|---|
| 奇幻 | 魔法、剑与魔法、法师、龙、地下城、中世纪、魔导 |
| 科幻 | 未来、太空、机甲、赛博朋克、星际、AI、机器人 |
| 现代 | 校园、都市、日常、职场、现代 |
| 恐怖 | 恐怖、灵异、丧尸、克苏鲁、黑暗、惊悚 |
| 恋爱 | 恋爱、约会、告白、情侣、甜宠 |

无明确信号时回退到 `现代`。

## 驱动模式识别

| 模式 | 信号 |
|---|---|
| `event-driven` | 节点驱动、事件驱动、场景切换、姿势改变 |
| `state-driven` | 情境驱动、状态驱动、角色描写 |
| `multi-angle` | 多视角、多视角绘图 |

## 使用方式

```bash
python3 scripts/extract_ui_semantics.py card.json ui-semantics.json
```

提取结果供 `scripts/generate_page_spec.py` 使用，生成 `data/page-spec.json`。
