from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


AUTHORITY = """AUTHORITY:
- You may inspect, code, test, draft, and write artifacts inside BeserkForce.
- Treat parent WorkForce and every GrokBot folder as read-only.
- Never send outreach, publish, deploy, spend, book, alter accounts, or push Git.
- If external action would be useful, create an internal decision packet and set approvalRequired=true.
- Never convert UNKNOWN metrics to zero or estimates.
- Never claim a sale without verified booking record, asn=elion attribution, operator/FareHarbor confirmation, and Eric confirmation."""


def _decode(value: bytes | None) -> str:
    if not value:
        return ""
    return value.decode("utf-8", errors="replace")


def _run(command: list[str], cwd: Path, stdin: str | None, timeout: int) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        cwd=cwd,
        input=(stdin or "").encode("utf-8"),
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def extract_json_object(text: str) -> dict[str, Any] | None:
    """Return the last balanced top-level JSON object in text, or None."""
    depth = 0
    start: int | None = None
    in_string = False
    escaped = False
    candidate: str | None = None
    for index, char in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            if depth == 0:
                start = index
            depth += 1
        elif char == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start is not None:
                candidate = text[start:index + 1]
    if candidate is None:
        return None
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def opencode_text(stdout: str) -> str:
    """Pull assistant text out of `opencode run --format json` event output."""
    chunks: list[str] = []
    for line in (stdout or "").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        part = event.get("part")
        if not isinstance(part, dict):
            part = event.get("properties", {}).get("part") if isinstance(event.get("properties"), dict) else {}
        if not isinstance(part, dict):
            part = {}
        if str(part.get("type") or "").lower() in {"reasoning", "thinking", "step-start", "step-finish", "tool"}:
            continue
        kind = str(event.get("type") or "").lower()
        if kind in {"reasoning", "thinking"}:
            continue
        text = part.get("text") or event.get("text") or ""
        if isinstance(text, str) and text.strip() and kind in {"text", "message", "assistant"}:
            chunks.append(text.strip())
    return clean_reply("\n\n".join(chunks))


REASONING_BLOCK = re.compile(r"<\s*(thinking|think)\s*>.*?<\s*/\s*(thinking|think)\s*>", re.DOTALL | re.IGNORECASE)
REASONING_TAG = re.compile(r"<\s*/?\s*(thinking|think)\s*>", re.IGNORECASE)
REASONING_LINE = re.compile(r"(?im)^[ \t]*(thinking|think)[ \t]*$")
LEADING_TAG = re.compile(r"^\s*<\s*/?\s*(thinking|think)\s*>", re.IGNORECASE)


def clean_reply(text: str) -> str:
    """Remove leaked reasoning wrappers/tags from a model reply."""
    value = text or ""
    value = REASONING_BLOCK.sub("", value)
    value = REASONING_TAG.sub("", value)
    value = REASONING_LINE.sub("", value)
    value = LEADING_TAG.sub("", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def _job_header(job: dict[str, Any], role: dict[str, Any]) -> str:
    return (
        f"JOB ID: {job['jobId']}\n"
        f"ROLE {role['id']}: {role['name']} — {role['title']}\n"
        f"OBJECTIVE: {job['objective']}\n"
        f"DELIVERABLE: {job['deliverable']}\n"
        f"SUCCESS CRITERIA: {json.dumps(job['successCriteria'], ensure_ascii=False)}"
    )


class CodexBrain:
    """Safe internal-work adapter for the installed Codex CLI."""

    def __init__(self, root: Path):
        self.root = root
        self.executable = shutil.which("codex")
        self.schema = root / "config" / "codex-result.schema.json"

    def identity(self) -> dict[str, Any]:
        return {
            "id": "codex-beserkforce",
            "name": "Codex",
            "provider": "OpenAI Codex CLI",
            "role": "primary conductor brain",
            "installed": bool(self.executable),
            "path": self.executable,
            "mode": "internal workspace-write; external actions remain approval-gated",
            "capabilities": ["plan", "route", "code", "review", "verify", "produce internal artifacts"],
        }

    def prompt_for(self, job: dict[str, Any], role: dict[str, Any]) -> str:
        return f"""You are the primary conductor brain for BeserkForce.

Execute this one bounded internal job inside the BeserkForce folder.

{_job_header(job, role)}

{AUTHORITY}

Return only the structured result required by config/codex-result.schema.json.
"""

    def command_for(self, job: dict[str, Any], role: dict[str, Any], output: Path) -> list[str]:
        if not self.executable:
            raise RuntimeError("Codex CLI is not installed or not on PATH")
        return [
            self.executable,
            "exec",
            "--cd", str(self.root),
            "--sandbox", "workspace-write",
            "--skip-git-repo-check",
            "--ephemeral",
            "--output-schema", str(self.schema),
            "--output-last-message", str(output),
            self.prompt_for(job, role),
        ]

    def dispatch(self, job: dict[str, Any], role: dict[str, Any], output: Path, timeout: int = 900) -> dict[str, Any]:
        output.parent.mkdir(parents=True, exist_ok=True)
        process = _run(self.command_for(job, role, output), self.root, None, timeout)
        if process.returncode != 0:
            raise RuntimeError((_decode(process.stderr) or _decode(process.stdout) or "Codex dispatch failed")[-4000:])
        try:
            return json.loads(output.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError(f"Codex returned no valid structured result: {error}") from error

    def converse(self, message: str, write: bool = True, timeout: int = 600) -> str:
        if not self.executable:
            raise RuntimeError("Codex CLI is not installed or not on PATH")
        prompts = self.root / "data" / "runtime" / "chat"
        prompts.mkdir(parents=True, exist_ok=True)
        command = [
            self.executable, "exec",
            "--cd", str(self.root),
            "--skip-git-repo-check",
            "--color", "never",
            "--sandbox", "workspace-write" if write else "read-only",
            "-",
        ]
        process = _run(command, self.root, message, timeout)
        reply = clean_reply(_decode(process.stdout))
        if not reply:
            raise RuntimeError((_decode(process.stderr) or "Codex returned an empty reply")[-4000:])
        return reply[-20000:]


class OpenCodeBrain:
    """Bounded internal-work adapter for the installed OpenCode CLI."""

    DEFAULT_MODEL = "opencode/big-pickle"

    def __init__(self, root: Path, model: str = DEFAULT_MODEL):
        self.root = root
        self.executable = shutil.which("opencode")
        self.model = model

    def identity(self) -> dict[str, Any]:
        return {
            "id": "opencode-beserkforce",
            "name": "OpenCode",
            "provider": "OpenCode CLI",
            "role": "secondary conductor brain",
            "installed": bool(self.executable),
            "path": self.executable,
            "model": self.model,
            "mode": "internal workspace-write; external actions remain approval-gated",
            "capabilities": ["plan", "route", "code", "review", "verify", "chat", "produce internal artifacts"],
        }

    def prompt_for(self, job: dict[str, Any], role: dict[str, Any], output: Path | None = None) -> str:
        prompt = f"""You are a conductor brain for BeserkForce.

Execute this one bounded internal job inside the BeserkForce folder.

{_job_header(job, role)}

{AUTHORITY}

Return only the structured result required by config/codex-result.schema.json.
"""
        if output is not None:
            prompt += f"\nWrite that exact JSON object to this file path as well: {output}\n"
        return prompt

    def command_for(self, job: dict[str, Any], role: dict[str, Any], output: Path) -> list[str]:
        if not self.executable:
            raise RuntimeError("OpenCode CLI is not installed or not on PATH")
        return [
            self.executable,
            "run",
            "--dir", str(self.root),
            "--format", "json",
            "--title", "BeserkForce",
            "--model", self.model,
            "--auto",
            self.prompt_for(job, role, output),
        ]

    def dispatch(self, job: dict[str, Any], role: dict[str, Any], output: Path, timeout: int = 1800) -> dict[str, Any]:
        output.parent.mkdir(parents=True, exist_ok=True)
        process = _run(self.command_for(job, role, output), self.root, None, timeout)
        result: Any = None
        try:
            result = json.loads(output.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            result = None
        if not isinstance(result, dict):
            result = extract_json_object(opencode_text(_decode(process.stdout)))
        if not isinstance(result, dict):
            raise RuntimeError((_decode(process.stderr) or _decode(process.stdout) or "OpenCode dispatch failed")[-4000:])
        return result

    def converse(self, message: str, write: bool = True, timeout: int = 900) -> str:
        if not self.executable:
            raise RuntimeError("OpenCode CLI is not installed or not on PATH")
        command = [
            self.executable,
            "run",
            "--dir", str(self.root),
            "--format", "json",
            "--title", "BeserkForce Chat",
            "--model", self.model,
        ]
        if write:
            command.append("--auto")
        command.append(message)
        process = _run(command, self.root, None, timeout)
        reply = opencode_text(_decode(process.stdout))
        if not reply:
            raise RuntimeError((_decode(process.stderr) or _decode(process.stdout) or "OpenCode returned an empty reply")[-4000:])
        return reply[-20000:]


class GrokBrain:
    """Bounded internal-work adapter for the installed Grok CLI."""

    DEFAULT_MODEL = "grok-4.7"

    def __init__(self, root: Path, model: str = DEFAULT_MODEL):
        self.root = root
        self.executable = shutil.which("grok")
        self.model = model
        self.schema = root / "config" / "codex-result.schema.json"

    def identity(self) -> dict[str, Any]:
        return {
            "id": "grok-beserkforce",
            "name": "Grok",
            "provider": "Grok CLI",
            "role": "conductor brain",
            "installed": bool(self.executable),
            "path": self.executable,
            "model": self.model,
            "mode": "internal workspace-write; external actions remain approval-gated",
            "capabilities": ["plan", "route", "code", "review", "verify", "chat", "produce internal artifacts"],
        }

    def prompt_for(self, job: dict[str, Any], role: dict[str, Any], output: Path | None = None) -> str:
        prompt = f"""You are a conductor brain for BeserkForce.

Execute this one bounded internal job inside the BeserkForce folder.

{_job_header(job, role)}

{AUTHORITY}

Return only the structured result required by config/codex-result.schema.json.
"""
        if output is not None:
            prompt += f"\nWrite that exact JSON object to this file path as well: {output}\n"
        return prompt

    def command_for(self, job: dict[str, Any], role: dict[str, Any], output: Path) -> list[str]:
        if not self.executable:
            raise RuntimeError("Grok CLI is not installed or not on PATH")
        prompt_path = output.with_name(output.stem + ".grok-prompt.txt")
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(self.prompt_for(job, role, output), encoding="utf-8")
        return [
            self.executable,
            "--cwd", str(self.root),
            "--no-alt-screen",
            "-m", self.model,
            "--permission-mode", "bypassPermissions",
            "--always-approve",
            "--json-schema", str(self.schema),
            "--prompt-file", str(prompt_path),
        ]

    def dispatch(self, job: dict[str, Any], role: dict[str, Any], output: Path, timeout: int = 900) -> dict[str, Any]:
        output.parent.mkdir(parents=True, exist_ok=True)
        process = _run(self.command_for(job, role, output), self.root, None, timeout)
        result: Any = None
        try:
            result = json.loads(output.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            result = None
        if not isinstance(result, dict):
            result = extract_json_object(_decode(process.stdout))
        if not isinstance(result, dict):
            raise RuntimeError((_decode(process.stderr) or _decode(process.stdout) or "Grok dispatch failed")[-4000:])
        return result

    def converse(self, message: str, write: bool = True, timeout: int = 900) -> str:
        if not self.executable:
            raise RuntimeError("Grok CLI is not installed or not on PATH")
        prompts = self.root / "data" / "runtime" / "chat"
        prompts.mkdir(parents=True, exist_ok=True)
        prompt_path = prompts / "grok-prompt.txt"
        prompt_path.write_text(message, encoding="utf-8")
        command = [
            self.executable,
            "--cwd", str(self.root),
            "--no-alt-screen",
            "--output-format", "plain",
            "-m", self.model,
            "--permission-mode", "bypassPermissions" if write else "plan",
        ]
        if write:
            command.append("--always-approve")
        command.extend(["--prompt-file", str(prompt_path)])
        process = _run(command, self.root, None, timeout)
        reply = clean_reply(_decode(process.stdout))
        if not reply:
            raise RuntimeError((_decode(process.stderr) or _decode(process.stdout) or "Grok returned an empty reply")[-4000:])
        return reply[-20000:]


BRAIN_CLASSES: dict[str, type] = {"codex": CodexBrain, "opencode": OpenCodeBrain, "grok": GrokBrain}


def build_brains(root: Path) -> dict[str, Any]:
    return {key: cls(root) for key, cls in BRAIN_CLASSES.items()}
