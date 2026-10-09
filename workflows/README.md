# ComfyUI 工作流

本目录存放 ComfyUI API 工作流 JSON。

## 导入自定义工作流

1. 在 ComfyUI 中搭建或加载你的工作流。
2. 点击 **Workflow → Export (API)**，保存为 JSON。
3. 将 JSON 放到 `workflows/` 目录。
4. 在 `data/page-spec.json` 中修改：
   - `imageGen.workflow`：指向你的 JSON 文件。
   - `imageGen.promptNodeId`：写入正向提示词节点的 ID（默认 `3`）。
   - `imageGen.modelType`：`sd` 或 `diffusion`。
5. 将 `imageGen.enabled` 设为 `true`。

## 默认工作流

- `comfyui-sd.json`：面向 SD 1.5 / SDXL / Pony 等标签化模型的示例。
- `comfyui-diffusion.json`：面向自然语言 diffusion 模型的示例（结构相同，仅默认提示词不同）。

## 注意事项

- 默认工作流中的 `ckpt_name` 是占位符 `model.safetensors`，使用前请替换为你的真实模型文件名。
- 正向提示词节点 ID 默认为 `3`；若你的工作流中不是 `3`，请同步修改 `promptNodeId`。
- 不建议探测模型类型，完全由用户在 `data/page-spec.json` 中配置。
