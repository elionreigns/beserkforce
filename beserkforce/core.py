from __future__ import annotations

import hashlib
import json
import os
import re
import socket
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

from .brain import build_brains
from .providers import discover_providers


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "default.json"
TERMINAL_STATES = {"closed", "cancelled"}
EXTERNAL_ACTIONS = {"outreach", "publish", "deploy", "spend", "book", "account-change", "git-push"}
ALLOWED_STATES = {
    "ready", "claimed", "in-progress", "review", "ready-for-human", "approved",
    "executing", "externally-confirmed", "closed", "held", "blocked", "cancelled",
}


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else stable_json(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class AtomicStore:
    """Single-writer JSON store using an expiring cross-process lock file."""

    def __init__(self, root: Path, stale_seconds: int = 45):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock_path = self.root / ".write.lock"
        self.stale_seconds = stale_seconds

    @contextmanager
    def lock(self, timeout: float = 8.0):
        started = time.monotonic()
        token = {"pid": os.getpid(), "host": socket.gethostname(), "created": time.time()}
        while True:
            try:
                fd = os.open(str(self.lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(token, handle)
                break
            except FileExistsError:
                existing = load_json(self.lock_path, {})
                if time.time() - float(existing.get("created", 0)) > self.stale_seconds:
                    try:
                        self.lock_path.unlink()
                    except FileNotFoundError:
                        pass
                    continue
                if time.monotonic() - started > timeout:
                    raise TimeoutError("BeserkForce state is locked by another writer")
                time.sleep(0.05)
        try:
            yield
        finally:
            try:
                current = load_json(self.lock_path, {})
                if current == token:
                    self.lock_path.unlink()
            except FileNotFoundError:
                pass

    def path(self, name: str) -> Path:
        if not re.fullmatch(r"[a-z0-9_.-]+", name):
            raise ValueError("Unsafe state filename")
        return self.root / name

    def read(self, name: str, default: Any) -> Any:
        return load_json(self.path(name), default)

    def _write_unlocked(self, name: str, value: Any) -> None:
        target = self.path(name)
        temp = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
        temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(temp, target)

    def write(self, name: str, value: Any) -> None:
        with self.lock():
            self._write_unlocked(name, value)

    def mutate(self, name: str, default: Any, fn: Callable[[Any], Any]) -> Any:
        with self.lock():
            value = self.read(name, default)
            result = fn(value)
            self._write_unlocked(name, result)
            return result


class Runtime:
    def __init__(self, data_root: Path | None = None):
        self.config = load_json(DEFAULT_CONFIG, {})
        self.root = ROOT
        self.timezone = ZoneInfo(self.config.get("timezone", "Pacific/Honolulu"))
        self.data_root = data_root or ROOT / "data" / "runtime"
        self.store = AtomicStore(self.data_root)
        self.artifacts = self.data_root / "artifacts"
        self.evidence = self.data_root / "evidence"
        self.artifacts.mkdir(parents=True, exist_ok=True)
        self.evidence.mkdir(parents=True, exist_ok=True)
        self.brains = build_brains(ROOT)
        self.brain = self.brains["codex"]
        self.bootstrap()

    def now(self) -> str:
        return datetime.now(self.timezone).isoformat(timespec="seconds")

    @property
    def device_id(self) -> str:
        override = load_json(ROOT / "config" / "device.local.json", {}).get("deviceId")
        if override:
            return str(override)
        hostname = (os.environ.get("COMPUTERNAME") or socket.gethostname()).lower()
        return "elionpc" if hostname in {"elion", "elion-pc"} else "laptop"

    def registry(self, key: str, default: Any) -> Any:
        path = (ROOT / self.config[key]).resolve()
        return load_json(path, default)

    def roles(self) -> list[dict[str, Any]]:
        roles = self.registry("roleRegistry", {}).get("roles", [])
        return [role for role in roles if int(role.get("id", 0)) in range(50, 55)]

    def append_event(self, kind: str, detail: str, **extra: Any) -> dict[str, Any]:
        event = {"id": "EV-" + uuid.uuid4().hex[:12], "at": self.now(), "kind": kind, "detail": detail, **extra}
        self.store.mutate("events.json", [], lambda events: (events + [event])[-500:])
        return event

    def bootstrap(self) -> None:
        if not self.store.path("jobs.json").exists():
            jobs = []
            definitions = {
                50: ("Refresh the private-flight funnel baseline and select one measurable bottleneck.", "Current scoreboard and one prioritized internal decision packet."),
                51: ("Audit the private 18/30/60 mobile funnel against the canonical FareHarbor routes.", "Draft-only conversion and SEO audit; no deployment."),
                52: ("Map attribution from source through checkout and booking proof.", "Tracked experiment design with every cost and performance unknown labeled."),
                53: ("Create a public, platform-permitted high-intent signal review queue.", "Five sourced signal cards and unsent reply drafts."),
                54: ("Create a consent-first creator and travel-partner shortlist.", "Three sourced partner cards and one unsent proposal draft."),
            }
            for role_id, (objective, deliverable) in definitions.items():
                jobs.append({
                    "schemaVersion": 1,
                    "jobId": f"BF-HELI-{role_id}",
                    "campaignId": "BF-CAMPAIGN-HELI-FIRST-SALE",
                    "objective": objective,
                    "organizationId": "hawaii-flight-growth",
                    "leadRoleId": 50,
                    "producerRoleId": role_id,
                    "reviewerRoleId": 50 if role_id != 50 else 51,
                    "producerAgentId": None,
                    "deviceId": None,
                    "state": "ready",
                    "deliverable": deliverable,
                    "successCriteria": ["Artifact is evidence-backed", "Unknown values remain UNKNOWN", "No external action occurs without exact approval"],
                    "dataClass": "shared-internal",
                    "lease": None,
                    "approvalIds": [],
                    "artifactIds": [],
                    "evidenceIds": [],
                    "blocker": None,
                    "nextOwner": "BeserkForce dispatcher",
                    "createdAt": self.now(),
                    "updatedAt": self.now(),
                })
            self.store.write("jobs.json", jobs)
        if not self.store.path("campaigns.json").exists():
            self.store.write("campaigns.json", [{
                "campaignId": "BF-CAMPAIGN-HELI-FIRST-SALE",
                "name": "First verified private Oahu helicopter sale",
                "state": "active",
                "northStar": "One FareHarbor/operator-confirmed private booking attributed to asn=elion",
                "proofRequired": ["booking record", "asn=elion attribution", "operator or FareHarbor confirmation"],
                "activeExperimentLimit": 1,
                "createdAt": self.now(),
            }])
        defaults = {
            "approvals.json": [],
            "events.json": [],
            "artifacts.json": [],
            "evidence.json": [],
            "outcomes.json": [],
            "funnel.json": {
                "observedAt": self.now(),
                "listing": {"value": "LIVE", "status": "verified-public", "source": "helicoptertoursonoahu.com"},
                "privateProducts": {"value": [326050, 326066, 326071], "status": "verified-link-canon"},
                "attribution": {"value": "asn=elion", "status": "verified-link-canon"},
                "traffic": {"value": "UNKNOWN", "status": "needs-authorized-analytics"},
                "leads": {"value": "UNKNOWN", "status": "needs-owning-runtime"},
                "fareharborOpens": {"value": "UNKNOWN", "status": "needs-authorized-analytics"},
                "bookings": {"value": "UNKNOWN", "status": "needs-FareHarbor-or-operator-proof"},
                "compensation": {"value": "UNKNOWN", "status": "not-verified-in-canonical-WorkForce"},
                "bottleneck": {"value": "MEASUREMENT BASELINE", "status": "selected-with-incomplete-data"},
            },
        }
        for filename, value in defaults.items():
            if not self.store.path(filename).exists():
                self.store.write(filename, value)
        if not any(event.get("kind") == "runtime.bootstrapped" for event in self.store.read("events.json", [])):
            self.append_event("runtime.bootstrapped", "BeserkForce nerves initialized", deviceId=self.device_id)

    def jobs(self) -> list[dict[str, Any]]:
        return self.store.read("jobs.json", [])

    def _find_job(self, jobs: list[dict[str, Any]], job_id: str) -> dict[str, Any]:
        job = next((item for item in jobs if item.get("jobId") == job_id), None)
        if not job:
            raise ValueError(f"Unknown job: {job_id}")
        return job

    def create_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        role_id = int(payload["producerRoleId"])
        if role_id not in {int(role["id"]) for role in self.roles()}:
            raise ValueError("Job producer role is not registered in Hawaii Flight Growth")
        objective = str(payload.get("objective", "")).strip()
        if not objective:
            raise ValueError("Job objective is required")
        job = {
            "schemaVersion": 1, "jobId": payload.get("jobId") or "BF-" + uuid.uuid4().hex[:10].upper(),
            "campaignId": payload.get("campaignId"), "objective": objective,
            "organizationId": "hawaii-flight-growth", "leadRoleId": 50, "producerRoleId": role_id,
            "reviewerRoleId": payload.get("reviewerRoleId", 50), "producerAgentId": None, "deviceId": None,
            "state": "ready", "deliverable": str(payload.get("deliverable", "One verifiable internal artifact")),
            "successCriteria": payload.get("successCriteria") or ["Observable result recorded"],
            "dataClass": payload.get("dataClass", "shared-internal"), "lease": None,
            "approvalIds": [], "artifactIds": [], "evidenceIds": [], "blocker": None,
            "nextOwner": "BeserkForce dispatcher", "createdAt": self.now(), "updatedAt": self.now(),
        }
        def add(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
            if any(item.get("jobId") == job["jobId"] for item in jobs):
                raise ValueError("Duplicate job id")
            return jobs + [job]
        self.store.mutate("jobs.json", [], add)
        self.append_event("job.created", objective, jobId=job["jobId"], roleId=role_id)
        return job

    def claim_job(self, job_id: str, agent_id: str, lease_seconds: int = 900) -> dict[str, Any]:
        if not agent_id.strip():
            raise ValueError("agent_id is required")
        claimed: dict[str, Any] = {}
        now = datetime.now(self.timezone)
        def claim(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
            nonlocal claimed
            job = self._find_job(jobs, job_id)
            lease = job.get("lease") or {}
            expires = lease.get("expiresAt")
            active = False
            if expires:
                try:
                    active = datetime.fromisoformat(expires) > now
                except ValueError:
                    active = False
            if active and lease.get("agentId") != agent_id:
                raise ValueError(f"Job leased by {lease.get('agentId')}")
            if job["state"] in TERMINAL_STATES:
                raise ValueError("Terminal job cannot be claimed")
            job["producerAgentId"] = agent_id
            job["deviceId"] = self.device_id
            job["state"] = "claimed"
            job["lease"] = {"token": uuid.uuid4().hex, "agentId": agent_id, "deviceId": self.device_id, "claimedAt": self.now(), "expiresAt": (now + timedelta(seconds=lease_seconds)).isoformat(timespec="seconds")}
            job["nextOwner"] = agent_id
            job["updatedAt"] = self.now()
            claimed = dict(job)
            return jobs
        self.store.mutate("jobs.json", [], claim)
        self.append_event("job.claimed", f"Claimed by {agent_id}", jobId=job_id, deviceId=self.device_id)
        return claimed

    def transition(self, job_id: str, state: str, note: str = "") -> dict[str, Any]:
        if state not in ALLOWED_STATES:
            raise ValueError("Invalid job state")
        changed: dict[str, Any] = {}
        def update(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
            nonlocal changed
            job = self._find_job(jobs, job_id)
            if job["state"] in TERMINAL_STATES:
                raise ValueError("Terminal job cannot transition")
            if state == "closed" and job.get("campaignId") and not job.get("artifactIds"):
                raise ValueError("Campaign job needs an artifact before closing")
            job["state"] = state
            job["checkpoint"] = note or None
            job["updatedAt"] = self.now()
            if state in TERMINAL_STATES:
                job["lease"] = None
            changed = dict(job)
            return jobs
        self.store.mutate("jobs.json", [], update)
        self.append_event("job.transitioned", note or state, jobId=job_id, state=state)
        return changed

    def write_artifact(self, job_id: str, title: str, content: str, agent_id: str) -> dict[str, Any]:
        self._find_job(self.jobs(), job_id)
        artifact_id = "AR-" + uuid.uuid4().hex[:12]
        folder = self.artifacts / job_id
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{artifact_id}.md"
        payload = f"# {title}\n\n{content.strip()}\n"
        path.write_text(payload, encoding="utf-8")
        artifact = {"artifactId": artifact_id, "jobId": job_id, "title": title, "path": str(path.relative_to(self.data_root)), "sha256": digest(payload.encode("utf-8")), "agentId": agent_id, "createdAt": self.now()}
        self.store.mutate("artifacts.json", [], lambda values: values + [artifact])
        def attach(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
            job = self._find_job(jobs, job_id)
            job.setdefault("artifactIds", []).append(artifact_id)
            job["updatedAt"] = self.now()
            return jobs
        self.store.mutate("jobs.json", [], attach)
        self.append_event("artifact.written", title, jobId=job_id, artifactId=artifact_id)
        return artifact

    def request_approval(self, job_id: str, action_type: str, target: str, exact_action: str, cost: str = "UNKNOWN", risk: str = "") -> dict[str, Any]:
        if action_type not in EXTERNAL_ACTIONS:
            raise ValueError("Action type is not approval-gated")
        self._find_job(self.jobs(), job_id)
        action = {"actionType": action_type, "target": target.strip(), "exactAction": exact_action.strip(), "cost": cost.strip(), "risk": risk.strip()}
        if not action["target"] or not action["exactAction"]:
            raise ValueError("Target and exact action are required")
        approval = {"approvalId": "AP-" + uuid.uuid4().hex[:12], "jobId": job_id, "status": "pending", "action": action, "actionHash": digest(action), "requestedAt": self.now(), "decidedAt": None, "decidedBy": None, "decisionNote": None}
        self.store.mutate("approvals.json", [], lambda values: values + [approval])
        def attach(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
            self._find_job(jobs, job_id).setdefault("approvalIds", []).append(approval["approvalId"])
            return jobs
        self.store.mutate("jobs.json", [], attach)
        self.append_event("approval.requested", f"{action_type}: {target}", jobId=job_id, approvalId=approval["approvalId"], actionHash=approval["actionHash"])
        return approval

    def decide_approval(self, approval_id: str, decision: str, decided_by: str, expected_hash: str, note: str = "") -> dict[str, Any]:
        if decision not in {"approved", "denied"}:
            raise ValueError("Decision must be approved or denied")
        if decided_by.strip().lower() != "eric":
            raise ValueError("Only Eric can decide consequential actions")
        decided: dict[str, Any] = {}
        def update(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
            nonlocal decided
            approval = next((item for item in values if item.get("approvalId") == approval_id), None)
            if not approval:
                raise ValueError("Unknown approval")
            if approval["status"] != "pending":
                raise ValueError("Approval already decided")
            if expected_hash != approval["actionHash"] or digest(approval["action"]) != approval["actionHash"]:
                raise ValueError("Action hash mismatch; exact action changed")
            approval.update(status=decision, decidedAt=self.now(), decidedBy="Eric", decisionNote=note.strip() or None)
            decided = dict(approval)
            return values
        self.store.mutate("approvals.json", [], update)
        self.append_event("approval.decided", decision, approvalId=approval_id, jobId=decided["jobId"])
        return decided

    def add_evidence(self, job_id: str, evidence_type: str, reference: str, content: str, verified: bool = False) -> dict[str, Any]:
        self._find_job(self.jobs(), job_id)
        evidence_id = "PR-" + uuid.uuid4().hex[:12]
        path = self.evidence / f"{evidence_id}.txt"
        path.write_text(content.strip() + "\n", encoding="utf-8")
        item = {"evidenceId": evidence_id, "jobId": job_id, "type": evidence_type, "reference": reference, "path": str(path.relative_to(self.data_root)), "sha256": digest(path.read_bytes()), "verified": bool(verified), "observedAt": self.now()}
        self.store.mutate("evidence.json", [], lambda values: values + [item])
        def attach(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
            self._find_job(jobs, job_id).setdefault("evidenceIds", []).append(evidence_id)
            return jobs
        self.store.mutate("jobs.json", [], attach)
        self.append_event("evidence.added", evidence_type, jobId=job_id, evidenceId=evidence_id, verified=verified)
        return item

    def verify_helicopter_sale(self, job_id: str, confirmed_by: str, booking_reference: str) -> dict[str, Any]:
        if confirmed_by.strip().lower() != "eric":
            raise ValueError("Only explicit Eric confirmation can verify a real sale")
        job = self._find_job(self.jobs(), job_id)
        evidence = [item for item in self.store.read("evidence.json", []) if item.get("evidenceId") in job.get("evidenceIds", []) and item.get("verified")]
        types = {item["type"] for item in evidence}
        required = {"booking-record", "attribution", "operator-confirmation"}
        if not required <= types:
            raise ValueError("Verified booking-record, attribution and operator-confirmation evidence are required")
        outcome = {"outcomeId": "OUT-" + uuid.uuid4().hex[:12], "jobId": job_id, "campaignId": job.get("campaignId"), "type": "private-helicopter-booking", "status": "verified", "bookingReference": booking_reference.strip(), "evidenceIds": [item["evidenceId"] for item in evidence], "confirmedBy": "Eric", "confirmedAt": self.now()}
        if not outcome["bookingReference"]:
            raise ValueError("Booking reference is required")
        self.store.mutate("outcomes.json", [], lambda values: values + [outcome])
        self.transition(job_id, "externally-confirmed", "Verified helicopter booking")
        self.append_event("outcome.verified", "Private helicopter booking verified", jobId=job_id, outcomeId=outcome["outcomeId"])
        return outcome

    def run_safety_demo(self) -> dict[str, Any]:
        demo_id = "BF-DEMO-" + uuid.uuid4().hex[:6].upper()
        job = self.create_job({"jobId": demo_id, "producerRoleId": 50, "objective": "Prove the internal BeserkForce job lifecycle without external action.", "deliverable": "One locally hashed demonstration artifact."})
        self.claim_job(demo_id, "beserkforce-self-test", 60)
        self.transition(demo_id, "in-progress", "Writing local demonstration artifact")
        artifact = self.write_artifact(demo_id, "Lifecycle demonstration", "Created, claimed, checkpointed, hashed, reviewed and closed locally. No external action was attempted.", "beserkforce-self-test")
        self.transition(demo_id, "review", "Artifact hash recorded")
        self.transition(demo_id, "closed", "Local safety demonstration passed")
        return {"jobId": demo_id, "artifactId": artifact["artifactId"], "sha256": artifact["sha256"], "state": "closed"}

    def brain_for(self, engine: str = "codex") -> Any:
        key = str(engine or "codex").strip().lower()
        if key not in self.brains:
            raise ValueError(f"Unknown brain engine: {engine}")
        return self.brains[key]

    def brains_status(self) -> list[dict[str, Any]]:
        return [{**brain.identity(), "engine": key} for key, brain in self.brains.items()]

    def brain_plan(self, job_id: str, engine: str = "codex") -> dict[str, Any]:
        brain = self.brain_for(engine)
        job = self._find_job(self.jobs(), job_id)
        role = next(role for role in self.roles() if int(role["id"]) == int(job["producerRoleId"]))
        output = self.data_root / "brain" / f"{job_id}-result.json"
        command = brain.command_for(job, role, output)
        return {"brain": brain.identity(), "engine": str(engine).lower(), "jobId": job_id, "roleId": role["id"], "command": command[:-1] + ["<bounded-job-prompt>"], "output": str(output)}

    def dispatch_to_brain(self, job_id: str, engine: str = "codex") -> dict[str, Any]:
        brain = self.brain_for(engine)
        agent_id = brain.identity()["id"]
        job = self._find_job(self.jobs(), job_id)
        role = next(role for role in self.roles() if int(role["id"]) == int(job["producerRoleId"]))
        self.claim_job(job_id, agent_id, 1200)
        self.transition(job_id, "in-progress", f"Dispatched to {brain.identity()['name']} brain")
        output = self.data_root / "brain" / f"{job_id}-result.json"
        try:
            result = brain.dispatch(job, role, output)
            self.append_event("brain.completed", result.get("summary", f"{brain.identity()['name']} completed the job"), jobId=job_id, brainId=agent_id)
            next_state = result.get("nextState", "review")
            self.transition(job_id, next_state, result.get("summary", f"{brain.identity()['name']} result ready"))
            return result
        except Exception as error:
            self.transition(job_id, "blocked", f"{brain.identity()['name']} dispatch failed: {error}")
            self.append_event("brain.failed", str(error), jobId=job_id, brainId=agent_id)
            raise

    def chat(self, message: str, engine: str = "codex", write: bool = True, timeout: int = 900) -> dict[str, Any]:
        text = str(message or "").strip()
        if not text:
            raise ValueError("Chat message is required")
        brain = self.brain_for(engine)
        if not brain.identity()["installed"]:
            raise ValueError(f"{brain.identity()['name']} CLI is not installed on this device")
        reply = brain.converse(text, write=write, timeout=timeout)
        turn = {
            "id": "CH-" + uuid.uuid4().hex[:12],
            "at": self.now(),
            "engine": str(engine).lower(),
            "brainId": brain.identity()["id"],
            "brainName": brain.identity()["name"],
            "write": bool(write),
            "threadId": self.current_thread()["id"],
            "message": text,
            "reply": reply,
        }
        self.store.mutate("chat.json", [], lambda values: (values + [turn])[-200:])
        self.append_event("chat.turn", text[:160], engine=turn["engine"], chatId=turn["id"], threadId=turn["threadId"])
        return turn

    # ---- chat threads -----------------------------------------------------
    # A single flat log meant every new task carried the whole previous
    # conversation in context. Threads let a new task start clean while older
    # chats stay on disk and can be reopened.
    def _touch_thread(self, thread_id: str, first_message: str):
        def apply(threads: list[dict[str, Any]]) -> list[dict[str, Any]]:
            for thread in threads:
                if thread.get("id") == thread_id:
                    thread["updatedAt"] = self.now()
                    thread["turns"] = int(thread.get("turns", 0)) + 1
                    return threads
            threads.append({
                "id": thread_id,
                "title": str(first_message).strip().splitlines()[0][:60] or "New chat",
                "createdAt": self.now(),
                "updatedAt": self.now(),
                "turns": 1,
            })
            return threads[-50:]
        return apply

    def migrate_legacy_chat(self) -> str:
        """Attach pre-thread turns to a real thread.

        Turns written before threads existed carry no threadId, so the history
        filter dropped them and the previous conversation appeared to vanish.
        This folds them into one "Previous chat" thread exactly once.
        """
        turns = self.store.read("chat.json", [])
        orphans = [t for t in turns if not str(t.get("threadId") or "")]
        if not orphans:
            return ""
        active = self.store.read("chat_active.json", None)
        target = None
        if isinstance(active, dict) and active.get("id"):
            target = active["id"]
        if not target:
            existing = self.store.read("chat_threads.json", [])
            target = next((t["id"] for t in existing if t.get("title") == "Previous chat"), "")
            if not target:
                target = "T-" + uuid.uuid4().hex[:10]
        def apply(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
            for value in values:
                if not str(value.get("threadId") or ""):
                    value["threadId"] = target
            return values
        self.store.mutate("chat.json", [], apply)
        if not isinstance(active, dict) or not active.get("id"):
            self.store.write("chat_active.json", {
                "id": target,
                "title": "Previous chat",
                "createdAt": orphans[0].get("at") or self.now(),
            })
        self.store.mutate("chat_threads.json", [], self._touch_thread(target, "Previous chat"))
        return target

    def chat_threads(self) -> list[dict[str, Any]]:
        self.migrate_legacy_chat()
        threads = list(self.store.read("chat_threads.json", []))
        active = self.store.read("chat_active.json", None)
        active_id = (active or {}).get("id") if isinstance(active, dict) else None
        for thread in threads:
            thread["active"] = thread.get("id") == active_id
        threads.sort(key=lambda t: str(t.get("updatedAt") or t.get("createdAt") or ""), reverse=True)
        return threads

    def current_thread(self) -> dict[str, Any]:
        active = self.store.read("chat_active.json", None)
        if isinstance(active, dict) and active.get("id"):
            return active
        threads = self.chat_threads()
        if threads:
            return next((t for t in threads if t.get("active")), threads[0])
        thread = {"id": "T-" + uuid.uuid4().hex[:10], "title": "Chat 1", "createdAt": self.now()}
        self.store.write("chat_active.json", thread)
        self.store.mutate("chat_threads.json", [], self._touch_thread(thread["id"], "Chat 1"))
        return thread

    def new_chat(self, title: str = "") -> dict[str, Any]:
        name = str(title or "").strip()
        thread = {
            "id": "T-" + uuid.uuid4().hex[:10],
            "title": (name.splitlines()[0][:60] if name else "New chat"),
            "createdAt": self.now(),
        }
        self.store.write("chat_active.json", thread)
        self.store.mutate("chat_threads.json", [], self._touch_thread(thread["id"], thread["title"]))
        self.append_event("chat.new", thread["title"], threadId=thread["id"])
        return thread

    def switch_chat(self, thread_id: str) -> dict[str, Any]:
        threads = self.store.read("chat_threads.json", [])
        match = next((t for t in threads if t.get("id") == str(thread_id)), None)
        if match is None:
            raise ValueError("No such chat thread")
        self.store.write("chat_active.json", {"id": match["id"]})
        return match

    def chat_history(self, limit: int = 40, thread_id: str = "") -> list[dict[str, Any]]:
        self.migrate_legacy_chat()
        want = str(thread_id or "") or self.current_thread()["id"]
        turns = [t for t in self.store.read("chat.json", []) if str(t.get("threadId") or "") == want]
        return list(reversed(turns))[:max(1, int(limit))]


    def status(self) -> dict[str, Any]:
        jobs = self.jobs()
        approvals = self.store.read("approvals.json", [])
        outcomes = self.store.read("outcomes.json", [])
        return {
            "ok": True,
            "name": "BeserkForce",
            "version": "0.2.0",
            "stage": "nerves-online",
            "deviceId": self.device_id,
            "time": self.now(),
            "campaigns": self.store.read("campaigns.json", []),
            "roles": self.roles(),
            "jobs": jobs,
            "approvals": approvals,
            "funnel": self.store.read("funnel.json", {}),
            "outcomes": outcomes,
            "providers": discover_providers(),
            "primaryBrain": self.brain.identity(),
            "brains": self.brains_status(),
            "chat": self.chat_history(40),
            "events": list(reversed(self.store.read("events.json", [])))[0:40],
            "summary": {
                "openJobs": sum(job["state"] not in TERMINAL_STATES for job in jobs),
                "pendingApprovals": sum(item["status"] == "pending" for item in approvals),
                "verifiedOutcomes": sum(item["status"] == "verified" for item in outcomes),
                "installedProviders": sum(item["installed"] for item in discover_providers()),
            },
            "authority": "External actions require Eric's exact approval and a matching action hash.",
        }

