---
title: Dependency & artifact matrix
description: Exact supported Python, Torch, Triton, framework, data, audio, frontend, and native-artifact versions with their authoritative manifests.
---

This is the current fork's compatibility contract, not an invitation to install each package independently. Use the installers and matching source. For a newer checkout, its manifests take precedence over this table.

## Interpreter and application identity

| Component | Selected contract | Authority |
| --- | --- | --- |
| Python | Standard, GIL-enabled, final CPython `>=3.14.7,<3.15`; default 3.14.7 | `studio/python_policy.py` |
| Core Python distribution | 2026.9.3 | `unsloth/_version.py` |
| Maintained Zoo | 2026.9.1+darbot.1 | Vendored companion, installed separately before Core in full profiles |
| Desktop | 0.2.0 / display tag `v0.2.0` | Tauri/Cargo desktop release scheme |
| Frontend build Node | 26.8.1 | CI and managed Node pins |
| Frontend TypeScript | 6.0.3 | Frontend manifest; ESLint compatibility prevents an arbitrary newer compiler |

Private npm `0.0.0` lockfile-holder versions are **not product releases**.

## Torch family and compiler namespace

| Profile | Torch | TorchVision | TorchAudio | Triton provider |
| --- | --- | --- | --- | --- |
| NVIDIA Linux | 2.14.0+cu130 | 0.29.0+cu130 | 2.11.0+cu130 | `triton==3.8.0` |
| NVIDIA Windows x64 | 2.14.0+cu130 | 0.29.0+cu130 | 2.11.0+cu130 | `triton-windows==3.8.0.post28` |
| CPU Linux/Windows | 2.14.0+cpu | 0.29.0+cpu | 2.11.0+cpu | No CUDA compiler requirement |
| macOS Torch | 2.14.0 | 0.29.0 | 2.11.0 | No CUDA compiler requirement |
| Intel XPU | 2.14.0+xpu | 0.29.0+xpu | 2.11.0+xpu | `triton-xpu==3.8.0` |
| Linux ROCm | 2.14.0+rocm7.2 | 0.29.0+rocm7.2 | 2.11.0+rocm7.2 | `triton-rocm==3.8.0` |
| True GGUF-only | Absent | Absent | Absent | All providers excluded |

Each wheel family uses its corresponding [official PyTorch index](https://download.pytorch.org/whl/). Compiler distributions share an import namespace and must not be mixed. CCE is CUDA-only. `cu126` artifacts exist but are **not enabled by policy**; `cu128` is not silently aliased. There is no TorchAudio 2.14 package to derive from Torch's version.

## Framework and shared data stack

| Package | Version | Why it matters |
| --- | --- | --- |
| Transformers / TRL / PEFT | 5.16.1 / 1.12.0 / 0.20.0 | Requires actual loader, trainer, and companion API adaptations |
| Accelerate / Hugging Face Hub | 1.14.0 / 1.30.0 | Training orchestration and model/dataset acquisition |
| datasets / scikit-learn | 5.0.1 / 1.9.0 | Dataset and downstream runtime contract |
| NumPy | 2.5.3 | Do not downgrade to satisfy unsupported compressed export |
| Data Designer / config / engine | 0.9.2 for all three | Shared environment; complete direct runtime union resolved separately |
| pandas / PyArrow | 2.3.3 / 24.0.0 | Data Designer requires pandas below 3 and Arrow below 25 |
| Rich / Click | 14.3.4 / 8.4.2 | Data Designer and SQLFluff compatibility ceilings |
| FastMCP / MCP | 3.4.7 / 1.29.1 | Data Designer requires MCP below 2; FastMCP 4 is not compatible |
| FastAPI / Uvicorn | 0.141.1 / 0.52.4 | Studio HTTP runtime |
| Pydantic / pydantic-core | 2.13.5 / 2.46.5 | Exact paired dependency; not independently upgradable |
| bitsandbytes / TorchAO | 0.50.2 / 0.18.0 | Profile-specific quantization paths, not blanket hardware certification |

## Audio and checksum-qualified artifacts

| Artifact | Selection |
| --- | --- |
| Protobuf | **Official pure-Python** `protobuf-4.25.9-py3-none-any.whl` |
| Protobuf SHA-256 | `d49b615e7c935194ac161f0965699ac84df6112c378e05ec53da65d2e4cbb6d4` |
| AudioTools | Stable upstream **0.7.4**, archive at commit `ffe03e96b4d2dfb3ddecad289a6a95a7e96cc8c6` |
| AudioTools archive SHA-256 | `c5093d26afeeec1e9dc2ecfac6a7a6e74ce9c349ff10668c1d3c9f11d7685689` |
| TensorBoard / DAC | 2.20.0 / `descript-audio-codec==1.0.0` |
| TorchCodec | 0.16.0, subject to the declared platform markers |
| xFormers (CUDA x64) | 0.0.35 official cu130 wheel URLs in the root manifest |

Protobuf 4's native abi3 wheel fails CPython 3.14 metaclass checks. Setting `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python` alone is insufficient because the selector probes the extension. Preserve the pure-wheel URL **and checksum**.

AudioTools 0.7.4 requires protobuf below 5; TensorBoard 2.21 requires protobuf 6. The selected **TensorBoard 2.20** satisfies the genuine shared requirements without falsifying installed metadata. See [audio](audio.md).

## macOS and native helpers

macOS selects PyAV **15.1.0**, versus **18.1.0** elsewhere, for wheel deployment-target compatibility. Intel macOS uses cryptography **48.0.1**, versus **49.0.0** on the other declared platforms. macOS uses pymupdf4llm **0.3.4**, versus **1.28.2** elsewhere.

Native `llama.cpp`, `whisper.cpp`, and `stable-diffusion.cpp` artifacts are selected by dedicated helpers, platform/accelerator compatibility, and their pin/manifest logic—not the Python distribution version. Do not invent a universal native binary filename or install a mismatched artifact.

**Authoritative sources:** [root extras](https://github.com/darbotlabs/darbot-unsloth/blob/main/pyproject.toml), [shared constraints](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/backend/requirements/single-env/constraints.txt), [audio archives](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/backend/requirements/extras-no-deps.txt), [Node pins](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/node_prebuilt_pins.json), [native installers](https://github.com/darbotlabs/darbot-unsloth/tree/main/studio).
