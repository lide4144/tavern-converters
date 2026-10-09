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
