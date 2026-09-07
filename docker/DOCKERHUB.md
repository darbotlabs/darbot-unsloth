# Unsloth Docker Image

Source builds for [darbotlabs/darbot-unsloth](https://github.com/darbotlabs/darbot-unsloth).
No fork image is assumed published. Upstream `unsloth/unsloth` does not include
this fork's changes. Both the base and Studio environment require standard
CPython **3.14.7**, Torch **2.14.0+cu130**, Triton **3.8.0**, datasets **5.0.1**
and scikit-learn **1.9.0**. TorchVision is 0.29.0; TorchAudio remains 2.11.0.
The vendored Zoo companion is bootstrapped before local Core resolution.
vLLM and xformers are not enabled by default; optional engines need separate
validation and may not force a Torch downgrade or install prereleases.
The current stable vLLM 0.28 release requires Torch 2.13, so it cannot be enabled
under this image's Torch 2.14 policy. An explicit vLLM build fails rather than
downgrading Torch or overriding dependency caps.

Source: [`docker/`](https://github.com/darbotlabs/darbot-unsloth/tree/main/docker).
See the [fork platform policy](../README.md#this-forks-platform-policy).

## Tags

| Tag | Contents | Use it for |
|---|---|---|
| `darbot-unsloth:studio` | Local Studio + JupyterLab + notebooks + key-only SSH build | Browser workflows supported by the selected backend. |
| `darbot-unsloth:core` | Local Core + JupyterLab + notebooks build | Notebooks and scripts. |

Publication is disabled unless the repository explicitly configures
`UNSLOTH_DOCKER_PUBLISH`, `UNSLOTH_DOCKER_IMAGE`, and `UNSLOTH_DOCKER_USERNAME`.
When enabled, the workflow maintains moving `core`/`studio` tags and immutable
`core-nightly-<YYYY.MM.DD>` / `nightly-<YYYY.MM.DD>` pins in that configured
namespace. This describes the publication contract, not existing fork images.

Build from a fork ref containing this migration (the build fetches that ref;
uncommitted local changes are not included):

```bash
UNSLOTH_REF=<fork-commit-sha> bash docker/build.sh
docker build --build-arg BASE_IMAGE=darbot-unsloth:core \
  --build-arg UNSLOTH_STUDIO_REF=<same-fork-commit-sha> \
  -f docker/Dockerfile.studio -t darbot-unsloth:studio docker
```

Both Dockerfiles target `linux/amd64` and `linux/arm64`; each must resolve
compatible wheels successfully. Studio verifies the exact Python ABI and Torch
build against the base. CUDA libraries are deduplicated only when their contents
match, never by linking a CUDA 13 library under a CUDA 12 SONAME.

## Quick start

Needs a CUDA 13-capable NVIDIA driver (580 series or newer) and, on Linux, the NVIDIA Container Toolkit:

```bash
sudo -E bash docker/install_nvidia_toolkit.sh
```

On Windows use Docker Desktop with the WSL 2 backend and a current NVIDIA Windows driver; nothing else to install. Then:

```bash
docker run -d --gpus all --ipc=host \
  --ulimit memlock=-1 --ulimit stack=67108864 \
  -p 8000:8000 -p 8888:8888 \
  -e UNSLOTH_STUDIO_PASSWORD="choose-a-password" \
  -e JUPYTER_PASSWORD="choose-a-password" \
  -v "$PWD":/workspace/host \
  -v "$HOME/.cache/huggingface":/workspace/.cache/huggingface \
  darbot-unsloth:studio
```

`docker run -d` returns at once; follow the startup with `docker logs -f <container>`, which ends with a ready block once both services answer (Studio takes about a minute). Then open Studio at `http://localhost:8000` (user `unsloth`) and JupyterLab at `http://localhost:8888`. Leave either password variable unset and a random one is generated and printed in that log.

The `docker/run.sh` helper in the repository sets these flags for you:

```bash
git clone https://github.com/darbotlabs/darbot-unsloth unsloth && cd unsloth
UNSLOTH_IMAGE=darbot-unsloth:studio UNSLOTH_PORTS="-p 8000:8000 -p 8888:8888" bash docker/run.sh
```

### Notebooks only (`core`)

The `core` image has no service manager. Start JupyterLab on the command line:

```bash
docker run -d --gpus all --ipc=host -p 8888:8888 \
  -v "$PWD":/workspace/host \
  darbot-unsloth:core \
  jupyter lab --ip 0.0.0.0 --port 8888 --allow-root
```

The login token is printed in `docker logs`. With no command the image runs `python`, so a bare `docker run darbot-unsloth:core` exits immediately.

### Scripts

```bash
docker run --rm --gpus all --ipc=host -v "$PWD":/workspace/host \
  darbot-unsloth:core python /workspace/host/train.py
```

### CPU-only hosts

Without a GPU the container refuses to start unless you opt in. Studio chat with GGUF models, JupyterLab and the GGUF tooling work; training does not.

```bash
docker run -d -e UNSLOTH_ALLOW_CPU=1 -p 8000:8000 -p 8888:8888 darbot-unsloth:studio
```

## Supported GPUs

Compiled for `sm_75 sm_80 sm_86 sm_90 sm_100 sm_120`: Turing (T4, RTX 20), Ampere (A100, A10, RTX 30), Ada (L4, L40, RTX 40), Hopper (H100, H200, GH200), Blackwell (B200, GB200, RTX 50, RTX PRO 6000) and GB10 (DGX Spark). The container prints the detected GPU on start and explains what to do when the driver is too old.

Driver requirements:

- 580 series or newer for native CUDA 13 on every architecture.

**Turing (T1000/T4/RTX 20-series, sm_75) is not blanket-rejected.**
Both physical T1000 GPUs passed offline tiny-Llama FP32 manual LoRA SFT and
default 4-bit QLoRA on Windows with Python 3.14.7, Torch 2.14/cu130 and
Triton-Windows 3.8.0.post28. The 4-bit path used seven genuinely packed CUDA
`Linear4bit` layers and verified forward/backward plus optimizer adapter updates.
FP32/4-bit adapter save/reload preserved weights and logits within precision
tolerances; real TensorBoard roundtrips also passed.
These demonstrated tiny-model paths do not certify this Linux image, every model,
or every dtype. Published upstream Turing policy remains separate from these
measurements. Native BF16 acceleration is unavailable on Turing. AMD GPUs are not
supported by these NVIDIA images.

## Ports

| Port | Service | Image |
|---|---|---|
| 8000 | Unsloth Studio | `latest` |
| 8888 | JupyterLab | both |
| 22 | SSH, key only, off unless `SSH_KEY` or `PUBLIC_KEY` is set | `latest` |

## Environment variables

| Variable | Effect |
|---|---|
| `UNSLOTH_STUDIO_PASSWORD` | Initial Studio admin password for user `unsloth`; ignored once a password is stored. Unset: generated once and printed in the logs, and Studio stops after an hour unless it is changed (`UNSLOTH_STUDIO_BOOTSTRAP_TIMEOUT=0` disables). |
| `JUPYTER_PASSWORD` | JupyterLab password. Unset: generated once and printed in the logs. |
| `JUPYTER_PORT` | JupyterLab port inside the container. Default `8888`. |
| `SSH_KEY` or `PUBLIC_KEY` | OpenSSH public key for root login. Enables sshd on port 22. Password login is never enabled. |
| `UNSLOTH_ALLOW_CPU=1` | Allow starting without a GPU. |
| `UNSLOTH_JUPYTER_CLOUDFLARE=1` | Publish JupyterLab through a Cloudflare quick tunnel and print the URL. |
| `UNSLOTH_SKIP_NOTEBOOK_SYNC=1` | Do not refresh the notebooks from GitHub on start. |
| `HF_TOKEN`, `WANDB_API_KEY` | Forwarded to Hugging Face and Weights and Biases. |

## Volumes

The working directory is `/workspace`. Mount what you want to keep:

| Container path | What it holds |
|---|---|
| `/workspace/host` | Your files. Mount your project directory here. |
| `/workspace/.cache/huggingface` | Model downloads. Mount your host HF cache to reuse it. |
| `/workspace/.cache/triton` | Compiled kernels. Optional, speeds up restarts. |
| `/workspace/unsloth-notebooks` | The synced notebooks. Your edits are kept across refreshes. |
| `/workspace/Unsloth Notebooks` | The same notebooks grouped by topic, rebuilt on each start. |

The container runs as root by default. `--user <uid>:<gid>` is supported and keeps files on your mounts owned by you.

## Updating inside a running container

On the `latest` image:

- Rebuild matching base and Studio images to update this fork; the upstream
  in-place PyPI updater is disabled to preserve the companion and CUDA ABI.
- `unsloth-llama-update` fetches the newest prebuilt llama.cpp.
- `unsloth-jupyter-tunnel` opens a Cloudflare quick tunnel to JupyterLab.

On both images the notebooks refresh from GitHub on each start unless `UNSLOTH_SKIP_NOTEBOOK_SYNC=1`. Pull a new image tag to update everything else.

## Help

- [Documentation](https://docs.unsloth.ai)
- [r/unsloth](https://reddit.com/r/unsloth)
- [Issues](https://github.com/unslothai/unsloth/issues)

## License

AGPL-3.0, following the main repository. See [LICENSE](https://github.com/unslothai/unsloth/blob/main/LICENSE).
