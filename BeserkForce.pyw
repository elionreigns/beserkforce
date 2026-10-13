"""BeserkForce desktop window. One app frame, no console, no browser tab.

The runtime still listens on 127.0.0.1 only. This file is the app the way
Sermon Feed is: pythonw + WebView2, with its own taskbar identity.
"""
from __future__ import annotations

import ctypes
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PORT = 8877
URL = f"http://127.0.0.1:{PORT}/"
TITLE = "BeserkForce"
STATE = ROOT / "data" / "runtime" / "window.json"
PID_FILE = ROOT / "data" / "beserkforce.pid"
LOG_DIR = ROOT / "data" / "logs"
ICON = ROOT / "web" / "assets" / "beserkforce.ico"
NOWIN = 0x08000000

try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ELionProductions.BeserkForce")
except Exception:
    pass


def focus_existing() -> bool:
    hwnd = ctypes.windll.user32.FindWindowW(None, TITLE)
    if not hwnd:
        return False
    ctypes.windll.user32.ShowWindow(hwnd, 9)
    ctypes.windll.user32.SetForegroundWindow(hwnd)
    return True


def healthy() -> bool:
    try:
        with urllib.request.urlopen(URL + "api/health", timeout=2) as response:
            body = response.read()
            return response.status == 200 and b'"ok"' in body and b'true' in body
    except Exception:
        return False


def load_state() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(window) -> None:
    try:
        if window.width < 300 or window.x < -10000:
            return
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(
            json.dumps({"x": window.x, "y": window.y, "width": window.width, "height": window.height}, indent=1),
            encoding="utf-8",
        )
    except Exception:
        pass


def set_window_icon() -> None:
    if not ICON.is_file():
        return
    user32 = ctypes.windll.user32
    hwnd = 0
    for _ in range(40):
        hwnd = user32.FindWindowW(None, TITLE)
        if hwnd:
            break
        time.sleep(0.25)
    if not hwnd:
        return
    for size, which in ((16, 0), (32, 1), (256, 1)):
        handle = user32.LoadImageW(None, str(ICON), 1, size, size, 0x10)
        if handle:
            user32.SendMessageW(hwnd, 0x80, which, handle)


def start_server() -> subprocess.Popen | None:
    if healthy():
        return None
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log = open(LOG_DIR / "server.out.log", "ab")
    process = subprocess.Popen(
        [sys.executable, str(ROOT / "app.py"), "serve"],
        cwd=str(ROOT),
        stdout=log,
        stderr=log,
        stdin=subprocess.DEVNULL,
        creationflags=NOWIN,
    )
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(process.pid), encoding="ascii")
    for _ in range(40):
        if healthy():
            return process
        if process.poll() is not None:
            break
        time.sleep(0.25)
    raise RuntimeError(f"BeserkForce did not answer {URL}api/health")


def main() -> int:
    if focus_existing():
        return 0
    import webview

    server = start_server()
    state = load_state()
    screen_w = ctypes.windll.user32.GetSystemMetrics(0)
    screen_h = ctypes.windll.user32.GetSystemMetrics(1)
    width = int(state.get("width", 1440))
    height = int(state.get("height", 900))
    x = state.get("x")
    y = state.get("y")
    if x is None or y is None or not (-50 < x < screen_w - 100 and -10 < y < screen_h - 100):
        x = max(0, (screen_w - width) // 2)
        y = max(0, (screen_h - height) // 2)
    window = webview.create_window(
        TITLE,
        URL,
        width=width,
        height=height,
        x=int(x),
        y=int(y),
        min_size=(1100, 720),
        background_color="#090a0d",
        text_select=True,
    )
    window.events.closing += lambda: save_state(window)
    import threading
    threading.Thread(target=set_window_icon, daemon=True).start()
    try:
        webview.start(gui="edgechromium", private_mode=False, storage_path=str(ROOT / "data" / "runtime" / "webview"))
    finally:
        save_state(window)
        if server and server.poll() is None:
            server.terminate()
            try:
                PID_FILE.unlink()
            except OSError:
                pass
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        (LOG_DIR / "app.err.log").write_text(str(error), encoding="utf-8")
        raise
