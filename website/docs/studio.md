---
title: Studio chat & model lifecycle
description: Launch the local Studio UI, select a model backend, manage downloads and generation, and understand chat storage and external-provider boundaries.
---

Studio is the browser-facing application. The Tauri desktop shell presents the same frontend while managing a local backend process; it is not a different model-training engine.

## First launch

```text
unsloth studio --host 127.0.0.1 --port 8888
```

Complete the authentication flow in the UI. Keep the loopback bind for a single-machine installation. Use the actual port printed by the launcher; do not confuse the Vite development port with the production FastAPI port.

## A reliable first chat

1. Open the model picker and choose an appropriate local model or a model you are authorized to download.
2. Check whether the selection is GGUF/native, a Torch-backed model, or a platform-specific backend. A [GGUF-only install](gguf-only.md) cannot run arbitrary Torch models.
3. Let downloads finish. A partially populated cache is not a complete checkpoint.
4. Begin with modest context length and one short request. Inspect actual load/generation status.
5. Stop generation or unload through the application before switching to a memory-intensive training run.

The backend has separate load, inference, and worker orchestration paths. A visible model in the catalog means it can be discovered; it does not mean it is already cached, compatible, or loaded.

## Context, parallel requests, and memory

For native llama-server inference, parallel slots share the loaded model and divide available context/KV capacity. Increasing parallelism is not free throughput. Long conversations, images, tool results, and retrieval context can materially increase memory and prompt-processing costs.

Studio maintains chat history and generation-run state. Do not treat closing a browser tab as proof that every background operation has finished. Stop the operation explicitly and verify status before maintenance.

## Local versus external connections

Local inference does not require sending prompts to a hosted model provider once required assets are available. However, choosing a remote provider, web search, repository import, an MCP server, or a tool can send data off-machine. Review credentials, permissions, and the exact destination before enabling them.

Server-side tools can execute code or access network resources. On shared or remotely accessible deployments, use the [security guide](security.md); "local UI" is not a security boundary.

## Related workflows

- [Data recipes](data-recipes.md) turn supported source material into datasets.
- [Training](training.md) saves adapters and run artifacts rather than changing a downloaded base model in place.
- [Audio](audio.md) distinguishes codecs, generation, and transcription backends.
- [API access](api.md) serves clients without requiring them to drive the UI.

**Implementation:** [inference routes](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/backend/routes/inference.py), [orchestrator](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/backend/core/inference/orchestrator.py), [chat persistence](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/backend/routes/chat_history.py), [frontend](https://github.com/darbotlabs/darbot-unsloth/tree/main/studio/frontend/src).
