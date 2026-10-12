#!/usr/bin/env python3
"""BeserkForce local command server — standard library only."""
from __future__ import annotations

import argparse
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from beserkforce.core import Runtime


ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
CONFIG = json.loads((ROOT / "config" / "default.json").read_text(encoding="utf-8"))
RUNTIME = Runtime()


def health() -> dict:
    state = RUNTIME.status()
    return {key: state[key] for key in ("ok", "name", "stage", "version", "deviceId", "time", "authority")}


class Handler(BaseHTTPRequestHandler):
    server_version = "BeserkForce/0.1"

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"[{RUNTIME.now()}] {self.address_string()} {fmt % args}")

    def send_json(self, payload: object, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/health":
            self.send_json(health())
            return
        if path == "/api/status":
            self.send_json(RUNTIME.status())
            return
        if path == "/api/brains":
            self.send_json({"ok": True, "brains": RUNTIME.brains_status()})
            return
        if path == "/api/chat/threads":
            self.send_json({"ok": True, "threads": RUNTIME.chat_threads(), "current": RUNTIME.current_thread()})
            return
        relative = "index.html" if path == "/" else path.lstrip("/")
        target = (WEB / relative).resolve()
        if WEB.resolve() not in target.parents and target != WEB.resolve():
            self.send_error(403)
            return
        if not target.is_file():
            self.send_error(404)
            return
        body = target.read_bytes()
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", "0"))
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
            if path == "/api/demo":
                self.send_json(RUNTIME.run_safety_demo(), 201)
                return
            if path == "/api/jobs/claim":
                self.send_json(RUNTIME.claim_job(str(payload["jobId"]), str(payload["agentId"])), 200)
                return
            if path == "/api/chat":
                turn = RUNTIME.chat(str(payload.get("message", "")), str(payload.get("engine", "codex")), bool(payload.get("write", True)), int(payload.get("timeout", 900)))
                self.send_json({"ok": True, "turn": turn}, 201)
                return
            if path == "/api/chat/new":
                self.send_json({"ok": True, "thread": RUNTIME.new_chat(str(payload.get("title", "")))}, 201)
                return
            if path == "/api/chat/switch":
                self.send_json({"ok": True, "thread": RUNTIME.switch_chat(str(payload.get("threadId", "")))}, 200)
                return
            if path == "/api/approvals/decide":
                self.send_json(RUNTIME.decide_approval(str(payload["approvalId"]), str(payload["decision"]), str(payload["decidedBy"]), str(payload["actionHash"]), str(payload.get("note", ""))), 200)
                return
            self.send_json({"ok": False, "error": "Unknown endpoint"}, 404)
        except (ValueError, KeyError, RuntimeError, json.JSONDecodeError) as error:
            self.send_json({"ok": False, "error": str(error)}, 400)


def serve(host: str, port: int) -> None:
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"BeserkForce skeleton ready at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="BeserkForce local workforce runtime")
    parser.add_argument("command", nargs="?", choices=["serve", "health", "status", "demo", "brain", "brains", "dispatch", "chat"], default="serve")
    parser.add_argument("job_id", nargs="?")
    parser.add_argument("--engine", default="codex", help="brain engine for brain/dispatch/chat (codex or opencode)")
    parser.add_argument("--host", default=CONFIG["host"])
    parser.add_argument("--port", type=int, default=int(CONFIG["port"]))
    args = parser.parse_args()
    if args.command == "health":
        print(json.dumps(health(), indent=2))
    elif args.command == "status":
        print(json.dumps(RUNTIME.status(), indent=2))
    elif args.command == "demo":
        print(json.dumps(RUNTIME.run_safety_demo(), indent=2))
    elif args.command == "brains":
        print(json.dumps(RUNTIME.brains_status(), indent=2))
    elif args.command == "brain":
        job_id = args.job_id or "BF-HELI-50"
        print(json.dumps(RUNTIME.brain_plan(job_id, args.engine), indent=2))
    elif args.command == "dispatch":
        if not args.job_id:
            parser.error("dispatch requires a job_id")
        print(json.dumps(RUNTIME.dispatch_to_brain(args.job_id, args.engine), indent=2))
    elif args.command == "chat":
        message = args.job_id
        if not message:
            parser.error("chat requires a message")
        print(json.dumps(RUNTIME.chat(message, args.engine), indent=2))
    else:
        serve(args.host, args.port)


if __name__ == "__main__":
    main()

