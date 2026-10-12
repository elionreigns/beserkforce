from __future__ import annotations

import os
import shutil
import subprocess
from typing import Any


PROVIDERS = [
    {"id": "codex", "commands": ["codex"], "key": "OPENAI_API_KEY"},
    {"id": "openai", "commands": ["openai"], "key": "OPENAI_API_KEY"},
    {"id": "grok", "commands": ["grok"], "key": "XAI_API_KEY"},
    {"id": "opencode", "commands": ["opencode"], "key": None},
    {"id": "blessor", "commands": ["blessor"], "key": None},
]


def _version(path: str) -> str:
    for flag in ("--version", "version"):
        try:
            result = subprocess.run(
                [path, flag], capture_output=True, text=True, timeout=3, check=False
            )
            value = (result.stdout or result.stderr).strip().splitlines()
            if value:
                return value[0][:180]
        except (OSError, subprocess.SubprocessError):
            continue
    return "installed; version unavailable"


def discover_providers() -> list[dict[str, Any]]:
    discovered = []
    for spec in PROVIDERS:
        path = next((shutil.which(command) for command in spec["commands"] if shutil.which(command)), None)
        discovered.append({
            "id": spec["id"],
            "installed": bool(path),
            "path": path,
            "version": _version(path) if path else None,
            "credentialEnvironmentPresent": bool(spec["key"] and os.environ.get(spec["key"])),
            "credentialEnvironmentName": spec["key"],
            "capability": "detected-only; no autonomous execution adapter enabled",
        })
    return discovered

