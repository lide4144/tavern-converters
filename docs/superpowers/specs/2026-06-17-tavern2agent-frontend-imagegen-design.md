# Tavern2Agent 前端页面与可选生图功能设计文档

## 1. 背景与目标

### 1.1 背景

Tavern2Agent 现有 skill 把 SillyTavern 角色卡编译成 pi-native 互动叙事 runtime，核心关注后端：领域事件、reducer、state schema、工具与子代理。它默认剥离 HTML 状态栏、前端面板、文生图提示词等 UI 相关内容。

### 1.2 目标

本次优化让 Tavern2Agent skill 生成的 agent **拥有基于角色卡内容自动设计的页面**，并新增**可选开启的生图功能**：

1. **自动设计页面**：根据角色卡的题材、玩法复杂度、视觉风格关键词生成不同的 Next.js 前端页面。
2. **可选生图**：根据角色卡内嵌的生图规则，调用本地 ComfyUI 生成角色立绘或场景插图。
3. **保留现有 runtime 优势**：新增能力不破坏 evented runtime 的事件源、状态写入纪律和子代理边界。

## 2. 方案选择

### 2.1 候选方案回顾

| 方案 | 概述 | 优点 | 缺点 |
|---|---|---|---|
| A. 独立 Next.js 项目生成器 | skill 额外输出一个独立 `web/` 项目 | 与 runtime 解耦，改动小 | 页面与 runtime 交互弱 |
| B. pi extension 托管前后端一体化 | 前端作为 pi extension 的一部分运行，通过 extension API 与 runtime 双向通信 | 与 evented runtime 集成自然，页面可调用工具/触发事件 | 需要深入 pi extension 机制 |
| C. 可插拔页面 DSL + 独立渲染器 | 生成 `page-spec.json` DSL，由通用渲染器动态构建页面 | 结构可版本化、可复用 | 多一层抽象，初期成本高 |

### 2.2 选定方案：B

选择 **方案 B**：pi extension 托管前后端一体化。原因：

- 最贴合“根据角色卡转换出来的 agent 拥有自己设计的页面”这一核心目标。
- 能复用 pi extension 的 API 能力，而不是让页面成为孤立静态展示。
- 生图功能可以封装成标准工具，由 GM 或页面触发，保持事件源一致。

## 3. 新增产物结构

在现有 evented runtime 产物基础上，skill 额外生成前端包并通过 pi extension 托管：

```txt
project/
├── .pi/settings.json              # 已有，追加 frontend extension 注册
├── agents/preset.json             # 已有
├── agents/gm-*.md                 # 已有
├── data/
│   ├── card-ir.json               # 已有
│   ├── runtime-plan.json          # 已有
│   └── page-spec.json             # 新增：页面主题与组件配置
├── engine/                        # 已有
├── tools/
│   ├── registry.ts                # 已有
│   └── image-gen.ts               # 新增：可选生图工具
├── extension.ts                   # 已有，扩展为同时 serve 前端 API
├── web/                           # 新增：Next.js 项目
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── api/state/route.ts     # 读取 runtime state
│   │   └── api/tools/route.ts     # 转发工具调用到 extension
│   ├── components/
│   │   ├── ThemeProvider.tsx
│   │   ├── CharacterPanel.tsx
│   │   ├── StatePanel.tsx
│   │   ├── SceneLog.tsx
│   │   └── ImageGenButton.tsx
│   ├── themes/
│   │   ├── index.ts
│   │   ├── fantasy.ts
│   │   ├── scifi.ts
│   │   ├── modern.ts
│   │   └── ...
│   ├── lib/
│   │   └── page-spec.ts
│   ├── next.config.js
│   └── package.json
├── workflows/                     # 新增：ComfyUI 工作流
│   ├── comfyui-sd.json
│   ├── comfyui-diffusion.json
│   └── README.md
├── templates/                     # 新增：prompt 模板
│   ├── comfyui-prompt-sd.txt
│   └── comfyui-prompt-diffusion.txt
├── skills/start-game/SKILL.md     # 已有，追加启动页面说明
└── start.sh                       # 已有，可选启动 dev server
```

关键点：

- `data/page-spec.json` 是从 IR 生成的页面配置，避免页面直接解析 IR。
- `web/` 是完整 Next.js 项目，可独立 `npm install && npm run dev`，也可构建为静态导出由 extension 托管。
- `tools/image-gen.ts` 默认不注册，只有 `data/page-spec.json` 中 `imageGen.enabled === true` 时才加入工具清单。

## 4. 页面主题与组件选择逻辑

### 4.1 UI 语义提取

新增一个 UI Semantic Extraction 步骤，在生成 `data/card-ir.json` 之后、`data/page-spec.json` 之前执行。

| 来源 | 提取内容 | 用途 |
|---|---|---|
| `description` / `scenario` | 题材关键词（奇幻、科幻、现代、恐怖、恋爱等） | 选择基础主题 |
| `creator_notes` / 世界书 | 视觉风格词（赛博朋克、水彩、像素、暗黑等） | 调色盘、字体、装饰元素 |
| 世界书条目中的 UI/面板 | HTML 状态栏、前端面板片段 | 推断需要展示的状态字段和布局偏好 |
| `first_mes` / 开场白 | 叙事视角、玩家角色 | 决定首页是“角色卡展示”还是“场景沉浸” |
| mechanics / mutableConcepts | 状态字段、骰子、经济、好感度 | 决定仪表盘需要哪些组件 |
| 文生图提示词（如有） | 角色外貌、场景描述 | 初始化 ComfyUI prompt |

### 4.2 主题选择器

`web/themes/index.ts` 维护主题注册表，包含 fantasy、scifi、modern、horror、romance 等。

选择逻辑：

1. 先按题材匹配基础主题。
2. 再用风格关键词覆盖调色盘、字体、装饰。
3. 冲突时以 `creator_notes` 中的显式风格词优先。
4. 无法匹配时回退到 `modern`。

### 4.3 组件选择器

根据 runtime-plan 复杂度档位选择组件集合：

- **prompt-only**：`Hero` + `CharacterPanel` + `OpeningScene`
- **evented light**：追加 `StatePanel`（只读）
- **evented standard**：追加 `ActionBar`、`SceneLog`、`RelationshipMap` 等
- **有 imageGen 开启**：追加 `ImageGenButton`、`Gallery`

组件和主题配置最终写入 `data/page-spec.json`，前端只负责渲染，不做决策。

## 5. 前后端通信机制

### 5.1 总体流程

```txt
用户操作页面
  → Next.js API Route (/api/tools, /api/state)
  → extension.ts 中暴露的 HTTP handler
  → pi extension API / tool call hook
  → engine reducer / tool implementation
  → state 更新
  → 页面轮询 / 事件通知后重新拉取 state
```

### 5.2 extension.ts 扩展

`extension.ts` 新增 `startWebServer()` 函数，激活时启动本地 HTTP server：

```ts
export function activate(context: ExtensionContext) {
  registerTools(context);

  const webPort = startWebServer(context, {
    getState,
    dispatch,
    callTool,
  });

  context.workspaceState.update("tavern2agent.webPort", webPort);
}
```

### 5.3 Next.js API Route

- `GET /api/state`：返回当前 state 投影（只暴露 `page-spec` 中声明为 player-visible 的字段）。
- `POST /api/tools`：接收 `{ tool, args }`，转发到 extension 的 `callTool`。
- `POST /api/events`：接收 `{ event }`，转发到 extension 的 `dispatch`。

### 5.4 安全边界

- 页面只能调用 `data/page-spec.json` 中 `allowedTools` 列出的工具。
- `dispatch` 只接受白名单内的事件类型。
- state 投影由 extension 端过滤，前端不直接接触完整 state。

### 5.5 发现机制

extension 启动 web server 后，把实际端口写入 `.pi/web-port.json`。前端在运行时通过 `fetch("/.pi/web-port.json")` 或读取环境变量 `NEXT_PUBLIC_TAVERN2AGENT_PORT` 来连接。本地开发时，用户也可手动指定环境变量覆盖。

## 6. 生图功能集成

### 6.1 总体架构

```txt
角色卡 IR
  → image-gen prompt builder
  → ComfyUI API
  → 图片保存到 web/public/generated/
  → 更新 state.images[]
  → 页面展示 Gallery
```

### 6.2 `tools/image-gen.ts`

新增可选工具，默认不注册。当 `data/page-spec.json` 中 `imageGen.enabled === true` 时加入 `tools/registry.ts`。

工具签名：

```ts
{
  name: "generate_image",
  description: "根据当前场景或角色描述生成图片。仅在有 imageGen 配置时可用。",
  input: {
    type: "object",
    properties: {
      subject: { enum: ["character", "scene"] },
      promptOverride: { type: "string" },
      negativePrompt: { type: "string" }
    },
    required: ["subject"]
  }
}
```

### 6.3 Prompt 构建与模型类型

后端统一为 ComfyUI，差异在模型类型：

| 模型类型 | 代表 | Prompt 策略 |
|---|---|---|
| `sd` | SD 1.5 / SDXL / Pony 等 | 标签化、加权、负面提示词 |
| `diffusion` | zimage 等自然语言 diffusion 模型 | 自然语言段落、叙事感 |

`engine/image-prompt-builder.ts` 提供 `SDPromptBuilder` 和 `DiffusionPromptBuilder`，由 `data/page-spec.json` 中的 `imageGen.modelType` 决定。

### 6.4 从卡中提取生图规则

skill 在生成 IR 时新增 `imageGenRules` 字段，解析来源包括：

| 来源 | 解析目标 |
|---|---|
| 卡内“驱动模式”“触发时机”“核心戒律”等区块 | 触发模式（节点驱动 / 情境驱动 / 多视角） |
| `<pic>` 标签、图片声明格式 | 输出格式与数量要求 |
| 角色详述模块、C.3 等固定字段 | 必须保留的固定属性 |
| 场景状态继承 (SCST) 声明 | 同一场景下禁止变更的动态属性 |
| Prompt 净化规则 | 负面词/占位词黑名单 |

### 6.5 自动触发时机

`engine/events.ts` 读取 `imageGen.triggers`：

- 节点驱动：场景切换、姿势改变、高潮、射精等事件发生时触发。
- 情境驱动：角色描写、情绪延续、特写等状态持续时触发。
- 多视角兜底：正文内容不足时，自动生成环境镜头、POV、细节特写、后果延续等视角图。

### 6.6 用户自定义工作流

不强制探测模型类型，完全由用户配置：

```json
{
  "imageGen": {
    "enabled": true,
    "provider": "comfyui",
    "endpoint": "http://127.0.0.1:8188",
    "modelType": "sd",
    "workflow": "workflows/my-workflow.json",
    "promptTemplate": "templates/comfyui-prompt-sd.txt",
    "promptNodeId": "3",
    "basePrompt": "masterpiece, best quality, ...",
    "negativePrompt": "worst quality, ...",
    "outputDir": "web/public/generated"
  }
}
```

用户导入自定义 ComfyUI workflow：

1. 从 ComfyUI 导出 API workflow。
2. 放入 `workflows/` 目录。
3. 在 `data/page-spec.json` 中修改 `imageGen.workflow`。
4. 如果 prompt 输入节点不是默认节点名，在 `promptNodeId` 中指定。

### 6.7 Prompt 构建规则

- 固定属性（发色、肤色、瞳色、胸部大小、身材等）从角色卡读取，禁止 LLM 改写。
- 动态属性（发型、服装）继承当前场景状态。
- 净化：过滤 `no`、`without`、`none`、`unknown` 等词。
- 负面提示词由配置指定，不硬塞卡内未声明的限制。

## 7. Skill 工作流程更新

### 7.1 新流程

```txt
解包卡片
  → 生成 card-ir.json（新增 UI 语义提取）
  → Runtime Plan（新增 frontend extension 和 image-gen 评估）
  → 生成 page-spec.json
  → 生成 engine/tools（已有）
  → 生成 web/ 前端项目
  → 生成 workflows/ 与 templates/
  → 用户确认后写代码
```

### 7.2 SKILL.md 入口调整

开工步骤新增：

1. 如果用户要求页面/生图，先读 `references/frontend-design.md` 和 `references/image-generation.md`。
2. 审计卡中是否存在前端面板、HTML 状态栏、文生图规则、C.3 角色详述等 UI 相关内容。

### 7.3 新增 References 文档

- `references/frontend-design.md`：页面主题、组件、page-spec 格式。
- `references/image-generation.md`：ComfyUI 接入、prompt 构建、工作流导入。
- `references/ui-semantic-extraction.md`：如何从卡中提取 UI 相关语义。

### 7.4 新增生成脚本

- `scripts/generate_page_spec.py`：从 `card-ir.json` 生成 `data/page-spec.json`。
- `scripts/validate_page_spec.py`：校验 page-spec 结构。
- `scripts/setup_frontend.py`：根据 page-spec 生成 `web/` 目录和基础 Next.js 文件。

### 7.5 增量更新策略

- 不覆盖用户自定义的 `workflows/*.json` 和 `templates/*.txt`。
- `data/page-spec.json` 可增量更新，保留用户手动修改的 `imageGen` 配置。
- `web/` 中用户新增的文件不会被删除，skill 生成的文件覆盖前需用户确认。

## 8. 测试与验收

### 8.1 单元测试

skill 新增 `tests/` 目录：

- `test_extract_ui_semantics.py`
- `test_page_spec_generation.py`
- `test_image_prompt_builder.py`
- `test_theme_selector.py`

### 8.2 前端构建测试

```bash
cd web && npm install && npm run build
```

确保 TypeScript 类型检查、Tailwind 主题配置、API Route 编译通过。

### 8.3 集成测试

使用示例角色卡跑完整流程：

```bash
python3 scripts/extract_card.py fixtures/sample-card.png card.json
python3 scripts/generate_page_spec.py card.json
python3 scripts/setup_frontend.py
cd web && npm run build
```

### 8.4 下场测试

- 启动 pi，加载生成的项目。
- 验证页面能读取 state 并展示。
- 调用一次工具，确认 state 更新并反映到页面。
- 如果开启 imageGen，验证 ComfyUI 调用成功，图片出现在 Gallery 中。
- 玩 20-30 轮，检查页面渲染、状态同步、图片生成无异常。

### 8.5 验收清单

- [ ] `data/page-spec.json` 与 `data/card-ir.json` 一致。
- [ ] `web/` 能独立构建。
- [ ] extension 能启动 web server 并提供 `/api/state`、`/api/tools`、`/api/events`。
- [ ] 页面主题与角色卡题材/风格匹配。
- [ ] 状态面板只展示 player-visible 字段。
- [ ] image-gen 工具仅在开启时注册，且 prompt 符合模型类型。
- [ ] 自定义 ComfyUI workflow 能被正确加载和注入 prompt。
- [ ] 下场 20-30 轮无严重错误。

## 9. 风险与回退

| 风险 | 影响 | 回退策略 |
|---|---|---|
| pi extension 不允许长期监听端口 | 前后端通信失败 | 回退到静态导出页面，只读展示 state/state.json |
| ComfyUI 未启动或配置错误 | 生图功能不可用 | 关闭 `imageGen.enabled`，不影响核心 gameplay |
| 主题/风格提取不准确 | 页面与卡气质不符 | 用户可手动编辑 `data/page-spec.json` 覆盖 |
| 新增产物过多导致 skill 复杂度上升 | 维护成本增加 | 保持模块化，页面和生图作为可选增量能力 |
