# 生图功能规范

## 启用条件

`data/page-spec.json` 中 `imageGen.enabled === true`。

## 后端

统一使用本地 ComfyUI：

1. 向 `POST {endpoint}/prompt` 提交 workflow。
2. 通过 `GET {endpoint}/history/{prompt_id}` 轮询结果。
3. 下载图片到 `imageGen.outputDir`（默认 `web/public/generated/`）。
4. 将图片路径写回 state，供 `Gallery` 组件展示。

## 模型类型

| 类型 | 代表 | Prompt 策略 |
|---|---|---|
| `sd` | SD 1.5 / SDXL / Pony 等 | 标签化、逗号分隔、加权 |
| `diffusion` | zimage 等自然语言 diffusion 模型 | 自然语言段落、叙事感 |

后端统一为 ComfyUI，差异仅在 prompt 构建策略与默认工作流。

## Prompt 构建规则

- 固定属性（发色、肤色、瞳色、胸部大小、身材等）从角色卡读取，禁止 LLM 改写。
- 动态属性（发型、服装、表情）继承当前场景状态。
- 过滤 `no`、`without`、`none`、`unknown` 等污染词。
- 负面提示词由 `imageGen.negativePrompt` 指定，不硬塞卡内未声明的限制。

## 用户自定义工作流

1. 在 ComfyUI 中搭建好工作流。
2. 点击 **Workflow → Export (API)**，保存为 JSON。
3. 将 JSON 放入 `workflows/`。
4. 在 `data/page-spec.json` 中修改：
   - `imageGen.workflow`: 文件路径
   - `imageGen.promptNodeId`: 正向提示词节点 ID（默认 `3`）
   - `imageGen.modelType`: `sd` 或 `diffusion`
5. 不强制探测模型，完全由用户配置。

## 触发规则

`imageGen.triggers` 描述自动触发时机：

- `eventDriven`: 节点驱动，如场景切换、姿势改变、战斗开始等事件发生。
- `stateDriven`: 情境驱动，如角色描写、情绪延续、特写等状态持续。
- `multiAngleFallback`: 多视角兜底，如环境镜头、POV、细节特写、后果延续。

页面同时提供 `ImageGenButton` 用于手动触发。

## 文件清单

- `engine/image-prompt-builder.ts`: prompt 构建器
- `tools/image-gen.ts`: 生图工具
- `workflows/comfyui-sd.json`: 默认 SD 工作流
- `workflows/comfyui-diffusion.json`: 默认 diffusion 工作流
- `templates/comfyui-prompt-sd.txt`: SD prompt 模板
- `templates/comfyui-prompt-diffusion.txt`: diffusion prompt 模板
