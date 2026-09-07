---
title: Linux, macOS & WSL
description: Source-install Darbot Unsloth on POSIX platforms without confusing configured CPU, CUDA, ROCm, MLX, or container lanes with runtime qualification.
---

## Source installation

From the fork checkout:

```bash
UNSLOTH_SKIP_AUTOSTART=1 bash install.sh --local
```

To keep the environment independent of persistent data:

```bash
export UNSLOTH_ENV_DIR="$HOME/ai/unsloth-env"
export UNSLOTH_STUDIO_HOME="$HOME/ai/unsloth-data"
UNSLOTH_SKIP_AUTOSTART=1 bash install.sh --local
"$UNSLOTH_ENV_DIR/bin/unsloth" studio verify-install --json
"$UNSLOTH_ENV_DIR/bin/unsloth" studio --host 127.0.0.1 --port 8888
```

Use an empty or appropriately owned environment directory, not your system Python. The absolute-path and ownership rules apply here as on [Windows](windows.md). All modes require standard final-release CPython `>=3.14.7,<3.15`.

## Platform-specific choices

| Platform | Profile considerations |
| --- | --- |
| Linux + NVIDIA | Canonical Torch 2.14/cu130; compatible driver and matching native artifacts required |
| Linux + AMD | ROCm 7.2 wheel family and `triton-rocm`, not generic CUDA Triton |
| Linux CPU | CPU-ML includes Torch; native GGUF-only does not |
| Apple Silicon | MLX and native helper integrations exist, but require compatible wheels and separate on-device validation |
| Intel macOS | Do not assume Apple Silicon MLX availability; check platform markers and use only resolvable supported paths |
| WSL | Treat the Linux environment, dependencies, and filesystem as a separate installation; Windows runtime evidence does not qualify it |

The [dependency matrix](dependency-matrix.md) documents macOS-specific PyAV, cryptography, and PDF-processing constraints. In particular, macOS pins are not accidental stale versions: wheel deployment targets differ.

## True native GGUF-only

```bash
UNSLOTH_SKIP_AUTOSTART=1 bash install.sh --local --no-torch
```

This retains Studio, the application dependency graph, Data Designer, and local plugins while rejecting transitive Torch, Zoo, and Triton. It is not a partially installed full-ML stack. See [the profile contract](gguf-only.md).

## Docker is a separate build lane

The [Dockerfile](https://github.com/darbotlabs/darbot-unsloth/blob/main/docker/Dockerfile) targets CPython 3.14.7, CUDA 13, and architecture-specific artifacts. Build-time dependency resolution cannot qualify runtime GPUs, drivers, or container integration. Upstream Docker images do not include this fork by implication; no fork image is advertised here without publication evidence.

Linux, macOS, Docker, and hardware CI lanes are configured, but they were not fully runtime-qualified by the Windows-only migration exercise. See [support scope](support.md) before planning a production rollout.

**Implementation:** [install.sh](https://github.com/darbotlabs/darbot-unsloth/blob/main/install.sh), [setup.sh](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/setup.sh), [platform requirements](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/backend/requirements/single-env/constraints.txt).
