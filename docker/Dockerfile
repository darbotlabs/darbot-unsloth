# syntax=docker/dockerfile:1.7
# -----------------------------------------------------------------------------
# darbotlabs/darbot-unsloth: standard CPython 3.14.7, Torch 2.14 cu130,
# Triton 3.8. Both Linux architectures resolve the same supported stack.
# Wheel availability is checked by the build; GPU runtime support must still
# be tested on the deployment hardware. Windows T1000/sm75 tiny-Llama FP32 LoRA
# and packed 4-bit QLoRA passed; that does not qualify this Linux image or all models.
# xformers and vLLM are not enabled by default: an older compiled extension
# must not force a Torch downgrade. vLLM is an explicit stable-only opt-in.
#
# Build host needs Docker buildkit + buildx, and QEMU binfmt for arm64-on-x86_64;
# nvidia-container-toolkit only for test-time `--gpus all`. No GPU at build time.
# -----------------------------------------------------------------------------

ARG CUDA_VERSION=13.0.0
ARG UBUNTU_VERSION=24.04
ARG PYTHON_VERSION=3.14.7

# Stage 1: builder -- toolkit + dev headers, builds any source extensions.
FROM nvidia/cuda:${CUDA_VERSION}-cudnn-devel-ubuntu${UBUNTU_VERSION} AS builder

# TARGETARCH (buildx: amd64/arm64) selects the unsloth extras matching the
# wheels available for the platform (xformers aarch64 gap -- see header).
ARG TARGETARCH
ARG PYTHON_VERSION
COPY --from=ghcr.io/astral-sh/uv:0.12.10 /uv /uvx /usr/local/bin/
ENV UV_PYTHON_INSTALL_DIR=/opt/python
ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Cross-compile for every current NVIDIA arch (developer.nvidia.com/cuda/gpus):
    #   sm_75 Turing (T4, RTX 20xx) | sm_80 A100/A30 | sm_86 A40/RTX 30xx
    #   sm_89 Ada (L4/L40/RTX 40xx) | sm_90 Hopper (H100/H200/GH200)
    #   sm_100 Blackwell DC (B100/B200/GB200) | sm_120 Blackwell (RTX 50xx, RTX PRO 6000)
    # +PTX allows forward-compatible JIT; this is not a training support claim.
    TORCH_CUDA_ARCH_LIST="7.5;8.0;8.6;8.9;9.0;10.0;12.0+PTX" \
    MAX_JOBS=4 \
    CUDA_HOME=/usr/local/cuda \
    # Build-host-independence guards: the build must NEVER introspect a GPU so all
    # hosts yield byte-identical images.
    # 1) no JIT-compiled sm_NNN blob into unsloth_compiled_cache/ at import.
    UNSLOTH_COMPILE_DISABLE=1 \
    UNSLOTH_COMPILE_OVERWRITE=0 \
    # 2) don't probe torch.cuda.is_available() at setup (would silently skip wheels).
    UNSLOTH_DISABLE_GPU_PROBE=1 \
    # 3) empty CUDA_VISIBLE_DEVICES so stray torch.cuda calls see no devices
    #    (re-enabled at runtime via `docker run --gpus all`).
    CUDA_VISIBLE_DEVICES=""

RUN apt-get update && apt-get install -y --no-install-recommends \
        software-properties-common ca-certificates curl git build-essential \
        ninja-build cmake pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Isolated prefix; never touch the system Python (PEP 668 externally-managed).
# The venv bootstraps pip via ensurepip and gets uv a few lines below.
ENV VENV=/opt/unsloth-venv
RUN uv python install "${PYTHON_VERSION}" \
 && uv venv --python "${PYTHON_VERSION}" --seed "${VENV}" \
 && ${VENV}/bin/python -c 'import sys, sysconfig; assert sys.implementation.name == "cpython" and (3, 14, 7) <= sys.version_info[:3] < (3, 15) and sys.version_info.releaselevel == "final" and not sysconfig.get_config_var("Py_GIL_DISABLED"), "standard CPython >=3.14.7,<3.15 required"'

# Supply the maintained companion to the same resolver transaction as local Core.
# Published Zoo excludes this stack; do not bypass its caps with resolver overrides.
# No flash-attn/xformers is assumed compatible merely because it installs.
ARG UNSLOTH_REF=main
ARG UNSLOTH_REPOSITORY=https://github.com/darbotlabs/darbot-unsloth
RUN set -eux \
 && case "${TARGETARCH:-amd64}" in \
        amd64) UNSLOTH_EXTRA="huggingface"; XFORMERS_PIN="" ;; \
        arm64) UNSLOTH_EXTRA="huggingface"; XFORMERS_PIN="" ;; \
        *)     echo "ERROR: unsupported TARGETARCH=${TARGETARCH}" >&2; exit 1 ;; \
    esac \
 && echo ">> TARGETARCH=${TARGETARCH:-amd64}, unsloth extra=[${UNSLOTH_EXTRA}], xformers=[${XFORMERS_PIN}]" \
 && ${VENV}/bin/pip install "uv==0.12.10" \
 && git init -q /opt/unsloth-src \
 && cd /opt/unsloth-src \
 && git remote add origin "${UNSLOTH_REPOSITORY}" \
 && git fetch -q --depth 1 origin "${UNSLOTH_REF}" \
 && git checkout -q FETCH_HEAD \
 && ZOO_SOURCE="$(${VENV}/bin/python /opt/unsloth-src/studio/install_zoo.py \
        --python ${VENV}/bin/python --print-source)" \
 && ${VENV}/bin/uv pip install \
        --python ${VENV}/bin/python \
        --index-strategy unsafe-best-match \
        --extra-index-url https://download.pytorch.org/whl/cu130 \
        "torch==2.14.0+cu130" "torchvision==0.29.0" "torchaudio==2.11.0" \
        ${XFORMERS_PIN} \
        "triton==3.8.0" "datasets==5.0.1" "scikit-learn==1.9.0" \
        "bitsandbytes>=0.49.2,!=0.46.0,!=0.48.0" \
        "${ZOO_SOURCE}" \
        "/opt/unsloth-src[${UNSLOTH_EXTRA}]" \
        `# structlog is a studio backend dep, not an unsloth[huggingface] dep,` \
        `# but unsloth_cli's train / export / chat / list-checkpoints all import` \
        `# studio.backend.core.*, so without it every one of them dies on` \
        `# ModuleNotFoundError. The last builder stage imports it as a guard.` \
        "timm>=1.0.11" "addict" "structlog" "fastapi==0.141.1"

# vLLM is optional and resolves only stable releases with Torch 2.14 held.
# GRPO's fast_inference=True path is unavailable unless this opt-in succeeds.
# https://docs.vllm.ai/en/latest/getting_started/installation/gpu/
ARG INSTALL_VLLM=0
RUN set -eux \
 && WANT_VLLM=0 \
 && case "${INSTALL_VLLM}" in \
        auto|1|true|yes) WANT_VLLM=1 ;; \
        0|false|no) WANT_VLLM=0 ;; \
        *) echo "ERROR: invalid INSTALL_VLLM=${INSTALL_VLLM}" >&2; exit 1 ;; \
    esac \
 && if [ "${WANT_VLLM}" = "1" ]; then \
        echo ">> installing vLLM (TARGETARCH=${TARGETARCH:-amd64})"; \
        # Explicit && chain, not `set -e` -- POSIX shells disable errexit inside a
        # condition context (verified on dash), masking install failures.
        # Resolve together; never repair an incompatible dependency graph with
        # post-install upgrades that violate an engine's declared caps.
        { ${VENV}/bin/uv pip install \
            --python ${VENV}/bin/python \
            --index-strategy unsafe-best-match \
            --extra-index-url https://download.pytorch.org/whl/cu130 \
            "torch==2.14.0+cu130" "triton==3.8.0" \
            "torchvision==0.29.0" "torchaudio==2.11.0" \
            "datasets==5.0.1" "scikit-learn==1.9.0" "transformers==5.16.1" \
            "vllm>=0.28.0" \
       && ${VENV}/bin/python -c "import vllm; print('vllm', vllm.__version__)" \
       && ${VENV}/bin/python -c "import numpy.testing, numpy; print('numpy', numpy.__version__, 'testing ok')" \
       && ${VENV}/bin/python -c "import numba; print('numba', numba.__version__, 'imports ok')" \
        # flashinfer-jit-cache: precompiled cubins so flashinfer ops skip the JIT
        # path (standalone `vllm serve` dies there for fmha_gen on sm_100a). ~1.5 GB.
        # The version MUST equal the flashinfer-python vLLM resolved: flashinfer
        # raises at import when the two disagree, which takes the vLLM EngineCore
        # down with it and breaks Unsloth's GRPO fast_inference path. So read the
        # resolved version instead of pinning a literal that drifts.
       && FI_VER="$(${VENV}/bin/python -c 'from importlib.metadata import version; print(version("flashinfer-python"))')" \
       && echo ">> flashinfer-python ${FI_VER}, matching flashinfer-jit-cache" \
       && { ${VENV}/bin/uv pip install \
            --python ${VENV}/bin/python \
            --index-url https://flashinfer.ai/whl/cu130 \
            "flashinfer-jit-cache==${FI_VER}" \
         || echo ">> flashinfer-jit-cache ${FI_VER} unavailable for ${TARGETARCH:-amd64}; vllm serve may require nvcc for uncached ops"; } \
        # Whatever happened above, flashinfer has to import: a version mismatch
        # here is silent until the first vLLM engine start.
       && ${VENV}/bin/python -c \
            "import flashinfer; print('OK: flashinfer', flashinfer.__version__, 'imports')" \
       && ${VENV}/bin/uv pip check --python ${VENV}/bin/python \
       && echo ">> vLLM installed with a consistent dependency graph"; \
        } || { \
            echo "ERROR: no validated stable vLLM stack for the fixed Torch 2.14 policy (${TARGETARCH:-amd64})." >&2; \
            exit 1; \
        }; \
    else \
        echo ">> vLLM skipped (INSTALL_VLLM=${INSTALL_VLLM}, TARGETARCH=${TARGETARCH:-amd64})"; \
    fi

# JupyterLab so the image runs unslothai/notebooks out of the box:
#   docker run --gpus all -p 8888:8888 darbot-unsloth:core \
#       jupyter lab --ip 0.0.0.0 --port 8888 --allow-root --no-browser
# Separate pass AFTER the torch pin: pure-Python, never names torch, so uv can't
# disturb the cu130 pin set. Declared by notebook install cells, so bake them:
#   matplotlib   plotting; some trust_remote_code files import it (DeepSeek-OCR)
#   soundfile    TTS audio read/write (bundles libsndfile)
#   evaluate+jiwer  Whisper WER metric
#   tensorboard  default TrainingArguments report_to backend
#   langid       DeepSeek-R1 GRPO reward language-id check
#   easydict     some vision trust_remote_code modeling files
#   protobuf     inherited from Core's Python-only 4.25.9 wheel for CPython 3.14
#   omegaconf    TTS + NeMo-Gym RL notebook configs
#   einx         TTS codec tensor-rearrange (Llasa/Oute/Spark)
#   librosa      Whisper audio features; Numba 0.67 accepts NumPy 2.5.3
#   ftfy         Oute TTS text normalisation
# decord is separate below (no aarch64 wheel). Pinned (==) for reproducible
# rebuilds. The resolve must NOT move torch/numpy/numba (asserted below).
RUN ${VENV}/bin/uv pip install \
        --python ${VENV}/bin/python \
        "jupyterlab==4.6.0" "notebook==7.6.0" "ipywidgets==8.1.8" "matplotlib==3.11.0" \
        "soundfile==0.14.0" "evaluate==0.4.6" "jiwer==4.0.0" "tensorboard==2.20.0" \
        "langid==1.1.6" "easydict==1.13" \
        "omegaconf==2.3.1" "einx==0.4.3" "librosa==1.0.0" "ftfy==6.3.1" \
        "numpy==2.5.3" "numba==0.67.0" \
 && ${VENV}/bin/python -c "import torch, numpy, numba; from importlib.metadata import version; from google.protobuf.internal import api_implementation; assert torch.__version__.startswith('2.14.0+cu130'), torch.__version__; assert numpy.__version__ == '2.5.3', numpy.__version__; assert numba.__version__ == '0.67.0', numba.__version__; assert version('protobuf') == '4.25.9'; assert api_implementation.Type() == 'python'; print('notebook-deps pins OK:', torch.__version__, numpy.__version__, numba.__version__)" \
 && ${VENV}/bin/uv pip check --python ${VENV}/bin/python

# decord (ERNIE-VL video decode) has wheels only for x86_64. Installed alone:
# HARD on amd64 (a missing wheel is a real regression), fail-soft elsewhere.
RUN if [ "${TARGETARCH:-amd64}" = "amd64" ]; then \
        ${VENV}/bin/uv pip install --python ${VENV}/bin/python "decord==0.6.0"; \
    else \
        ${VENV}/bin/uv pip install --python ${VENV}/bin/python "decord==0.6.0" \
        || echo ">> decord skipped (no matching wheel for ${TARGETARCH:-}); ERNIE-VL video decode unavailable"; \
    fi

# Audio decode (torchcodec). The 0.16 wheel must pair with Torch 2.14 and come
# from the cu130 index, matching the rest of the stack rather than a different
# default; (3) its libs dlopen venv torch/NVIDIA libs registered via ld.so.conf.d
# in the runtime stage. Fail-soft on arches without a matching wheel.
RUN set -eux \
 && { ${VENV}/bin/uv pip install \
        --python ${VENV}/bin/python \
        --index-url https://download.pytorch.org/whl/cu130 \
        "torchcodec==0.16.0" \
   && ${VENV}/bin/uv pip install --python ${VENV}/bin/python nvidia-npp; } \
 || echo ">> torchcodec bake skipped (no matching wheel for ${TARGETARCH:-amd64})"

# transformers SIDECARS for per-notebook version activation (see
# unsloth_nb_compat.py). Each sidecar is transformers==X + matched
# huggingface_hub/tokenizers/safetensors, --no-deps into its own --target under
# ${VENV}/tf-sidecars. Prepending one to sys.path swaps transformers without
# touching the cu130 base. This fork ships the current stable 5.16.1 tier.
#
# Every candidate is then VERIFIED against the baked vLLM and dropped if it does
# not survive, because vLLM is version-locked to transformers and a sidecar it
# cannot import does not give the notebook an older transformers -- it gives it
# an ImportError at `import unsloth`, before the first model cell. Historical
# vLLM 0.26 rejected Transformers 4.57.6 and 5.3.0; retain the actual import
# gate instead of assuming the current stable pair is compatible.
#
# vllm.transformers_utils.config is the gate because it is the vLLM module that
# reads the transformers API, it reproduces BOTH failures, and it imports without
# a GPU (the build host has none, so `import unsloth` cannot be used here).
# Deriving the kept set instead of hardcoding it means a later vLLM bump that
# widens or narrows the supported range re-tunes the image by itself. The lowest
# survivor is recorded as the selection FLOOR read by unsloth_nb_compat.
RUN set -eux \
 && if ${VENV}/bin/python -c "import vllm" >/dev/null 2>&1; then HAVE_VLLM=1; else HAVE_VLLM=0; fi \
 && echo ">> sidecar verification: baked vLLM importable=${HAVE_VLLM}" \
 && KEPT="" \
 && for TFV in 5.16.1; do \
        SCRATCH="$(mktemp -d)"; \
        if ! ${VENV}/bin/uv pip install --python ${VENV}/bin/python \
                --target "$SCRATCH" "transformers==${TFV}" >/dev/null 2>&1; then \
            echo ">> sidecar resolve failed for ${TFV}; skipping"; rm -rf "$SCRATCH"; continue; \
        fi; \
        pin() { ls -d "$SCRATCH/$1"-*.dist-info 2>/dev/null \
            | sed -E "s@.*/$1-([0-9][0-9A-Za-z.]*)\.dist-info@\1@" | head -1; }; \
        HFV="$(pin huggingface_hub)"; TKV="$(pin tokenizers)"; SFV="$(pin safetensors)"; \
        rm -rf "$SCRATCH"; \
        DEST="${VENV}/tf-sidecars/t_$(echo "${TFV}" | tr . _)"; \
        ${VENV}/bin/uv pip install --python ${VENV}/bin/python --target "$DEST" --no-deps \
            "transformers==${TFV}" \
            ${HFV:+"huggingface_hub==${HFV}"} \
            ${TKV:+"tokenizers==${TKV}"} \
            ${SFV:+"safetensors==${SFV}"}; \
        if [ "$HAVE_VLLM" = "1" ] && ! PYTHONPATH="$DEST" ${VENV}/bin/python \
                -c "import vllm.transformers_utils.config" >/dev/null 2>&1; then \
            echo ">> sidecar transformers==${TFV} DROPPED -- the baked vLLM cannot import under it:"; \
            PYTHONPATH="$DEST" ${VENV}/bin/python \
                -c "import vllm.transformers_utils.config" 2>&1 | tail -2 || true; \
            rm -rf "$DEST"; \
            continue; \
        fi; \
        KEPT="${KEPT} ${TFV}"; \
        echo ">> sidecar transformers==${TFV} kept (hf_hub=${HFV} tokenizers=${TKV} safetensors=${SFV})"; \
    done \
 && if [ -z "$KEPT" ]; then \
        echo ">> FATAL: no transformers sidecar survived vLLM verification"; exit 1; \
    fi \
 && if [ "$HAVE_VLLM" = "1" ]; then \
        printf '%s\n' $KEPT | sort -V | head -1 > ${VENV}/tf-sidecars/.vllm_min_transformers; \
    fi \
 && echo ">> sidecars kept:${KEPT} floor=$(cat ${VENV}/tf-sidecars/.vllm_min_transformers 2>/dev/null || echo '(none)')" \
 && { du -sh ${VENV}/tf-sidecars || true; }

# Informational pin record (NOT byte-reproducible: pip freeze omits wheel hashes
# and the source ref or optional stable dependencies may move between builds).
RUN ${VENV}/bin/pip freeze --exclude-editable > ${VENV}/requirements.lock.txt \
 && head -50 ${VENV}/requirements.lock.txt

# Strip pip cache & __pycache__ to shrink the runtime layer. The `-name tests`
# strip excludes numpy's tests dirs (numpy 2.4 needs numpy/_core/tests/ or
# `import numpy` breaks). Other verified-safe cuts:
#   * npp: torchcodec dlopens only libnppicc + libnppc; drop the rest (~388MB).
#   * static .a archives (~143MB): link-time only.
#   * nvshmem device .bc (~30MB): device-relink only; host .so kept.
# Do NOT strip headers (torch/include): causal-conv1d / mamba-ssm build against
# them at notebook time with --no-build-isolation.
RUN set -eux \
 && find ${VENV} -depth -type d -name __pycache__ -exec rm -rf {} + \
 && find ${VENV} -depth -type d -name tests \
        ! -path "*numpy/_core/tests*" \
        ! -path "*numpy/tests*" \
        ! -path "*numpy/ma/tests*" \
        -exec rm -rf {} + \
 && rm -rf /root/.cache/pip /root/.cache/uv \
 && SP=${VENV}/lib/python3.14/site-packages \
 && if [ -d "$SP/nvidia/npp/lib" ]; then \
        find "$SP/nvidia/npp/lib" -maxdepth 1 -name 'libnpp*.so.*' \
            ! -name 'libnppicc.so.*' ! -name 'libnppc.so.*' -delete; \
    fi \
 && find ${VENV} -name '*.a' -delete \
 && rm -f "$SP"/nvidia/nvshmem/lib/libnvshmem_device.bc \
 && echo "venv size after prune:" && du -sh ${VENV}

# Build-time verification.
# (1) arch-list check uses the RAW C++ accessor: torch.cuda.get_arch_list()
#     returns [] with no GPU visible (CUDA_VISIBLE_DEVICES is empty here).
# (2) required packages verified via metadata only -- we do NOT import unsloth/
#     unsloth_zoo (their __init__ needs a real CUDA device). Import correctness is
#     exercised at deploy time by smoke_test.py with --gpus all.
RUN TARGETARCH="${TARGETARCH:-amd64}" ${VENV}/bin/python - <<'PY'
import os, platform
target = os.environ.get("TARGETARCH", "amd64")
mach   = platform.machine()
print(f"build target: TARGETARCH={target} platform.machine()={mach}")

import torch
arches = torch._C._cuda_getArchFlags().split()
print("torch", torch.__version__, "cuda", torch.version.cuda)
print("arches:", arches)
assert torch.__version__.startswith("2.14.0"), f"torch silently moved: {torch.__version__}"
assert "+cu130" in torch.__version__, f"cu build silently changed: {torch.__version__}"
assert "sm_100" in arches, f"sm_100 (B200/GB200) missing: {arches}"
# Verify architecture coverage from the resolved cu130 wheel itself.
assert "sm_120" in arches, f"sm_120 missing: {arches}"
print(f"OK: torch 2.14.0+cu130 with sm_100 + sm_120 native SASS intact ({target})")

from importlib.metadata import version, PackageNotFoundError
# xformers is amd64-only (aarch64 wheel gap -- see header).
REQUIRED = ["torch", "triton", "bitsandbytes", "unsloth",
            "unsloth_zoo", "transformers", "trl", "peft", "accelerate"]
missing = []
for pkg in REQUIRED:
    try:
        v = version(pkg.replace("_", "-"))
        print(f"  {pkg:14s} {v}")
    except PackageNotFoundError:
        missing.append(pkg)
if missing:
    raise SystemExit(f"FAIL: missing wheels: {missing}")
print("OK: all required wheels present")

# Lightweight imports: these init without touching CUDA, unlike unsloth.
import importlib
LIGHT_IMPORTS = ["bitsandbytes", "triton"]
for pkg in LIGHT_IMPORTS:
    importlib.import_module(pkg)
print(f"OK: {' + '.join(LIGHT_IMPORTS)} import cleanly on no-GPU host")

# Guard for the studio.backend.core.* closure the unsloth CLI needs (structlog,
# plus starlette via the logging handlers). Runs last in the builder, after vLLM,
# because that is what pulls starlette in.
from studio.backend.core.export import ExportBackend  # noqa: F401
print("OK: the unsloth CLI can reach the studio export backend")
PY

# Stage 2: runtime -- slim, no nvcc, no cuDNN/cuBLAS layers.
# The "-base-" variant drops ~2.7 GB of system CUDA libs we never load: torch
# wheels bake their own cuDNN/cuBLAS into torch/lib/ and resolve via RPATH. The
# base still provides nvidia-smi + libcuda stubs + libnvidia-ml.
FROM nvidia/cuda:${CUDA_VERSION}-base-ubuntu${UBUNTU_VERSION} AS runtime

# The base manifest is multi-arch; buildx picks the right one for
# TARGETPLATFORM at this FROM line, no conditional needed.
ARG TARGETARCH
ARG PYTHON_VERSION
ARG CUDA_VERSION
ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/unsloth-venv/bin:${PATH} \
    HF_HOME=/workspace/.cache/huggingface \
    TRITON_CACHE_DIR=/workspace/.cache/triton \
    # Keep the arch list at runtime so an in-container source build gets the same
    # The runtime must preserve the same SASS coverage as the builder.
    TORCH_CUDA_ARCH_LIST="7.5;8.0;8.6;8.9;9.0;10.0;12.0+PTX"

# System packages needed by the notebooks:
#   zstd    Ollama installer (`curl ollama.com/install.sh | sh`) extracts a zstd tarball
#   ffmpeg  torchcodec dlopens system FFmpeg libs (not bundled in the wheel)
#   wget    notebooks fetch assets with `!wget URL`
#   ninja-build  flashinfer cpp_ext JIT shells out to ninja
#   cuda-nvcc + cudart-dev  flash-linear-attention TileLang JIT-compiles CUDA
#                kernels via nvcc, absent from the -base image
RUN CUDA_PKG="$(echo "${CUDA_VERSION}" | awk -F. '{print $1"-"$2}')" \
    && apt-get update && apt-get install -y --no-install-recommends \
        software-properties-common ca-certificates curl wget git libgomp1 \
        gcc g++ zstd ffmpeg ninja-build \
        "cuda-nvcc-${CUDA_PKG}" "cuda-cudart-dev-${CUDA_PKG}" \
    && test -x /usr/local/cuda/bin/nvcc \
    && rm -rf /var/lib/apt/lists/*
# gcc + g++ + the managed Python headers: Triton's NVIDIA backend compiles a C
# extension (CudaUtils) on first GPU access; without a compiler + headers the
# first forward pass dies with "Failed to find C compiler". ~250MB.

COPY --from=builder /opt/unsloth-venv /opt/unsloth-venv
COPY --from=builder /opt/python /opt/python
COPY --from=builder /opt/unsloth-src /opt/unsloth-src
ENV UV_PYTHON_INSTALL_DIR=/opt/python

# CUDA 13 is native throughout. Never alias a CUDA 13 library to a CUDA 12
# SONAME: matching filenames do not establish ABI compatibility.

# Register the venv's torch + NVIDIA lib dirs with the loader so torchcodec can
# dlopen them. ld.so.conf.d, NOT LD_LIBRARY_PATH: the cache is consulted after
# DT_RUNPATH, so llama.cpp keeps resolving its own $ORIGIN libs first.
# cublas/lib and cu13/lib are here for llama.cpp's libggml-cuda.so, which links
# against libcublas but does not ship it (see the guard after the fetch below).
RUN set -eux \
 && SP=/opt/unsloth-venv/lib/python3.14/site-packages \
 && printf "%s\n" "$SP/torch/lib" "$SP/nvidia/cuda_nvrtc/lib" \
                  "$SP/nvidia/cuda_runtime/lib" "$SP/nvidia/npp/lib" \
                  "$SP/nvidia/cublas/lib" "$SP/nvidia/cu13/lib" \
        > /etc/ld.so.conf.d/zz-unsloth-venv.conf \
 && ldconfig \
 && { /opt/unsloth-venv/bin/python -c \
        "import torchcodec; print('torchcodec', torchcodec.__version__)" \
   || echo ">> torchcodec unavailable on this arch (audio decode falls back)"; }

# Prebuilt llama.cpp so GGUF export works out of the box; without it the first
# export hits install_llama_cpp()'s prompt + slow source build.
#
# NOT studio/install_llama_prebuilt.py: it selects a bundle for the CURRENT host,
# but the build must never introspect the host, so release + asset are pinned by
# build target instead (see fetch_llama_prebuilt.py).
#
# /opt (not /root) so it survives `docker run --user`. Default "latest" resolves
# the newest release; build.sh pins a concrete tag so the cache busts only on new
# releases. --build-arg LLAMA_PREBUILT_TAG=<tag> for a frozen build.
ARG LLAMA_PREBUILT_TAG=latest
COPY fetch_llama_prebuilt.py /tmp/fetch_llama_prebuilt.py
RUN /opt/unsloth-venv/bin/python /tmp/fetch_llama_prebuilt.py \
        "${LLAMA_PREBUILT_TAG}" "${TARGETARCH:-amd64}" /opt/unsloth/llama.cpp \
 && rm -f /tmp/fetch_llama_prebuilt.py \
 && cat /opt/unsloth/llama.cpp/UNSLOTH_PREBUILT_INFO.json

# libggml-cuda.so is loaded with dlopen (ggml_backend_dl), links against
# libcublas, and does not ship it; the CUDA runtime base only carries libcudart.
# A missing libcublas therefore makes the backend fail to load SILENTLY and
# llama.cpp runs on the CPU: measured 1.6 tok/s instead of 222 tok/s for
# gemma-4-E2B UD-Q4_K_XL on a B200, with `--list-devices` printing nothing.
# torch's wheels already ship libcublas for their own CUDA major (registered
# with the loader above); install the bundle's major when it differs. Then fail
# the build on any dependency that is still unresolved, so a silent CPU fallback
# can never ship again. libcuda.so.1 is exempt: that is the driver stub, injected
# by nvidia-container-toolkit at `docker run --gpus`, never present in the image.
# ldd needs no GPU, so this keeps the build host-independent.
#
# The name is not `nvidia-cublas-cu${major}` at every major: NVIDIA dropped the
# suffix at CUDA 13, where `nvidia-cublas-cu13` is only a 0.0.1 sdist whose build
# backend exits 1 with "use nvidia-cublas instead", failing the BUILD, not the
# install. Neither project spans both majors: the unsuffixed one publishes 13.x
# only, and nvidia-cublas-cu12 has no unsuffixed twin. Pin the major so a future
# CUDA 14 cannot install over a 13 bundle; the unresolved-library check below is
# what proves the right wheel landed.
RUN set -eux \
 && CUDA_SO=/opt/unsloth/llama.cpp/libggml-cuda.so \
 && if [ -f "$CUDA_SO" ]; then \
        want="$(ldd "$CUDA_SO" | sed -n 's/^[[:space:]]*\(libcublas\.so\.[0-9]*\)[[:space:]]*=> not found$/\1/p' | head -n1)"; \
        if [ -n "$want" ]; then \
            major="${want##*.}"; \
            if [ "$major" -ge 13 ]; then \
                pkg="nvidia-cublas==${major}.*"; \
            else \
                pkg="nvidia-cublas-cu${major}"; \
            fi; \
            echo ">> $want missing, installing ${pkg}"; \
            /opt/unsloth-venv/bin/uv pip install --python /opt/unsloth-venv/bin/python \
                "${pkg}"; \
            ldconfig; \
        fi; \
        missing="$(ldd "$CUDA_SO" | grep 'not found' | grep -v 'libcuda\.so\.1 ' || true)"; \
        if [ -n "$missing" ]; then \
            echo "ERROR: llama.cpp CUDA backend has unresolved libraries:"; \
            echo "$missing"; \
            echo "GGUF inference would silently fall back to the CPU."; \
            exit 1; \
        fi; \
        echo "OK: llama.cpp CUDA backend dependencies all resolve"; \
    else \
        echo ">> no libggml-cuda.so in this bundle (CPU-only build)"; \
    fi
# Verify the completed runtime, including the optional CUDA-library installation.
RUN /opt/unsloth-venv/bin/uv pip check --python /opt/unsloth-venv/bin/python \
 && /opt/unsloth-venv/bin/python -c "from importlib.metadata import version; from google.protobuf.internal import api_implementation; assert version('protobuf') == '4.25.9'; assert api_implementation.Type() == 'python'"
ENV UNSLOTH_LLAMA_CPP_PATH=/opt/unsloth/llama.cpp

WORKDIR /workspace
# World-writable so `docker run --user <uid>` (documented non-root use) can
# create notebooks and populate the default caches without a bind mount.
RUN mkdir -p ${HF_HOME} ${TRITON_CACHE_DIR} \
 && chmod -R a+rwX /workspace

# Per-notebook transformers version activation -- run unslothai/notebooks
# UNCHANGED (see unsloth_nb_compat.py). Pieces:
#   * unsloth_nb_compat.py: tier detection + sidecar resolution + IPython hook.
#   * pip/uv shim on a PATH dir AHEAD of the venv bin: makes `!pip install` cells
#     safe + idempotent (keeps the baked stack, records requested transformers).
#   * unsloth_nb_pip_magic.py: re-points `%pip`/`%uv` and `!python -m pip` at the
#     same shim so in-process installs can't bypass PATH.
#   * IPython startup hook: activates the right sidecar before the first model cell.
#   * unsloth-run: headless `unsloth-run <notebook|url>`, the robust driven path.
COPY unsloth_nb_compat.py unsloth_pip_shim.py unsloth_nb_pip_magic.py unsloth_ipython_startup.py unsloth_run.py unsloth_sync_notebooks.sh unsloth_nb_content_sig.py unsloth_nb_view.py unsloth_nb_strip_colab.py unsloth_colab_compat.py /opt/unsloth-nb/
RUN set -eux \
 && SP=/opt/unsloth-venv/lib/python3.14/site-packages \
 && cp /opt/unsloth-nb/unsloth_nb_compat.py "$SP/unsloth_nb_compat.py" \
 && cp /opt/unsloth-nb/unsloth_nb_pip_magic.py "$SP/unsloth_nb_pip_magic.py" \
 && cp /opt/unsloth-nb/unsloth_colab_compat.py "$SP/unsloth_colab_compat.py" \
 && chmod +x /opt/unsloth-nb/unsloth_pip_shim.py /opt/unsloth-nb/unsloth_run.py /opt/unsloth-nb/unsloth_sync_notebooks.sh /opt/unsloth-nb/unsloth_nb_content_sig.py /opt/unsloth-nb/unsloth_nb_view.py /opt/unsloth-nb/unsloth_nb_strip_colab.py \
 && mkdir -p /opt/unsloth-nb/bin \
 && for t in pip pip3 uv; do ln -sf /opt/unsloth-nb/unsloth_pip_shim.py /opt/unsloth-nb/bin/$t; done \
 && ln -sf /opt/unsloth-nb/unsloth_run.py /usr/local/bin/unsloth-run \
 && ln -sf /opt/unsloth-nb/unsloth_sync_notebooks.sh /usr/local/bin/unsloth-sync-notebooks \
 && ln -sf /opt/unsloth-nb/unsloth_nb_content_sig.py /usr/local/bin/unsloth-nb-content-sig \
 && ln -sf /opt/unsloth-nb/unsloth_nb_view.py /usr/local/bin/unsloth-nb-view \
 && ln -sf /opt/unsloth-nb/unsloth_nb_strip_colab.py /usr/local/bin/unsloth-nb-strip-colab \
 && mkdir -p /opt/unsloth-nb/ipython/profile_default/startup \
 && cp /opt/unsloth-nb/unsloth_ipython_startup.py /opt/unsloth-nb/ipython/profile_default/startup/00-unsloth-nb.py \
 && chmod -R a+rX /opt/unsloth-nb/ipython \
 && chmod 1777 /opt/unsloth-nb/ipython /opt/unsloth-nb/ipython/profile_default \
 && /opt/unsloth-venv/bin/python -c "import sys, glob; sys.path.insert(0, '$SP'); import unsloth_nb_compat, unsloth_colab_compat; print('nb-compat OK; baked sidecars:', sorted(glob.glob('/opt/unsloth-venv/tf-sidecars/t_*')))" \
 && /opt/unsloth-venv/bin/python /opt/unsloth-nb/unsloth_pip_shim.py --unsloth-selfcheck-value-flags
# Shim dir AHEAD of the venv bin so `!pip`/`!uv` resolve to the shim, not the real tool.
ENV PATH=/opt/unsloth-nb/bin:${PATH}
# Load the notebook startup hook for EVERY kernel, any uid: IPYTHONDIR points
# IPython at this shared profile, so it loads under `--user <uid>` too (unlike
# /root/.ipython).
#
# The profile has to be WRITABLE by that uid, which is what the 1777 above is for.
# IPython.paths.get_ipython_dir() discards an IPYTHONDIR it cannot write to and
# silently substitutes tempfile.mkdtemp(), and an empty temp profile has no
# startup/ -- so a root-owned 0755 profile did not merely lose history.sqlite, it
# dropped the hook entirely and every kernel under `--user <uid>` ran with no
# sidecar activation, no %pip/%uv magic and no colab-compat. ProfileDir then also
# creates security/, log/, pid/ and db/ INSIDE profile_default, so making only the
# top dir writable is worse still: the kernel dies on PermissionError. The sticky
# bit keeps the shared hook read-only -- 00-unsloth-nb.py and its startup/ dir stay
# a+rX and no other uid can unlink or rename them.
ENV IPYTHONDIR=/opt/unsloth-nb/ipython

# Pre-clone unslothai/notebooks so JupyterLab opens with them present. Baked as a
# READ-ONLY template (~206MB, .git stripped); on boot the entrypoint copies it to
# /workspace/unsloth-notebooks and best-effort refreshes from GitHub, never
# overwriting a user-touched notebook (see unsloth_sync_notebooks.sh).
#
# UNSLOTH_NOTEBOOKS_REF pins ONE commit/branch/tag so a multi-arch publish bakes
# identical templates into both legs; default "main" tracks the tip.
ARG UNSLOTH_NOTEBOOKS_REF=main
RUN set -eux \
 && git init -q /opt/unsloth-notebooks \
 && git -C /opt/unsloth-notebooks remote add origin https://github.com/unslothai/notebooks \
 && git -C /opt/unsloth-notebooks fetch -q --depth 1 origin "${UNSLOTH_NOTEBOOKS_REF}" \
 && git -C /opt/unsloth-notebooks checkout -q FETCH_HEAD \
 && git -C /opt/unsloth-notebooks rev-parse HEAD > /opt/unsloth-notebooks/.unsloth_template_commit \
 && rm -rf /opt/unsloth-notebooks/.git \
 && du -sh /opt/unsloth-notebooks

# Mount a volume on /workspace to persist the notebooks and caches.
EXPOSE 8888

COPY smoke_test.py /workspace/smoke_test.py
COPY entrypoint.sh /usr/local/bin/unsloth-entrypoint
RUN chmod +x /usr/local/bin/unsloth-entrypoint

# Fast GPU pre-flight checks before user code, each with an actionable error (see
# entrypoint.sh). Bypass for offline tooling: docker run -e UNSLOTH_SKIP_GPU_CHECK=1
ENTRYPOINT ["/usr/local/bin/unsloth-entrypoint"]

# Override examples:
#   docker run --gpus all unsloth/unsloth:latest python /workspace/smoke_test.py
#   docker run --gpus all -it unsloth/unsloth:latest bash
CMD ["python"]
