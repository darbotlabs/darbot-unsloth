---
title: Architecture & process boundaries
description: Map Core, the maintained Zoo companion, FastAPI, recipe and model workers, React/Vite, Tauri, native helpers, and persistent storage.
---

Darbot Unsloth is not a monolithic desktop binary. It is a set of Python, native, browser, and process-lifecycle components that share explicit compatibility and data-root contracts.

## System map

```text
Browser or Tauri webview
          |
          | authenticated HTTP / streaming
          v
Studio FastAPI application <---- API clients / opt-in MCP clients
          |
          +-- inference orchestrator -- model worker / native llama-server
          +-- training service ------- training worker -- Core + Zoo + ML stack
          +-- export orchestrator ---- export worker / native converters
          +-- recipe job manager ----- Data Designer + local plugins
          |
          +-- persistent Studio data, auth, datasets, outputs, exports

Tauri shell -- preflight / install / backend ownership / lifecycle
Installers -- Python policy / exact environment / source + artifact provenance
```

This conceptual diagram does not imply every operation launches a new process on every request. Follow the relevant orchestrator for its lifecycle details.

## Code ownership and responsibilities

| Layer | Source location | Responsibility |
| --- | --- | --- |
| Core | `unsloth/` | Fast model loading, adapter/kernel integration, trainer adaptations, save/export helpers |
| Maintained Zoo | `studio/backend/vendor/unsloth_zoo_compat/` | Companion training/dataset/model utilities, installed as a separate distribution |
| CLI | `unsloth_cli/` | Start Studio, manage runtime/update workflows, expose CLI commands |
| FastAPI | `studio/backend/main.py` and `routes/` | Authentication, validation, route registration, lifespan, and client responses |
| ML services | `studio/backend/core/inference`, `training`, `export` | Resource-sensitive model operations and worker orchestration |
| Data recipes | `studio/backend/core/data_recipe` and `plugins/` | Recipe validation, generation jobs, and dataset artifacts |
| Frontend | `studio/frontend/` | React/Vite UI and application state |
| Desktop shell | `studio/src-tauri/` | Rust/Tauri lifecycle, native integration, managed backend ownership |
| This wiki | `website/` | Static documentation only; no model runtime or authentication service |

## Core and Zoo are a pair

Core depends on the maintained Zoo source contract, not merely its version number. Source refreshes must update the pair together even when package versions are unchanged. The vendored companion remains licensed third-party-derived source; it is not folded into Core's distribution namespace.

True GGUF-only installs defer Zoo rather than installing a dependency-inconsistent companion. Studio's HTTP and recipe layers must remain usable without importing a full training stack. See [the no-Torch contract](gguf-only.md).

## Process lifetime is a correctness boundary

Inference/training/export work can outlive an individual request. The desktop shell and backend maintain ownership, identity, leases, and shutdown coordination so that an app controls its own processes rather than arbitrary similarly named processes.

Do not stop processes by name during repair. Close operations normally; if manual recovery is necessary, identify the exact owned process. Replacing an active environment risks locked executables and workers still using old code.

## Data and deployment boundaries

The Python environment is replaceable runtime material; the data root contains user state. Source trees, model caches, external workspaces, and native helper paths may live elsewhere. [Storage](storage.md) explains their resolution.

GitHub Pages hosts only generated documentation. GitHub Releases hosts public release binaries. Neither hosts your running FastAPI server, model checkpoints, chat database, or user credentials.

**Sources:** [backend](https://github.com/darbotlabs/darbot-unsloth/tree/main/studio/backend), [Tauri process code](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/src-tauri/src/process.rs), [backend ownership](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/src-tauri/src/desktop_backend_owner.rs), [companion installer](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/install_zoo.py).
