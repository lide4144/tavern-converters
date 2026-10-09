#!/usr/bin/env python3
"""根据 page-spec.json 生成 Next.js 前端项目脚手架。

Usage:
    python3 setup_frontend.py [--force] data/page-spec.json
"""

import argparse
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

NEXT_ENV_D_TS = """/// <reference types="next" />
/// <reference types="next/image-types/global" />

// NOTE: This file should not be edited
// see https://nextjs.org/docs/basic-features/typescript for more information.
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
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        background: 'var(--background)',
        surface: 'var(--surface)',
        primary: 'var(--primary)',
        text: 'var(--text)',
        accent: 'var(--accent)',
      },
    },
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

PAGE_TSX = """import fs from 'fs/promises';
import path from 'path';
import { PageSpec } from '@/lib/page-spec';
import { CharacterPanel } from '@/components/CharacterPanel';
import { StatePanel } from '@/components/StatePanel';
import { SceneLog } from '@/components/SceneLog';
import { ImageGenButton } from '@/components/ImageGenButton';
import { Gallery } from '@/components/Gallery';

function fallbackSpec(): PageSpec {
  return {
    version: 1,
    theme: { id: 'modern', base: 'modern', colors: {}, fonts: {} },
    layout: {},
    components: [],
  };
}

async function loadSpec(): Promise<PageSpec> {
  try {
    const file = path.join(process.cwd(), 'public', 'page-spec.json');
    const raw = await fs.readFile(file, 'utf-8');
    return JSON.parse(raw) as PageSpec;
  } catch {
    try {
      const res = await fetch('http://127.0.0.1:3001/page-spec.json', { next: { revalidate: 0 } });
      if (!res.ok) return fallbackSpec();
      return res.json();
    } catch {
      return fallbackSpec();
    }
  }
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

THEME_INDEX_TS = """export interface Theme {
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

export * from "./fantasy";
export * from "./scifi";
export * from "./modern";
export * from "./horror";
export * from "./romance";

import { fantasy } from "./fantasy";
import { scifi } from "./scifi";
import { modern } from "./modern";
import { horror } from "./horror";
import { romance } from "./romance";

export const themes: Record<string, Theme> = {
  fantasy,
  scifi,
  modern,
  horror,
  romance,
};

export function getTheme(id: string): Theme {
  return themes[id] || themes.modern;
}
"""

THEME_FANTASY_TS = """import { Theme } from "./index";

export const fantasy: Theme = {
  id: "fantasy",
  base: "fantasy",
  colors: {
    background: "#faf6e9",
    surface: "#f0e6c8",
    primary: "#8b5a2b",
    text: "#3d2b1f",
    accent: "#d4af37",
  },
  fonts: { heading: "serif", body: "serif" },
};
"""

THEME_SCIFI_TS = """import { Theme } from "./index";

export const scifi: Theme = {
  id: "scifi",
  base: "scifi",
  colors: {
    background: "#0b0f19",
    surface: "#151b2b",
    primary: "#22d3ee",
    text: "#e2e8f0",
    accent: "#a855f7",
  },
  fonts: { heading: "sans-serif", body: "sans-serif" },
};
"""

THEME_MODERN_TS = """import { Theme } from "./index";

export const modern: Theme = {
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
};
"""

THEME_HORROR_TS = """import { Theme } from "./index";

export const horror: Theme = {
  id: "horror",
  base: "horror",
  colors: {
    background: "#0a0a0a",
    surface: "#171717",
    primary: "#dc2626",
    text: "#f5f5f5",
    accent: "#7f1d1d",
  },
  fonts: { heading: "sans-serif", body: "sans-serif" },
};
"""

THEME_ROMANCE_TS = """import { Theme } from "./index";

export const romance: Theme = {
  id: "romance",
  base: "romance",
  colors: {
    background: "#fff1f2",
    surface: "#ffe4e6",
    primary: "#e11d48",
    text: "#881337",
    accent: "#fb7185",
  },
  fonts: { heading: "serif", body: "serif" },
};
"""

THEME_PROVIDER_TSX = """"use client";

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
"""

THEME_FILES = {
    "index.ts": THEME_INDEX_TS,
    "fantasy.ts": THEME_FANTASY_TS,
    "scifi.ts": THEME_SCIFI_TS,
    "modern.ts": THEME_MODERN_TS,
    "horror.ts": THEME_HORROR_TS,
    "romance.ts": THEME_ROMANCE_TS,
}


PAGE_SPEC_TS = """export interface PageSpec {
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
"""

CHARACTER_PANEL_TSX = """"use client";

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
"""

STATE_PANEL_TSX = """"use client";

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
"""

SCENE_LOG_TSX = """"use client";

import { PageSpec } from "@/lib/page-spec";

export function SceneLog({ spec }: { spec: PageSpec }) {
  return (
    <section className="p-4 rounded-lg" style={{ backgroundColor: "var(--surface)" }}>
      <h2 className="text-xl font-bold mb-2">剧情日志</h2>
      <p className="text-sm opacity-80">此处将展示最近的场景与事件。</p>
    </section>
  );
}
"""

ACTION_BAR_TSX = """"use client";

import { PageSpec } from "@/lib/page-spec";

export function ActionBar({ spec }: { spec: PageSpec }) {
  async function dispatch(action: string) {
    await fetch("/api/events", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ event: { type: action } }),
    });
  }

  return (
    <section className="p-4 rounded-lg" style={{ backgroundColor: "var(--surface)" }}>
      <h2 className="text-xl font-bold mb-2">行动</h2>
      <div className="flex gap-2">
        <button
          className="px-4 py-2 rounded text-white"
          style={{ backgroundColor: "var(--primary)" }}
          onClick={() => dispatch("roll_dice")}
        >
          投骰子
        </button>
        <button
          className="px-4 py-2 rounded text-white"
          style={{ backgroundColor: "var(--accent)" }}
          onClick={() => dispatch("advance_scene")}
        >
          推进场景
        </button>
      </div>
    </section>
  );
}
"""

IMAGE_GEN_BUTTON_TSX = """"use client";

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
"""

GALLERY_TSX = """"use client";

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
"""

API_STATE_ROUTE_TS = """import { NextRequest, NextResponse } from "next/server";

const EXTENSION_PORT = process.env.NEXT_PUBLIC_TAVERN2AGENT_PORT || "3001";

export async function GET(_req: NextRequest) {
  try {
    const res = await fetch(`http://127.0.0.1:${EXTENSION_PORT}/state`, { cache: "no-store" });
    if (!res.ok) throw new Error("extension state error");
    return NextResponse.json(await res.json());
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 503 });
  }
}
"""

API_TOOLS_ROUTE_TS = """import { NextRequest, NextResponse } from "next/server";

const EXTENSION_PORT = process.env.NEXT_PUBLIC_TAVERN2AGENT_PORT || "3001";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const res = await fetch(`http://127.0.0.1:${EXTENSION_PORT}/tools`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error("extension tool error");
    return NextResponse.json(await res.json());
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 503 });
  }
}
"""

API_EVENTS_ROUTE_TS = """import { NextRequest, NextResponse } from "next/server";

const EXTENSION_PORT = process.env.NEXT_PUBLIC_TAVERN2AGENT_PORT || "3001";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const res = await fetch(`http://127.0.0.1:${EXTENSION_PORT}/events`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error("extension event error");
    return NextResponse.json(await res.json());
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 503 });
  }
}
"""

IMAGE_PROMPT_BUILDER_TEST = """import { describe, it, expect } from 'vitest';
import { getPromptBuilder } from '../engine/image-prompt-builder';

describe('image prompt builder', () => {
  const ctx = {
    subject: 'character' as const,
    characterName: '艾莉娅',
    fixedAttributes: { hairColor: 'red hair', eyeColor: 'green eyes' },
    dynamicAttributes: { hairstyle: 'long hair' },
    styleBoost: ['fantasy'],
  };
  const config = {
    modelType: 'sd' as const,
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

VITEST_CONFIG_TS = """import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'node',
    globals: true,
  },
});
"""


def validate_input(page_spec_path: str) -> Path:
    """Validate that the input file exists and is valid JSON."""
    spec_path = Path(page_spec_path)
    if not spec_path.exists():
        print(f"Error: page-spec file not found: {page_spec_path}", file=sys.stderr)
        sys.exit(3)
    if not spec_path.is_file():
        print(f"Error: page-spec path is not a file: {page_spec_path}", file=sys.stderr)
        sys.exit(3)
    try:
        spec_path.read_text(encoding="utf-8")
    except PermissionError as exc:
        print(f"Error: cannot read page-spec file ({exc})", file=sys.stderr)
        sys.exit(5)
    try:
        with spec_path.open(encoding="utf-8") as f:
            json.load(f)
    except json.JSONDecodeError as exc:
        print(f"Error: invalid JSON in page-spec file: {exc}", file=sys.stderr)
        sys.exit(4)
    except PermissionError as exc:
        print(f"Error: cannot read page-spec file ({exc})", file=sys.stderr)
        sys.exit(5)
    return spec_path


def setup_frontend(page_spec_path: str, force: bool = False, web_dir: str = "web") -> None:
    spec_path = validate_input(page_spec_path)

    root = Path(web_dir)
    if root.exists():
        if not force:
            print(
                f"Warning: {root} already exists. Use --force to overwrite.",
                file=sys.stderr,
            )
            sys.exit(2)
        shutil.rmtree(root)
    root.mkdir(parents=True)

    (root / "package.json").write_text(PACKAGE_JSON, encoding="utf-8")
    (root / "next.config.js").write_text(NEXT_CONFIG, encoding="utf-8")
    (root / "next-env.d.ts").write_text(NEXT_ENV_D_TS, encoding="utf-8")
    (root / "tsconfig.json").write_text(TS_CONFIG, encoding="utf-8")
    (root / "tailwind.config.ts").write_text(TAILWIND_CONFIG, encoding="utf-8")
    (root / "postcss.config.js").write_text(POSTCSS_CONFIG, encoding="utf-8")
    (root / "app").mkdir(parents=True)
    (root / "app" / "globals.css").write_text(GLOBALS_CSS, encoding="utf-8")
    (root / "app" / "layout.tsx").write_text(LAYOUT_TSX, encoding="utf-8")
    (root / "app" / "page.tsx").write_text(PAGE_TSX, encoding="utf-8")
    (root / "components").mkdir(parents=True)
    (root / "components" / "ThemeProvider.tsx").write_text(THEME_PROVIDER_TSX, encoding="utf-8")
    (root / "lib").mkdir(parents=True)
    (root / "lib" / "page-spec.ts").write_text(PAGE_SPEC_TS, encoding="utf-8")
    (root / "themes").mkdir(parents=True)
    for filename, content in THEME_FILES.items():
        (root / "themes" / filename).write_text(content, encoding="utf-8")
    (root / "app" / "api").mkdir(parents=True)
    (root / "app" / "api" / "state").mkdir(parents=True)
    (root / "app" / "api" / "tools").mkdir(parents=True)
    (root / "app" / "api" / "events").mkdir(parents=True)
    (root / "public").mkdir(parents=True)

    # Components
    (root / "components" / "CharacterPanel.tsx").write_text(CHARACTER_PANEL_TSX, encoding="utf-8")
    (root / "components" / "StatePanel.tsx").write_text(STATE_PANEL_TSX, encoding="utf-8")
    (root / "components" / "SceneLog.tsx").write_text(SCENE_LOG_TSX, encoding="utf-8")
    (root / "components" / "ActionBar.tsx").write_text(ACTION_BAR_TSX, encoding="utf-8")
    (root / "components" / "ImageGenButton.tsx").write_text(IMAGE_GEN_BUTTON_TSX, encoding="utf-8")
    (root / "components" / "Gallery.tsx").write_text(GALLERY_TSX, encoding="utf-8")

    # API Routes
    (root / "app" / "api" / "state" / "route.ts").write_text(API_STATE_ROUTE_TS, encoding="utf-8")
    (root / "app" / "api" / "tools" / "route.ts").write_text(API_TOOLS_ROUTE_TS, encoding="utf-8")
    (root / "app" / "api" / "events" / "route.ts").write_text(API_EVENTS_ROUTE_TS, encoding="utf-8")

    # Prompt builder test scaffold
    (root / "image-prompt-builder.test.ts").write_text(IMAGE_PROMPT_BUILDER_TEST, encoding="utf-8")
    (root / "vitest.config.ts").write_text(VITEST_CONFIG_TS, encoding="utf-8")

    # 复制 page-spec.json 到 public 供开发时读取
    shutil.copy(spec_path, root / "public" / "page-spec.json")

    print(f"Frontend scaffold created at {root}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate a Next.js frontend scaffold from a page-spec.json file."
    )
    parser.add_argument("page_spec", help="Path to the page-spec.json file")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Remove and regenerate the web/ directory if it already exists",
    )
    parser.add_argument(
        "--web-dir",
        dest="web_dir",
        default="web",
        help="Output directory for the generated frontend (default: web)",
    )
    args = parser.parse_args()

    setup_frontend(args.page_spec, force=args.force, web_dir=args.web_dir)


if __name__ == "__main__":
    main()
