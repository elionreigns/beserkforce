# BeserkForce architecture

## Clean-room boundary

BeserkForce lives entirely below `WorkForce/BeserkForce`. Parent WorkForce
files are read-only registries. Historical GrokBot code informed the audit but
is neither imported nor mutated.

## What was kept from the earlier system

- Named roles and visible handoffs.
- Atomic JSON persistence and append-style event history.
- Proof hashing and a strict distinction between artifacts and outcomes.
- Human gates for consequential actions.
- A focused outcome campaign instead of an unlimited activity queue.

## What was corrected

- Parent WorkForce registries are authoritative; no legacy Obsidian path is
  required to discover Roles 50–54.
- One state vocabulary is used throughout the new runtime.
- Provider discovery reports reality and never silently substitutes a model.
- A job claim has an expiring owner/device lease.
- Approval is bound to a canonical SHA-256 hash of the exact action.
- Traffic, leads, checkout opens, bookings and compensation begin as UNKNOWN.
- A helicopter sale requires three verified proof classes and Eric's explicit
  confirmation.
- Runtime data and machine configuration are excluded from source control.

## Layers

1. `app.py`: local HTTP/CLI entrypoint.
2. `beserkforce/core.py`: jobs, leases, artifacts, approvals and evidence.
3. `beserkforce/providers.py`: read-only CLI/provider discovery.
4. `data/runtime`: atomic local operational state.
5. `web`: command center consuming `/api/status`.

## Current execution boundary

Provider adapters are detection-only. No adapter may send, publish, deploy,
spend, book, change an account or push Git until an exact action packet has an
Eric-approved hash and an executor for that action has been explicitly enabled.

