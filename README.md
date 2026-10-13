# BeserkForce

BeserkForce is an isolated, provider-neutral workforce runtime built inside
`WorkForce/BeserkForce`. It reads the parent WorkForce registries as immutable
source material and never rewrites the original WorkForce or GrokBot files.

## First launch

```powershell
.\Start-BeserkForce.ps1
```

That opens the BeserkForce window. It is a desktop app, the same pattern as
Sermon Feed: `pythonw` plus a WebView2 frame, with its own taskbar name.
The runtime stays on this machine at `127.0.0.1:8877` and is not a browser tab.

First-time setup also installs the desktop shortcut:

```powershell
.\Install-BeserkForce-App.ps1
```

Stop it with:

```powershell
.\Stop-BeserkForce.ps1
```

## Authority boundary

Internal research, local code, tests, drafts, job routing and evidence storage
are allowed. Outreach, publishing, deployment, spending, booking, account
changes and Git pushes require Eric's explicit approval for the exact action.

## CLI

```powershell
python app.py health
python app.py status
python app.py demo
python app.py brains
python app.py brain BF-HELI-50
python app.py brain BF-HELI-50 --engine opencode
python app.py brain BF-HELI-50 --engine grok
# Explicit local dispatch, when desired:
python app.py dispatch BF-HELI-50
python app.py dispatch BF-HELI-50 --engine opencode
python app.py dispatch BF-HELI-50 --engine grok
# Chat with a conductor CLI inside the runtime (bounded to this folder):
python app.py chat "Summarize what Codex built here and what is still missing"
python app.py chat "Inspect the approval gate" --engine opencode
python app.py chat "Inspect the approval gate" --engine grok
python -m unittest discover -s tests -v
```

The `demo` command exercises a complete internal lifecycle and performs no
external action.

Codex, OpenCode, and Grok are conductor brains. Codex is the default.
Choose another with `--engine opencode` or `--engine grok`. Grok uses the
local Grok CLI at model `grok-4.7`. `brain` previews the bounded command
without execution. `dispatch` invokes the installed CLI inside this folder,
with structured output and the BeserkForce authority boundary. The chat
panel lists whichever of the three CLIs are installed.

The dashboard at `http://127.0.0.1:8877` also has a **Conductor Chat** panel
backed by `POST /api/chat` (`{message, engine, write}`) and `GET /api/brains`.
Chat runs the selected CLI inside the BeserkForce folder; toggle *allow edits*
off for a read-only turn.

## Build stages

1. Skeleton: local server, configuration, visual shell and health endpoint.
2. Nerves: atomic state, leases, jobs, approval hashes and evidence ledger. ✓
3. First campaign: Roles 50–54 pursue one verified private Oahu booking.
4. Muscles: provider adapters execute only approved, capability-matched work.

