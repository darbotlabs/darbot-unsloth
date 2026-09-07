#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2026-present the Unsloth AI Inc. team. All rights reserved. See /studio/LICENSE.AGPL-3.0
# UNSLOTH_STUDIO_STAGE_ROOT redirects a background update into a copy of the
# environment, and the whole point is that the live install keeps running and
# keeps working if the staged one is never activated. Anything the setup scripts
# write outside the stage root breaks that. Legacy environments stay untouched;
# mutable helper runtimes and caches must respect staging.
#
# Source-shape assertions: driving either script to those lines needs a real
# managed venv. Both are checked, because the failure is per-platform.
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SETUP_SH="$SCRIPT_DIR/../../studio/setup.sh"
SETUP_PS1="$SCRIPT_DIR/../../studio/setup.ps1"
PASS=0
FAIL=0

check() {
    if [ "$2" = 0 ]; then echo "  PASS: $1"; PASS=$((PASS+1));
    else echo "  FAIL: $1"; FAIL=$((FAIL+1)); fi
}

has() { grep -qF "$2" "$1" && echo 0 || echo 1; }

# ── the runtime root itself ──
check "setup.sh reads the stage override" \
    "$(has "$SETUP_SH" 'STAGE_ROOT="${UNSLOTH_STUDIO_STAGE_ROOT:-}"')"
check "setup.sh falls back to STUDIO_HOME" \
    "$(has "$SETUP_SH" 'RUNTIME_ROOT="${STAGE_ROOT:-$STUDIO_HOME}"')"
check "setup.ps1 reads the stage override" \
    "$(has "$SETUP_PS1" '$env:UNSLOTH_STUDIO_STAGE_ROOT')"
check "setup.ps1 falls back to StudioHome" \
    "$(has "$SETUP_PS1" '$RuntimeRoot = if ($StageRoot) { $StageRoot } else { $StudioHome }')"

# Every venv the update writes has to follow the override, or a staged run
# installs straight into the environment the app is running from.
for v in VENV_DIR; do
    check "setup.sh points $v at RUNTIME_ROOT" \
        "$(grep -qE "^${v}=\"\\\$RUNTIME_ROOT/" "$SETUP_SH" && echo 0 || echo 1)"
done
check "setup.ps1 points VenvDir at RuntimeRoot" \
    "$(grep -qE '^\$VenvDir = Join-Path \$RuntimeRoot ' "$SETUP_PS1" && echo 0 || echo 1)"

# Both installers use shared base Transformers rather than rewriting old trees.
check "setup.sh preserves legacy sidecars during staged and live updates" \
    "$(grep -qE 'VENV_T5_|\.venv_t5' "$SETUP_SH" && echo 1 || echo 0)"
check "setup.ps1 preserves legacy sidecars during staged and live updates" \
    "$(grep -qE 'VenvT5|\.venv_t5' "$SETUP_PS1" && echo 1 || echo 0)"

# The WebView cache belongs to the app that is still running and rendering from it.
check "setup.sh skips the webview cache clear while staging" \
    "$(has "$SETUP_SH" 'if [ -z "$STAGE_ROOT" ] && [ -x "$VENV_DIR/bin/python" ]; then')"
check "setup.ps1 skips the webview cache clear while staging" \
    "$(has "$SETUP_PS1" 'if (-not $StageRoot -and (Test-Path -LiteralPath (Join-Path $VenvDir "Scripts\python.exe") -PathType Leaf)) {')"

check "setup.sh stages the managed Node runtime" \
    "$(has "$SETUP_SH" '_NODE_PARENT="$RUNTIME_ROOT"')"
check "setup.sh stages llama.cpp and whisper.cpp" \
    "$(has "$SETUP_SH" 'UNSLOTH_HOME="$RUNTIME_ROOT"')"
check "setup.sh forwards the staged helper root to whisper.cpp source builds" \
    "$(has "$SETUP_SH" 'env UNSLOTH_HOME="$UNSLOTH_HOME" sh "$_WHISPER_BUILD"')"
check "whisper.cpp source builds honor the managed helper root" \
    "$(has "$SCRIPT_DIR/../../scripts/build_whisper_cpp.sh" '${UNSLOTH_HOME:-}')"
check "setup.sh does not install global uv while staging" \
    "$(has "$SETUP_SH" 'step "uv" "using pip inside the staged environment"')"
check "setup.ps1 stages the managed Node runtime" \
    "$(has "$SETUP_PS1" '$NodeParent = $StageRoot')"
check "setup.ps1 stages llama.cpp and whisper.cpp" \
    "$(grep -qF 'return (Join-Path $StagingRoot "llama.cpp")' "$SETUP_PS1" && grep -qF '$LlamaCppDir = Get-ManagedLlamaCppDir -StagingRoot $StageRoot' "$SETUP_PS1" && grep -qF '$llamaPreflightFailure = Invoke-ManagedLlamaCppPreflight -StagingRoot $StageRoot' "$SETUP_PS1" && echo 0 || echo 1)"
check "setup.ps1 does not persist User PATH while staging" \
    "$(has "$SETUP_PS1" 'Get-Variable -Name StageRoot -ValueOnly -ErrorAction SilentlyContinue')"
check "setup.ps1 leaves vcredist unchanged while staging" \
    "$(has "$SETUP_PS1" 'step "vcredist" "missing; unchanged during staging"')"
check "setup.ps1 leaves long-path policy unchanged while staging" \
    "$(has "$SETUP_PS1" 'step "long paths" "disabled; unchanged during staging"')"
check "setup.ps1 does not install Git while staging" \
    "$(has "$SETUP_PS1" 'Background staging cannot install Git; retry with the foreground updater.')"
check "setup.ps1 preserves foreground Git bootstrap" \
    "$(has "$SETUP_PS1" 'if ($gitNeeded -or -not $StageRoot) {')"
check "setup.ps1 keeps the staging compiler cache under the stage root" \
    "$(has "$SETUP_PS1" 'if ($StageRoot -or $LongPathsEnabled) {')"

# ── the staged activation cannot dot-source a copied Activate script ──
# A venv copied out of $STUDIO_HOME still names the original root in its activate
# scripts, so the staged branch sets PATH itself. Assert-VenvActivated then proves
# `python` really resolves inside the stage.
check "setup.sh activates the staged venv without sourcing the copy" \
    "$(has "$SETUP_SH" 'elif [ -n "$STAGE_ROOT" ] || [ -n "${UNSLOTH_ENV_DIR:-}" ]; then')"
check "setup.ps1 activates the staged venv without dot-sourcing the copy" \
    "$(has "$SETUP_PS1" 'function Enter-StudioVenv {')"
check "setup.ps1 still asserts the interpreter after activating" \
    "$(has "$SETUP_PS1" 'Assert-VenvActivated -VenvDir $VenvDir')"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" = 0 ]
