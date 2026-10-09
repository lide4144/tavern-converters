#!/usr/bin/env python3
"""下场测试脚本：对生成的项目进行 20-30 轮事件/工具调用实测。

Usage:
    python3 scripts/field_test.py --project-dir 测试 --rounds 30
"""

import argparse
import json
import os
import random
import subprocess
import sys
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread


class MockExtensionHandler(BaseHTTPRequestHandler):
    """模拟 pi extension 的本地 HTTP server。"""

    state = {
        "character": {"name": "", "avatar": ""},
        "state": {
            "round": 0,
            "scene": [],
            "protagonist": {"name": "测试玩家"},
            "relationship": {},
            "economy": {"balance": 10000},
        },
        "images": [],
    }
    event_log = []

    def log_message(self, format, *args):
        pass

    def _send_json(self, code, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send_json(204, {})

    def do_GET(self):
        if self.path == "/state":
            self._send_json(200, self.state)
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid json"})
            return

        if self.path == "/events":
            event = payload.get("event", {})
            self.event_log.append(event)
            self._apply_event(event)
            self._send_json(200, {"accepted": True, "event": event})
        elif self.path == "/tools":
            tool = payload.get("tool")
            args = payload.get("args", {})
            result = self._call_tool(tool, args)
            self._send_json(200, result)
        else:
            self._send_json(404, {"error": "not found"})

    def _apply_event(self, event):
        t = event.get("type")
        if t == "advance_scene":
            self.state["state"]["round"] += 1
            self.state["state"]["scene"].append(f"第 {self.state['state']['round']} 轮场景推进")
        elif t == "roll_dice":
            self.state["state"]["last_roll"] = random.randint(1, 100)
        elif t == "place_order":
            self.state["state"]["economy"]["balance"] -= random.randint(50, 500)
            self.state["state"]["current_order"] = {"id": self.state["state"]["round"]}
        else:
            # 未知事件也推进轮次，避免卡住
            self.state["state"]["round"] += 1

    def _call_tool(self, tool, args):
        if tool == "generate_image":
            subject = args.get("subject", "character")
            path = f"/generated/mock-{subject}-{len(self.state['images'])}.png"
            self.state["images"].append({"path": path, "subject": subject})
            return {"success": True, "path": path}
        return {"error": f"unknown tool {tool}"}


def start_extension_server(port):
    server = HTTPServer(("127.0.0.1", port), MockExtensionHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def wait_for_server(url, timeout=60):
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as res:
                if res.status == 200:
                    return True
                last_error = f"HTTP {res.status}"
        except Exception as exc:
            last_error = str(exc)
        time.sleep(0.5)
    raise TimeoutError(f"Server did not respond in {timeout}s ({url}): {last_error}")


def start_next_server(web_dir, extension_port, next_port):
    env = os.environ.copy()
    env["NEXT_PUBLIC_TAVERN2AGENT_PORT"] = str(extension_port)
    env["PORT"] = str(next_port)
    log_path = Path(web_dir) / ".." / "next-dev.log"
    log_file = open(log_path, "w", encoding="utf-8")
    proc = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=web_dir,
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )
    return proc, log_file


def request_next(base_url, method, path, payload=None):
    url = f"{base_url}{path}"
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload else None
    req = urllib.request.Request(url, data=data, method=method)
    if data:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=10) as res:
        return res.status, json.loads(res.read().decode("utf-8"))


def main():
    parser = argparse.ArgumentParser(
        description="Run field test against a Tavern2Agent generated project."
    )
    parser.add_argument("--project-dir", default="测试", help="Generated project directory")
    parser.add_argument("--rounds", type=int, default=30, help="Number of rounds to run")
    parser.add_argument("--extension-port", type=int, default=3001, help="Mock extension server port")
    parser.add_argument("--next-port", type=int, default=3000, help="Next.js dev server port")
    args = parser.parse_args()

    project = Path(args.project_dir)
    web_dir = project / "web"
    if not web_dir.exists():
        print(f"Error: {web_dir} does not exist. Run setup_frontend.py first.", file=sys.stderr)
        sys.exit(2)

    print(f"[*] Starting mock extension server on port {args.extension_port}")
    ext_server = start_extension_server(args.extension_port)
    wait_for_server(f"http://127.0.0.1:{args.extension_port}/state")

    print(f"[*] Starting Next.js dev server in {web_dir} on port {args.next_port}")
    next_proc, log_file = start_next_server(web_dir, args.extension_port, args.next_port)
    base_url = f"http://127.0.0.1:{args.next_port}"
    try:
        wait_for_server(f"{base_url}/api/state")
    except TimeoutError:
        log_file.flush()
        print((project / "next-dev.log").read_text(encoding="utf-8")[-2000:], file=sys.stderr)
        next_proc.terminate()
        raise

    print(f"[*] Running {args.rounds} rounds of events/tools")
    actions = ["advance_scene", "roll_dice", "place_order", "generate_image"]
    failures = 0
    for i in range(1, args.rounds + 1):
        action = random.choice(actions)
        try:
            if action == "generate_image":
                status, body = request_next(
                    base_url,
                    "POST",
                    "/api/tools",
                    {"tool": "generate_image", "args": {"subject": random.choice(["character", "scene"])}},
                )
            else:
                status, body = request_next(
                    base_url,
                    "POST",
                    "/api/events",
                    {"event": {"type": action}},
                )
            if status != 200:
                failures += 1
                print(f"  Round {i:02d}: {action:15s} -> HTTP {status} {body}")
            else:
                print(f"  Round {i:02d}: {action:15s} -> OK")
        except Exception as exc:
            failures += 1
            print(f"  Round {i:02d}: {action:15s} -> ERROR {exc}")

    status, final_state = request_next(base_url, "GET", "/api/state")
    round_count = final_state.get("state", {}).get("round", 0)
    image_count = len(final_state.get("images", []))
    print(f"[*] Final state: round={round_count}, images={image_count}")

    print("[*] Stopping servers")
    next_proc.terminate()
    try:
        next_proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        next_proc.kill()
    log_file.close()
    ext_server.shutdown()

    if failures:
        print(f"[FAIL] {failures}/{args.rounds} rounds failed")
        sys.exit(1)
    print("[PASS] All rounds completed successfully")


if __name__ == "__main__":
    main()
