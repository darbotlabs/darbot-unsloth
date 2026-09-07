---
title: Security, privacy & deployment
description: Deploy Studio with deliberate network exposure, authentication, tool permissions, secret handling, data retention, and release provenance.
---

This is operational guidance, not a security audit or a guarantee that the application is suitable for hostile multi-tenant hosting.

## Start with a narrow boundary

```text
unsloth studio --host 127.0.0.1 --port 8888 --disable-tools
```

Loopback avoids making the raw server reachable from other machines. For a headless API, add `--api-only`. Changing the bind to `0.0.0.0` or `::` is a real exposure decision, not merely a convenient URL.

For remote access, use an authenticated, correctly configured TLS reverse proxy or an approved private-access mechanism. Restrict network reachability, forwarded-header trust, request sizes, and authentication at the application boundary. Do not assume a tunnel makes the underlying raw port private.

Cloudflare/public-link modes are separate, opt-in behavior with their own trust and routing consequences. This documentation site does not provide a proxy or host a Studio instance.

## Authentication and tools

- Complete first-run authentication and use unique credentials.
- Create client API keys through the application; never embed them in source or this wiki.
- Avoid enabling keyless API access on shared or exposed deployments.
- Keep the MCP server disabled unless needed; when enabled, supply its required token.
- Disable server-side tools when not needed. Code execution, web access, MCP calls, and agent actions are not made harmless by a chat interface.
- Run Studio as a non-administrative user with the minimum filesystem/network access required.

Review preview-sharing settings separately. The password-reset implementation explicitly notes that existing shared preview links are not automatically revoked by a password reset.

## Local processing is not universal privacy

Local model inference can keep prompts on the machine, but downloads, external providers, web search, repository imports, telemetry-capable dependencies, and remote tools have independent network behavior. Check the configured feature before promising users that "nothing leaves the device."

Uploaded datasets, conversations, retrieved documents, generated audio, model artifacts, and logs may contain personal or confidential information. Set retention and backup practices deliberately. Protect the [data root](storage.md), provider credentials, authentication material, and backup copies.

This static wiki uses local build-time search indexing, no external analytics, and no hosted search account. Its search index contains **only public documentation**, never Studio databases or user uploads.

## Software supply chain

Install from the correct fork source and preserve artifact provenance. Keep lockfiles, exact backend-family selections, and checksum-qualified protobuf/AudioTools artifacts. Do not use broad `pip upgrade` operations or dependency overrides to force an incompatible export feature.

For releases, verify the repository and tag plus `SHA256SUMS.txt`. A matching checksum detects a file mismatch but does not itself authenticate a publisher. Unsigned Windows builds and disabled automatic signed updating must remain clearly disclosed.

## Reporting a concern

Do not open a public issue containing an exploit against a live deployment, a password, API key, private dataset, or unredacted user log. Use a private reporting channel offered by the affected repository/maintainers if available; no unverified security email address is invented here.

Revoke exposed credentials, preserve relevant evidence privately, and report the affected fork revision and deployment boundary. Avoid testing systems without authorization.

**Sources:** [authentication](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/backend/auth/authentication.py), [CLI exposure/tool options](https://github.com/darbotlabs/darbot-unsloth/blob/main/unsloth_cli/commands/studio.py), [MCP server](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/backend/mcp_server.py), [Tauri CSP](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/src-tauri/tauri.conf.json).
