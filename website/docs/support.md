---
title: Qualification & support scope
description: Read what has actually been exercised on the migrated stack, what is configured but unqualified, and what information a useful support report needs.
---

## What "supported" means here

The supported **interpreter/dependency policy** is broader than demonstrated **device/workload qualification**. Neither a compatibility pin nor an upstream feature list certifies every combination.

### Measured Windows paths

The installed Windows **Core 2026.9.3 + Zoo 2026.9.1+darbot.1** stack passed **eight GPU cases with no skips**, using standard CPython 3.14.7, Torch 2.14/cu130, and Triton-Windows 3.8.0.post28:

| Physical device | Memory / architecture | Passed GPU cases | Execution boundary |
| --- | --- | --- | --- |
| T1000 GPU 0 | 8 GB / sm_75 | 4, no skips | One physical GPU selected |
| T1000 GPU 1 | 8 GB / sm_75 | 4, no skips | One physical GPU selected in a separate run |

The qualification used an isolated interpreter outside the checkout. Core, Zoo, and the tested submodules resolved to the installed environment before and after execution, rather than accidentally importing working-tree code. This validates the **installed Windows package paths** exercised by these tests; it is not a declaration that the complete desktop release is production-ready.

The four cases per device comprise the underlying tiny-Llama PEFT forward/backward check and three actual Unsloth trainer cases: FP32, FP32 with TensorBoard, and packed 4-bit QLoRA. Together they exercised:

- Offline tiny-Llama FP32 manual LoRA on attention Q/K/V/O and MLP projections.
- Genuine packed 4-bit QLoRA with CUDA `Linear4bit` weights, forward/backward, and optimizer steps that changed adapters.
- FP32 and 4-bit adapter save/reload with weight/logit parity within the relevant tolerances.
- TensorBoard event write/read.

Separate migration checks also exercised compiled elementwise forward/backward, real Studio API lifespans with MCP disabled/enabled, DAC encode/decode/checkpoint paths, Data Designer/plugins, normal warmup, and controlled-absence GGUF-only startup. These are not additional cases silently included in the eight-case GPU total.

This is a focused qualification record, **not a performance benchmark**.

### What those results do not prove

- No pooled 16 GB VRAM or DDP/FSDP qualification.
- No blanket support for all model families, precisions, context lengths, or compiled extensions.
- No native BF16 acceleration on Turing.
- No claim that Windows results qualify Linux, macOS, WSL, Docker, ROCm, XPU, MLX, or hosted notebooks.
- No claim that locally built release assets are production-qualified or already uploaded.

Published upstream Triton/Turing support policy remains distinct from these measured fork results.

## Configured versus available

Linux/macOS/container/hardware CI lanes and platform-specific source paths exist. They were not fully runtime-qualified on the Windows migration machine. Wheel availability, a configured workflow, a successful import, and a passed end-to-end workload are different evidence.

LLMCompressor 0.13 FP8/FP4 compressed export is explicitly blocked by published dependency ceilings. GGUF/uncompressed export and 4-bit training are separate capabilities. See [export](export.md).

## Release status

Use [Downloads](/downloads) for the current preparation/publication state. The installed GPU result does not qualify the native UI's first-launch behavior; desktop UI qualification and release publication remain separate gates. Windows NSIS and Python distribution filenames are not proof of availability. Automatic signed desktop updating remains disabled; unsigned-build limitations must be considered during installation.

## A useful support report

Open a fork issue at [darbotlabs/darbot-unsloth/issues](https://github.com/darbotlabs/darbot-unsloth/issues) with:

1. Fork revision and install/update source mode.
2. OS, interpreter path/version/build, and exact profile.
3. GPU model, memory, driver, and physical device selected.
4. `verify-install` result and the first relevant sanitized traceback.
5. Model/dataset identity, precision, sequence length, and minimal reproduction.
6. Expected versus actual behavior, including whether tests failed or skipped.

Do not include tokens, private datasets, full user directories, or unredacted database/log dumps. Identify upstream-only behavior clearly rather than assuming the upstream maintainers can reproduce this fork's stack.

**Evidence locations:** [platform policy](https://github.com/darbotlabs/darbot-unsloth/blob/main/README.md), [GPU fixture](https://github.com/darbotlabs/darbot-unsloth/blob/main/tests/test_python314_gpu_smoke.py), [runtime compatibility tests](https://github.com/darbotlabs/darbot-unsloth/blob/main/tests/test_python314_runtime_compat.py), [workflow definitions](https://github.com/darbotlabs/darbot-unsloth/tree/main/.github/workflows).
