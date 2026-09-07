---
title: Overview
description: What Darbot Unsloth is, how this fork differs from upstream, and how to navigate its installation, training, and Studio wiki.
---

Darbot Unsloth is the independent [darbotlabs/darbot-unsloth](https://github.com/darbotlabs/darbot-unsloth) fork of [Unsloth](https://github.com/unslothai/unsloth). It combines a Python model-training library, a local web application, and a desktop shell. This wiki describes **this repository's stack and policies**, not a promise that every upstream integration works on every device.

## Three entry points, shared code

| Entry point | What you use | What still runs underneath |
| --- | --- | --- |
| Core | Python model loaders, adapters, trainers, and export helpers | The selected ML stack and the maintained Zoo companion |
| Studio | Browser UI or authenticated HTTP API | FastAPI plus inference, training, export, and recipe workers |
| Desktop | Tauri native application | The Studio frontend and a managed local backend; it is not an entire model environment in one executable |

For the full boundary map, see [architecture](architecture.md).

## The fork contract

- Use standard, final-release CPython **`>=3.14.7,<3.15`**, including in the Torch-free mode.
- NVIDIA installs use **Torch 2.14 with cu130**. CPU, XPU, ROCm, and GGUF-only are distinct profiles.
- Full installs pair Core with the maintained, licensed Zoo **2026.9.1+darbot.1**. Its source adaptations matter; this is not merely relaxed package metadata.
- Preserve installation provenance, the original data root, and rollback material when updating.
- Do not assume a successful import, a CI configuration, or a downloadable wheel certifies a complete training path.

The [dependency matrix](dependency-matrix.md) gives exact versions and artifact sources. [Support scope](support.md) distinguishes evidence from intended coverage.

## Pick a reading path

**New installation:** [Getting started](getting-started.md) → [Windows](windows.md) or [Linux/macOS](linux-macos.md) → [verification](testing.md).

**Train an adapter:** [LoRA/QLoRA](training.md) → [datasets and TRL semantics](datasets.md) → [export](export.md).

**Use the app:** [Studio chat](studio.md) → [data recipes](data-recipes.md) → [audio](audio.md) → [API](api.md).

**Maintain a deployment:** [Storage](storage.md) → [updates and recovery](updates.md) → [security and privacy](security.md).

## Releases and attribution

Desktop **0.2.0** and Python **2026.9.3** use different version schemes. See [Downloads](/downloads) for live publication status; filenames in documentation are not evidence that assets have been uploaded. Upstream installers, images, and hosted notebooks are not fork artifacts.

Unsloth AI's authorship and the repository's Apache-2.0, AGPL-3.0, and third-party license boundaries remain intact. Read [attribution and licenses](licenses.md).

**Source of truth:** [README platform policy](https://github.com/darbotlabs/darbot-unsloth/blob/main/README.md), [package manifest](https://github.com/darbotlabs/darbot-unsloth/blob/main/pyproject.toml).
