import http from "http";
import fs from "fs";
import path from "path";

// ExtensionContext 应替换为实际 pi extension API 提供的 context 类型。
// 此处使用最小接口，方便在缺少 pi 类型包时通过类型检查。
export interface ExtensionContext {
  workspaceState: {
    update: (key: string, value: any) => Promise<void> | void;
  };
}

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

  server.listen(0, "127.0.0.1");
  const address = server.address();
  const port = typeof address === "object" && address ? address.port : 0;

  const portFile = path.join(process.cwd(), ".pi", "web-port.json");
  fs.mkdirSync(path.dirname(portFile), { recursive: true });
  fs.writeFileSync(portFile, JSON.stringify({ port }, null, 2));

  context.workspaceState.update("tavern2agent.webPort", port);

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
