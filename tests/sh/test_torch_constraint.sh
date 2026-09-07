#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2026-present the Unsloth AI Inc. team. All rights reserved.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# Exercise the actual defaults, not a copied model of the installer.
eval "$(sed -n '/^TORCH_CONSTRAINT=/,/^# ── Resolve repo root/p' "$ROOT/install.sh" | sed '$d')"
test "$TORCH_CONSTRAINT" = 'torch==2.14.0'
test "$TORCHVISION_CONSTRAINT" = 'torchvision==0.29.0'
test "$TORCHAUDIO_CONSTRAINT" = 'torchaudio==2.11.0'

# Every literal branch must keep the policy; hardware cannot restore an old cap.
! grep -E '^[[:space:]]*TORCH_CONSTRAINT="torch[>=]' "$ROOT/install.sh" \
    | grep -vF 'torch==2.14.0'
! grep -E '^[[:space:]]*TORCHVISION_CONSTRAINT="torchvision[>=]' "$ROOT/install.sh" \
    | grep -vF 'torchvision==0.29.0'
! grep -E '^[[:space:]]*TORCHAUDIO_CONSTRAINT="torchaudio[>=]' "$ROOT/install.sh" \
    | grep -vF 'torchaudio==2.11.0'
! grep -F 'torchaudio==2.${_itdi_minor}' "$ROOT/install.sh"
grep -qF 'TORCH_INDEX_URL="${_policy_index_base%/}/cu130"' "$ROOT/install.sh"
grep -qF 'Torch 2.14 wheels are required; no legacy backend fallback' "$ROOT/install.sh"
grep -qF 'TORCH_CONSTRAINT="torch==2.14.0+rocm7.2"' "$ROOT/scripts/install_rocm_wsl_strixhalo.sh"
grep -qF 'TORCH_INDEX="${_torch_base%/}/rocm7.2"' "$ROOT/scripts/install_rocm_wsl_strixhalo.sh"

eval "$(sed -n '/^_torch_index_url_leaf()/,/^}/p' "$ROOT/install.sh")"
backend_policy="$(sed -n '/^# CUDA 13 is the supported wheel family/,/^_PREV_TORCH_PIN=/p' "$ROOT/install.sh" | sed '$d')"
test -n "$backend_policy"
substep() { :; }
C_WARN=""
for family in cpu xpu cu130 rocm7.2; do
    (
        SKIP_TORCH=false
        _torch_index_pinned=true
        TORCH_INDEX_URL="https://download.pytorch.org/whl/$family"
        eval "$backend_policy"
        test "$TORCH_INDEX_URL" = "https://download.pytorch.org/whl/$family"
    )
done
for family in cu128 rocm6.4 gfx1151; do
    if (
        SKIP_TORCH=false
        _torch_index_pinned=true
        TORCH_INDEX_URL="https://download.pytorch.org/whl/$family"
        eval "$backend_policy"
    ) 2>/dev/null; then
        echo "FAIL: explicitly requested legacy $family was silently accepted"
        exit 1
    fi
done
for pair in cu128:cu130 rocm6.4:rocm7.2 gfx1151:rocm7.2; do
    (
        SKIP_TORCH=false
        _torch_index_pinned=false
        UNSLOTH_PYTORCH_MIRROR="https://mirror.example/whl/"
        TORCH_INDEX_URL="$UNSLOTH_PYTORCH_MIRROR${pair%:*}"
        eval "$backend_policy"
        test "$TORCH_INDEX_URL" = "$UNSLOTH_PYTORCH_MIRROR${pair#*:}"
    )
done

# Full installs resolve Zoo before Core; Torch-free installs defer Zoo entirely.
source_install="$(sed -n '/^_install_fork_source()/,/^}/p' "$ROOT/install.sh")"
test -n "$source_install"
zoo_line="$(printf '%s\n' "$source_install" | grep -n 'install vendored Zoo"' | cut -d: -f1)"
core_line="$(printf '%s\n' "$source_install" | grep -n 'install local Core"' | cut -d: -f1)"
test "$zoo_line" -lt "$core_line"
! printf '%s\n' "$source_install" | grep -qF -- '--no-deps'
! printf '%s\n' "$source_install" | grep -qF 'git+https://github.com/unslothai/unsloth-zoo'

eval "$source_install"
calls=()
run_install_cmd_retry() { calls+=("$*"); }
_REPO_IS_CHECKOUT=1
_REPO_ROOT="$ROOT"
_VENV_PY="/dedicated environment/bin/python"
SKIP_TORCH=false
_install_fork_source
test "${#calls[@]}" -eq 2
test "${calls[0]}" = "install vendored Zoo $_VENV_PY $ROOT/studio/install_zoo.py --python $_VENV_PY"
test "${calls[1]}" = "install local Core uv pip install --python $_VENV_PY -e $ROOT $TORCH_CONSTRAINT $TORCHVISION_CONSTRAINT $TORCHAUDIO_CONSTRAINT"

calls=()
SKIP_TORCH=true
_install_fork_source
test "${#calls[@]}" -eq 1
test "${calls[0]}" = "install local Core (no-torch) uv pip install --python $_VENV_PY -e $ROOT[studio] -r $ROOT/studio/backend/requirements/no-torch-runtime.txt --constraint $ROOT/studio/backend/requirements/no-torch-constraints.txt"
# Normal resolution is safe only with the actual Torch-free profile, not the old
# list of training packages that was installed with missing dependencies.
! grep -Ei '^(torch|torchvision|torchaudio|torchcodec|peft|accelerate|trl|sentence[-_]transformers|cut[-_]cross[-_]entropy|unsloth[-_]zoo|triton([-_](windows|xpu|rocm))?)([^[:alnum:]_-]|$)' \
    "$ROOT/studio/backend/requirements/no-torch-runtime.txt"

calls=()
_REPO_IS_CHECKOUT=0
if _install_fork_source 2>/dev/null; then
    echo "FAIL: missing checkout accepted"
    exit 1
fi
test "${#calls[@]}" -eq 0

source_guard="$(sed -n '/^# ── Tauri structured output/,/^tauri_log()/p' "$ROOT/install.sh" | sed '1d;$d')"
test -n "$source_guard"
if (
    unset UNSLOTH_CI_SOURCE_OVERLAY
    STUDIO_LOCAL_INSTALL=false
    _SHORTCUTS_ONLY=false
    eval "$source_guard"
) 2>/dev/null; then
    echo "FAIL: source-less installation accepted"
    exit 1
fi
(
    UNSLOTH_CI_SOURCE_OVERLAY="$ROOT"
    STUDIO_LOCAL_INSTALL=false
    _SHORTCUTS_ONLY=false
    eval "$source_guard"
    test "$STUDIO_LOCAL_INSTALL" = true
)
(
    unset UNSLOTH_CI_SOURCE_OVERLAY
    STUDIO_LOCAL_INSTALL=false
    _SHORTCUTS_ONLY=true
    eval "$source_guard"
)
# A root bootstrap must not let the shared pass advance an explicit checkout.
handoff="$(awk '
    /^_run_setup_with_studio_home\(\)/ { seen = 1 }
    seen && /^if \[ "\$STUDIO_LOCAL_INSTALL" = true \]; then/ { emit = 1 }
    emit && /^if \[ "\$_SETUP_EXIT"/ { exit }
    emit { print }
' "$ROOT/install.sh")"
test -n "$handoff"
_handoff=()
_run_setup_with_studio_home() { _handoff=("$@"); }
STUDIO_LOCAL_INSTALL=true
UNSLOTH_CORE_TRACKING_REF=main
_SKIP_BASE=1
_SKIP_FRONTEND=0
PACKAGE_NAME=unsloth
_WITH_LLAMA_CPP_DIR=""
TAURI_MODE=false
SETUP_SH="/not-executed-setup.sh"
eval "$handoff"
printf '%s\n' "${_handoff[@]}" | grep -qx 'UNSLOTH_CORE_TRACKING_REF=pinned'
printf '%s\n' "${_handoff[@]}" | grep -qx 'SKIP_STUDIO_BASE=1'

# Direct setup --local has the same rule; managed nonlocal updates retain theirs.
local_tracking="$(sed -n '/^if \[ "${STUDIO_LOCAL_INSTALL:-0}" = "1" \]; then/,/^fi/p' "$ROOT/studio/setup.sh")"
test -n "$local_tracking"
REPO_ROOT="$ROOT"
STUDIO_LOCAL_INSTALL=1
eval "$local_tracking"
test "$UNSLOTH_CORE_TRACKING_REF" = pinned
STUDIO_LOCAL_INSTALL=0
UNSLOTH_CORE_TRACKING_REF=main
eval "$local_tracking"
test "$UNSLOTH_CORE_TRACKING_REF" = main
echo "PASS: fixed Torch family, independent TorchAudio release, and Zoo bootstrap ordering"
