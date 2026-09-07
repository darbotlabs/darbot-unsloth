#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2026-present the Unsloth AI Inc. team. All rights reserved.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
helper="$(sed -n '/^select_cuda_jit_tools()/,/^}/p' "$ROOT/docker/entrypoint.sh")"
test -n "$helper"
eval "$helper"

export TRITON_PTXAS_PATH=/custom/ptxas
select_cuda_jit_tools
test "$TRITON_PTXAS_PATH" = /custom/ptxas
unset TRITON_PTXAS_PATH
select_cuda_jit_tools
if [ -x /usr/local/cuda-13.0/bin/ptxas ]; then
    test "$TRITON_PTXAS_PATH" = /usr/local/cuda-13.0/bin/ptxas
else
    test -z "${TRITON_PTXAS_PATH:-}"
fi
! printf '%s\n' "$helper" | grep -qE 'ln -s|libnvrtc\.so\.12'
! grep -q 'libnvrtc.so.12.cu13' "$ROOT/docker/Dockerfile" "$ROOT/docker/Dockerfile.studio"
grep -qF 'diff -qr "$s" "$b"' "$ROOT/docker/Dockerfile.studio"
grep -qF 'test "${BASE_PYTHON}" = "${STUDIO_PYTHON}"' "$ROOT/docker/Dockerfile.studio"
echo "PASS: native CUDA JIT selection, override preservation, ABI-safe deduplication"
