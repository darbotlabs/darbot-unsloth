---
title: Devices & backend profiles
description: Separate wheel availability, driver support, compiler namespaces, precision, and runtime qualification across NVIDIA, CPU, XPU, ROCm, and Apple backends.
---

## Four different compatibility checks

1. **Interpreter:** Is the Python build supported?
2. **Artifacts:** Do matching wheels/native helpers exist for the platform?
3. **Runtime:** Can the driver and hardware execute those binaries?
4. **Workload:** Does the actual model, precision, optimizer, and export path pass a real test?

An import or wheel download only answers part of this chain.

## NVIDIA CUDA

The canonical profile is Torch **2.14/cu130**. Use a compatible **580-series-or-newer NVIDIA driver**, then validate on the actual device. Installers and Docker do not silently move to cu126 for older drivers even though that wheel family exists.

Ampere/sm_80 or newer remains the primary accelerated-training target. Turing/sm_75 is **not blanket-rejected** by this fork. Two separate NVIDIA T1000 8 GB devices passed tiny-Llama FP32 LoRA and genuine packed 4-bit QLoRA qualification, including changed weights and adapter reload parity.

That evidence is narrow:

- Each test used one physical GPU at a time; the devices do not form a pooled 16 GB GPU.
- It is not DDP, FSDP, or every-model certification.
- Turing lacks native BF16 acceleration.
- Published upstream Triton Turing policy is distinct from the measured fork paths.

Use `nvidia-smi` to inspect the real driver/device and [the targeted tests](testing.md) to validate behavior. Do not rely on a spoofed availability probe.

## Other profiles

| Profile | Boundary to preserve |
| --- | --- |
| CPU-ML | Contains Torch and Zoo; it is not `--no-torch` |
| True GGUF-only | Native inference with a Torch-free application environment |
| Intel XPU | Official XPU wheel family plus **triton-xpu**, not generic Triton |
| AMD ROCm | Selected Linux ROCm 7.2 family plus **triton-rocm** |
| Apple Silicon MLX | Separate MLX integration and on-device validation; no inference from Windows results |

CCE is CUDA-only. Do not contaminate XPU, ROCm, or no-Torch installations with CUDA-specific compiler dependencies. vLLM, Flash Attention, xFormers, TorchAO modes, and other compiled extensions each require their own compatibility checks.

## Plan memory conservatively

Account for weights, KV cache or training activations, optimizer state, sequence length, temporary buffers, other applications, and loaded workers. Model-picker memory estimates are useful estimates, not reservations or guarantees. Reduce sequence length and batch size before assuming a larger device pool exists.

Start with a small, licensed model and verify a complete load/generate/unload or train/save/reload cycle. See [support scope](support.md) and [troubleshooting](troubleshooting.md).

**Sources:** [platform policy](https://github.com/darbotlabs/darbot-unsloth/blob/main/README.md), [profile extras](https://github.com/darbotlabs/darbot-unsloth/blob/main/pyproject.toml), [real-device qualification test](https://github.com/darbotlabs/darbot-unsloth/blob/main/tests/test_python314_gpu_smoke.py).
