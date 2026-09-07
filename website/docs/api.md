---
title: API access
description: Use the local FastAPI and OpenAI-compatible endpoints with authentication, discover the live schema, and distinguish application APIs from model inference.
---

Studio serves a **FastAPI application** on loopback by default. The OpenAI-compatible routes are an integration surface of this local server—not a hosted service provided by this website.

## Start a local API

```text
unsloth studio --host 127.0.0.1 --port 8888 --api-only --disable-tools
```

For first-run UI setup, start without `--api-only`, complete authentication, and create a credential through Studio's API-key controls. A normal API client should use a valid bearer token; do not depend on permissive keyless-access settings. Store credentials outside scripts and repositories.

When enabled in the running application, `/docs`, `/redoc`, and `/openapi.json` describe the actual installed schema. Documentation UI assets are served locally rather than from a third-party CDN.

## Installed-version reference and schema download

The [API reference and model catalog](/api-reference) provides a method/path/summary/tag filter, paginated operation inspection, request and response definitions, and a searchable model-schema catalog. Referenced models can be opened directly from an operation. Individual operation and model selections are shareable through the page URL.

The catalog uses a captured, sanitized **installed-application** OpenAPI document, not inferred endpoint definitions. Its download retains the complete document except for the explicitly disclosed environment-local directory query defaults. Operation IDs are never rewritten by the website. Duplicate IDs, broken or external references, mismatched Python-version identity, and changed artifact bytes fail validation.

Read the snapshot's timestamp, source revision, SHA-256, omission count, and license before treating it as the contract for a different installation. Schema publication is distinct from native desktop or GPU qualification. Mounted MCP tools are not included simply because the FastAPI application's OpenAPI schema was captured.

The reference is read-only and performs its filtering locally. It has no live request runner or token storage, loads no external Swagger/Redoc/CDN, and never calls your Studio backend.

## Endpoint map

| Purpose | Actual route |
| --- | --- |
| Lightweight liveness / application health | `GET /api/liveness`, `GET /api/health` |
| Authentication status/login | `/api/auth/status`, `/api/auth/login` |
| Manage API keys | `/api/auth/api-keys` |
| Model load/unload/status | `/api/inference/load`, `/api/inference/unload`, `/api/inference/status` |
| OpenAI-compatible model discovery | `GET /v1/models` |
| Chat completions | `POST /v1/chat/completions` |
| Additional compatibility routes | `/v1/completions`, `/v1/embeddings`, `/v1/responses`, `/v1/messages` |
| Training start/stop/status | `/api/train/start`, `/api/train/stop`, `/api/train/status` |
| Data recipe operations | `/api/data-recipe/...` |
| Export operations | `/api/export/...` |

Route existence is not a promise that every model supports embeddings, tools, multimodality, or every upstream API parameter. Use the installed schema and model/backend capability checks.

## PowerShell request example

First load a compatible model through Studio and obtain its identifier from `/v1/models`. In this example, `STUDIO_CLIENT_API_KEY` is **your client-side secret variable**, not an application configuration option.

```powershell
$headers = @{ Authorization = "Bearer $env:STUDIO_CLIENT_API_KEY" }
Invoke-RestMethod 'http://127.0.0.1:8888/v1/models' -Headers $headers

$body = @{
  model = 'replace-with-the-loaded-model-id'
  messages = @(@{ role = 'user'; content = 'Reply with a short greeting.' })
  max_tokens = 32
  stream = $false
} | ConvertTo-Json -Depth 5

Invoke-RestMethod 'http://127.0.0.1:8888/v1/chat/completions' `
  -Method Post -Headers $headers -ContentType 'application/json' -Body $body
```

The placeholder must be replaced by the actual model identifier; no checkpoint is implicitly promised by this example.

## Operational checks

Inspect HTTP status and structured errors, not only the TCP port. A liveness result does not prove a model is ready or training is healthy. Streaming clients must handle cancellation/disconnection and preserve event framing.

Do not expose the raw backend to the internet as a shortcut. Authentication, proxy controls, TLS, tool policy, and least-privilege process permissions are all part of [deployment security](security.md).

**Source:** [route registration and health](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/backend/main.py), [inference handlers](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/backend/routes/inference.py), [authentication](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/backend/auth/authentication.py), [key management](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/backend/routes/auth.py).
