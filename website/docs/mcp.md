---
title: MCP integration
description: Enable the opt-in local MCP server, distinguish server tools from outbound MCP connections, and protect high-impact operations.
---

Studio includes an opt-in local **Model Context Protocol server**. An MCP client can inspect state and invoke operations such as training, recipe validation, and export. This is distinct from configuring Studio to use an external MCP server as a tool provider.

## Enable the local server

The server is disabled by default. Provide a fresh private token through your secret-management process, then launch:

```powershell
$env:UNSLOTH_STUDIO_ENABLE_MCP = '1'
$env:UNSLOTH_STUDIO_MCP_TOKEN = $env:STUDIO_PRIVATE_MCP_TOKEN
unsloth studio --host 127.0.0.1 --port 8888
```

`STUDIO_PRIVATE_MCP_TOKEN` above is an example secret source that **you must populate securely**; it is not a built-in default. Do not use a literal example password or put a real token in a command committed to Git.

The endpoint is:

```text
http://127.0.0.1:8888/mcp/
```

`/mcp` redirects to the canonical trailing-slash endpoint. Configure the client with the actual port and token; the server requires an exact bearer credential for HTTP and WebSocket access.

## Available high-impact tools

| Tools | Effect |
| --- | --- |
| `studio_status`, `list_local_models` | Discover runtime/model state |
| `get_training_status`, `list_training_runs` | Inspect training |
| `start_training`, `stop_training` | Consume resources or interrupt work |
| `validate_recipe`, `get_recipe_job_status`, `get_recipe_job_dataset` | Validate and inspect recipe work |
| `load_checkpoint`, `export_gguf` | Load artifacts and write exports |

`start_training` uses the same `TrainingStartRequest` validation as the existing backend. Export paths use Studio's established path validation. This is not an escape from normal model/backend compatibility.

## Trust and lifecycle

Enabling a protocol endpoint does not sandbox the tools it exposes. Clients may trigger GPU allocation, write model artifacts, and stop active work. Keep the server on loopback unless an appropriately authenticated reverse proxy protects the deployment. Give the backend process only the filesystem and network access it needs.

The actual FastAPI lifespan has been exercised with MCP disabled and enabled; startup must still be validated in each deployment environment. The shared stack keeps FastMCP **3.4.7** with MCP **1.29.1** because Data Designer requires MCP below 2.

For outbound MCP connections, review the remote server operator, credentials, tool definitions, and the data sent in calls. See [security and privacy](security.md).

**Sources:** [repository MCP guide](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/MCP.md), [server implementation](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/backend/mcp_server.py), [outbound server routes](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/backend/routes/mcp_servers.py).
