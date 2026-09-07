---
title: True GGUF-only mode
description: Understand the --no-torch installation contract, negative constraints, native inference, and how it differs from CPU machine learning.
---

`--no-torch` is an intentional **Torch-free application profile**, not a flag that hides a failed Torch installation.

## Install

Windows, from the fork checkout:

```powershell
.\install.ps1 --local --no-torch --skip-autostart
```

Linux/macOS:

```bash
UNSLOTH_SKIP_AUTOSTART=1 bash install.sh --local --no-torch
```

The same standard CPython `>=3.14.7,<3.15` policy applies. Custom environment and data-root rules remain unchanged.

## What is present—and absent

| Installed / available to resolve | Intentionally absent |
| --- | --- |
| Core's `studio` extra and the normal web/API dependency graph | Torch, TorchVision, TorchAudio |
| Torch-free tokenizer, dataset, and scientific/data utilities | The Torch-dependent Zoo companion |
| Data Designer direct runtime requirements and local recipe plugins | Generic, Windows, XPU, and ROCm Triton compiler providers |
| Native helper integration for GGUF inference | Python LoRA/QLoRA and other Torch-backed training paths |

Having `transformers` or `scikit-learn` installed does not imply Torch is installed. Conversely, importing the GPU-oriented `unsloth` training API is not an appropriate health check for a GGUF-only environment.

The scoped constraints use impossible package bounds such as `torch<0` and `unsloth-zoo<0` to reject accidental transitive ML dependencies. Constraints themselves install nothing. They must **not** be applied to CPU-ML or CUDA installs.

## It is not CPU-ML

The CPU profile installs the CPU Torch wheel family and the maintained companion. Choose it when you actually need supported Python ML operations on CPU. Native GGUF inference can use a suitable native backend independently of whether Python Torch exists; `--no-torch` does not automatically mean every native computation is CPU-only.

Nor does GGUF-only provide every audio or multimodal path: Python codec models, Torch-backed vision, and training require their own runtime. Check each feature's [backend requirements](devices.md).

## Verify and preserve the mode

Run `unsloth studio verify-install --json`, launch Studio, and test a real native model separately. The installer records completion plus no-Torch mode; `.unsloth-no-torch` preserves intent even across an interrupted dependency pass. Do not manually remove the marker to force a fast path.

Controlled-absence startup testing has exercised Studio without Torch/Zoo. That does not prove all models or native-helper variants work. Keep the same mode on reinstall and follow [source-aware updates](updates.md).

**Implementation:** [runtime requirements](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/backend/requirements/no-torch-runtime.txt), [negative constraints](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/backend/requirements/no-torch-constraints.txt), [completion manifest](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/install_manifest.py).
