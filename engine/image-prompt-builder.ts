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
      for (const value of Object.values(ctx.fixedAttributes)) {
        tags.push(value);
      }
      for (const value of Object.values(ctx.dynamicAttributes)) {
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
