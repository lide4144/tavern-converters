# 前端设计规范

## page-spec.json

`data/page-spec.json` 是前端渲染的唯一配置来源。它从 `card-ir.json` 与 UI 语义提取结果生成，skill 再据此生成 Next.js 项目 `web/`。

### source

- `cardName`: 角色卡名称
- `archetype`: runtime 方案档位
- `complexity`: `prompt-only` / `evented-light` / `evented-standard`

### theme

- `id`: 主题标识
- `base`: 基础主题（fantasy / scifi / modern / horror / romance）
- `colors`: CSS 变量值（background / surface / primary / text / accent）
- `fonts`: heading / body 字体族

### layout

- `hero`: 是否展示首屏大图/标题
- `sidebar`: 是否展示侧边栏
- `tabs`: 页面标签页数组

### components

组件数组，每个组件包含：

- `id`: 组件实例 ID
- `type`: 组件类型
- `props`: 组件专属属性

允许的类型：

- `Hero`
- `CharacterPanel`
- `StatePanel`
- `SceneLog`
- `ActionBar`
- `RelationshipMap`
- `ImageGenButton`
- `Gallery`

### allowedTools

页面允许调用的工具名列表，例如 `["generate_image"]`。

### stateProjection

- `visiblePaths`: 可展示给玩家的 state 路径白名单。

## 主题选择优先级

1. 题材关键词（genreKeywords）匹配 base 主题。
2. `creator_notes` 中的风格词覆盖颜色、字体。
3. 无法识别时回退到 `modern`。

## 前后端通信

页面通过 Next.js API Route 访问 extension 启动的本地 HTTP server：

- `GET /api/state` → 当前 state 投影
- `POST /api/tools` → 调用工具
- `POST /api/events` → 触发领域事件

## 增量更新

- `data/page-spec.json` 可手工编辑，重新运行 `scripts/setup_frontend.py` 会覆盖 `web/` 中的 skill 生成文件。
- `web/` 中用户新增的文件不会被删除。
