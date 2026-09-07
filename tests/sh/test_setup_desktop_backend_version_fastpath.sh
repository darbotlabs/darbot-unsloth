#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2026-present the Unsloth AI Inc. team. All rights reserved. See /studio/LICENSE.AGPL-3.0
# Tests that setup.sh's fastpath escapes when UNSLOTH_DESKTOP_BACKEND_VERSION
# requires a backend upgrade even if INSTALLED_VER == LATEST_VER.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SETUP_SH="$SCRIPT_DIR/../../studio/setup.sh"
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

BLK="$WORK/fastpath_blk.sh"

# This test runs the fast path by slicing it out of setup.sh, so every slice
# assumption below is checked and reported as drift. An unchecked slice fails
# as a bare "syntax error near unexpected token" from a temp file the reader
# has never heard of, which is how the elif of #8515 sat red on main: the
# condition text was unchanged, only the keyword in front of it moved, and
# three of the six cases still "passed" because a block that never sourced
# leaves _SKIP_PYTHON_DEPS at its false default.
drift() {
    echo "FATAL: the fast-path extraction no longer matches $SETUP_SH -- $1" >&2
    echo "       Fix the extraction in $0 (or the block in setup.sh), do not silence it:" >&2
    echo "       start anchor is the INSTALLED_VER = LATEST_VER condition (any if/elif keyword)," >&2
    echo "       end anchor is the first _setup_pin= assignment after it." >&2
    exit 1
}

# Matched as a literal, and deliberately without the leading keyword: the block
# is reached by an elif today and was reached by an if before #8515, and which
# one it is has no bearing on what this test exercises. The keyword is checked
# separately below and normalised to a plain `if` on the way out, so the slice
# is always a standalone, parseable construct.
FASTPATH_COND='[ -n "$INSTALLED_VER" ] && [ -n "$LATEST_VER" ] && [ "$INSTALLED_VER" = "$LATEST_VER" ]; then'

_extract_status=0
awk -v COND="$FASTPATH_COND" '
    index($0, COND) > 0 { starts++ }
    !on && index($0, COND) > 0 {
        prefix = substr($0, 1, index($0, COND) - 1)
        if (prefix !~ /^[ \t]*(el)?if $/) { bad_prefix = prefix; next }
        on = 1
        print "if " COND
        next
    }
    on && !ended && $0 ~ /^[ \t]*_setup_pin=/ { ended = 1; next }
    on && !ended { body++; print }
    END {
        if (starts != 1) { print starts + 0 > "/dev/stderr"; exit 3 }
        if (!on) { print bad_prefix > "/dev/stderr"; exit 4 }
        if (!ended) { exit 5 }
        if (body == 0) { exit 6 }
        print "fi"
    }
' "$SETUP_SH" > "$BLK" 2> "$WORK/extract_err" || _extract_status=$?

case "$_extract_status" in
    0) ;;
    3) drift "expected exactly 1 line holding the fast-path condition, found $(cat "$WORK/extract_err")" ;;
    4) drift "the fast-path condition is no longer introduced by if/elif (leading text: '$(cat "$WORK/extract_err")')" ;;
    5) drift "the end anchor (_setup_pin=) no longer follows the fast-path condition" ;;
    6) drift "the fast-path block is empty" ;;
    *) drift "the extraction failed with status $_extract_status" ;;
esac

# The slice has to still contain what this test claims to test. Without these
# the extraction could shrink to nothing meaningful and every case would pass.
grep -q '_SKIP_PYTHON_DEPS=true' "$BLK" \
    || drift "the extracted block never sets _SKIP_PYTHON_DEPS=true"
grep -q 'UNSLOTH_DESKTOP_BACKEND_VERSION' "$BLK" \
    || drift "the extracted block no longer consults UNSLOTH_DESKTOP_BACKEND_VERSION"

# The part that matters: a slice that does not parse is drift, not a test failure.
if ! _syntax_err=$(bash -n "$BLK" 2>&1); then
    echo "--- extracted block ---" >&2
    cat -n "$BLK" >&2
    echo "--- bash -n ---" >&2
    echo "$_syntax_err" >&2
    drift "the extracted block is not valid bash (see above)"
fi

PASS=0
FAIL=0

check() {
    local label="$1"
    local got="$2"
    local want="$3"
    if [ "$got" = "$want" ]; then
        echo "  PASS: $label (got=$got)"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: $label (got=$got, want=$want)"
        FAIL=$((FAIL + 1))
    fi
}

# Create a mock venv that runs Python without site-packages, exercising setup's fallback parser.
VENV_DIR="$WORK/mock_venv"
mkdir -p "$VENV_DIR/bin"
cat << 'EOF' > "$VENV_DIR/bin/python"
#!/bin/sh
exec python3 -S "$@"
EOF
chmod +x "$VENV_DIR/bin/python"

# Mock install_manifest to return ok: True so manifest check passes
cat > "$WORK/install_manifest.py" <<'PY'
import os
from pathlib import Path

def verify_install(**kwargs):
    return {"ok": True}

def venv_root():
    return Path(os.environ["TEST_SOURCE_VENV"])

def _installed_metadata_records(name):
    return []
PY

eval_fastpath() {
    local installed_ver="$1"
    local latest_ver="$2"
    local desktop_ver="${3:-}"
    (
        INSTALLED_VER="$installed_ver"
        LATEST_VER="$latest_ver"
        UNSLOTH_DESKTOP_BACKEND_VERSION="$desktop_ver"
        _PKG_NAME="unsloth"
        SCRIPT_DIR="$WORK"
        _SKIP_PYTHON_DEPS=false
        # false is also what a block that never ran leaves behind, so three of
        # the six cases below would pass on a block that did nothing at all.
        # Both ways that can happen report themselves instead.
        _STEP_CALLS=0
        step() { _STEP_CALLS=$((_STEP_CALLS + 1)); }
        substep() { :; }

        # Execute extracted block
        # shellcheck disable=SC1090
        . "$BLK" || { echo "BLOCK_FAILED_TO_RUN"; exit 0; }
        [ "$_STEP_CALLS" -gt 0 ] || { echo "BLOCK_NOT_ENTERED"; exit 0; }
        echo "$_SKIP_PYTHON_DEPS"
    )
}

echo "Testing UNSLOTH_DESKTOP_BACKEND_VERSION fastpath escape in setup.sh:"

# 1. When versions match and no desktop version required -> skips python deps
check "matching versions, no desktop requirement" \
    "$(eval_fastpath '2026.8.15' '2026.8.15' '')" "true"

# 2. When installed version satisfies desktop requirement -> skips python deps
check "installed satisfies desktop requirement" \
    "$(eval_fastpath '2026.8.15' '2026.8.15' '2026.8.15')" "true"

check "installed exceeds desktop requirement" \
    "$(eval_fastpath '2026.8.16' '2026.8.16' '2026.8.15')" "true"

# 3. When installed version is older than desktop requirement -> escapes fastpath (_SKIP_PYTHON_DEPS=false)
check "installed older than desktop requirement (2026.8.4 < 2026.8.15)" \
    "$(eval_fastpath '2026.8.4' '2026.8.4' '2026.8.15')" "false"

check "installed older than desktop requirement (2026.8.14 < 2026.8.15)" \
    "$(eval_fastpath '2026.8.14' '2026.8.14' '2026.8.15')" "false"

# 4. Without packaging, a suffix cannot be ordered safely, so force the dependency pass.
check "post-release requirement forces dependency pass without packaging" \
    "$(eval_fastpath '2026.8.15' '2026.8.15' '2026.8.15.post1')" "false"

echo "Testing source-registry tracking before the version fastpath:"
TRACKING_BLK="$WORK/tracking_blk.sh"
sed -n '/^_SKIP_PYTHON_DEPS=false/,/^_PKG_NAME=/p' "$SETUP_SH" | sed '$d' > "$TRACKING_BLK"
grep -q '_core_tracking_intent(stack._core_repair_source' "$TRACKING_BLK" \
    || drift "the source-tracking guard was not extracted"
bash -n "$TRACKING_BLK" || drift "the source-tracking guard is invalid"

# Load the actual stdlib-only source/provenance functions, not a copied resolver.
# The fake interpreter has no site-packages, so unrelated installer imports stay out.
cat > "$WORK/install_python_stack.py" <<'PY'
import ast
import json
import os
from pathlib import Path
import re
import sys
import urllib.request

import install_manifest

SCRIPT_DIR = install_manifest.venv_root() / "lib" / "site-packages" / "studio"
sys.path.insert(0, str(SCRIPT_DIR.parent))
functions = {
    "_core_source_record", "_core_source_from_record", "_core_source_payload",
    "_remembered_core_source", "_core_tracking_intent", "_core_repair_source",
}
constants = {"_CORE_SOURCE_REGISTRY", "_CORE_CHECKOUT_FILES"}
nodes = []
found = set()
source = Path(os.environ["TEST_REAL_STACK"])
for node in ast.parse(source.read_text(encoding="utf-8")).body:
    if isinstance(node, ast.FunctionDef) and node.name in functions:
        nodes.append(node)
        found.add(node.name)
    elif isinstance(node, ast.Assign):
        names = {target.id for target in node.targets if isinstance(target, ast.Name)}
        if names & constants:
            nodes.append(node)
            found.update(names & constants)
if found != functions | constants:
    raise RuntimeError(f"Source resolver extraction drifted: {(functions | constants) - found}")
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), "exec"), globals())
PY

eval_source_tracking() {
    local source_json="$1"
    (
        SCRIPT_DIR="$WORK"
        export TEST_SOURCE_VENV="$VENV_DIR"
        export TEST_REAL_STACK="$(dirname "$SETUP_SH")/install_python_stack.py"
        export UNSLOTH_CORE_TRACKING_REF="${4:-}"
        _COLAB_NO_VENV=false
        SKIP_STUDIO_BASE="${2:-0}"
        STUDIO_LOCAL_INSTALL="${3:-0}"
        if [ -n "$source_json" ]; then
            printf '%s\n' "$source_json" > "$VENV_DIR/.unsloth-studio-source.json"
        else
            rm -f "$VENV_DIR/.unsloth-studio-source.json"
        fi
        metadata="$VENV_DIR/lib/site-packages/unsloth-2026.9.2.dist-info"
        rm -rf "$metadata"
        if [ -n "${5:-}" ]; then
            mkdir -p "$metadata"
            printf 'Metadata-Version: 2.1\nName: unsloth\nVersion: 2026.9.2\n' > "$metadata/METADATA"
            printf '%s\n' "$5" > "$metadata/direct_url.json"
        fi
        substep() { :; }
        . "$TRACKING_BLK"
        if [ "$_SKIP_VERSION_CHECK" != true ] && [ "$SKIP_STUDIO_BASE" != 1 ] \
            && [ "$STUDIO_LOCAL_INSTALL" != 1 ]; then
            _SKIP_PYTHON_DEPS="$(eval_fastpath '2026.9.2' '2026.9.2')"
        fi
        echo "$_SKIP_PYTHON_DEPS"
    )
}
COMMIT=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
LEGACY_SOURCE="{\"schema\":1,\"core\":{\"kind\":\"archive\",\"commit\":\"$COMMIT\"}}"
PINNED_SOURCE="{\"schema\":1,\"tracking\":\"pinned\",\"core\":{\"kind\":\"archive\",\"commit\":\"$COMMIT\"}}"
TRACKED_SOURCE="{\"schema\":1,\"tracking\":\"main\",\"core\":{\"kind\":\"archive\",\"commit\":\"$COMMIT\"}}"
PEP610_MAIN="{\"url\":\"https://github.com/darbotlabs/darbot-unsloth.git\",\"vcs_info\":{\"commit_id\":\"$COMMIT\",\"requested_revision\":\"main\"}}"
PEP610_DEFAULT="{\"url\":\"https://github.com/darbotlabs/darbot-unsloth.git\",\"vcs_info\":{\"commit_id\":\"$COMMIT\"}}"
PEP610_PIN="{\"url\":\"https://github.com/darbotlabs/darbot-unsloth.git\",\"vcs_info\":{\"commit_id\":\"$COMMIT\",\"requested_revision\":\"$COMMIT\"}}"
CHECKOUT="$WORK/checkout"
mkdir -p "$CHECKOUT/studio/backend/vendor/unsloth_zoo_compat"
for file in pyproject.toml studio/install_zoo.py studio/python_policy.py \
    studio/backend/vendor/unsloth_zoo_compat/pyproject.toml; do
    printf 'fixture\n' > "$CHECKOUT/$file"
done
PEP610_EDITABLE=$(python3 -c 'import json,sys; from pathlib import Path; print(json.dumps({"url":Path(sys.argv[1]).resolve().as_uri(),"dir_info":{"editable":True}}))' "$CHECKOUT")
check "main tracking advances despite identical package versions" \
    "$(eval_source_tracking "$TRACKED_SOURCE")" false
check "pinned source retains the package-version fastpath" \
    "$(eval_source_tracking "$PINNED_SOURCE")" true
check "legacy unmarked archive without VCS intent remains fixed" \
    "$(eval_source_tracking "$LEGACY_SOURCE")" true
check "explicit main overrides a retained pinned archive" \
    "$(eval_source_tracking "$PINNED_SOURCE" 0 0 main)" false
check "registryless PEP610 main reaches the tracked updater" \
    "$(eval_source_tracking '' 0 0 '' "$PEP610_MAIN")" false
check "registryless implicit fork default reaches the tracked updater" \
    "$(eval_source_tracking '' 0 0 '' "$PEP610_DEFAULT")" false
check "explicit registry pin wins over PEP610 main intent" \
    "$(eval_source_tracking "$PINNED_SOURCE" 0 0 '' "$PEP610_MAIN")" true
check "registryless PEP610 commit remains pinned" \
    "$(eval_source_tracking '' 0 0 '' "$PEP610_PIN")" true
check "editable PEP610 stays fixed despite inherited main" \
    "$(eval_source_tracking '' 0 0 main "$PEP610_EDITABLE")" true
check "explicit pin overrides retained main tracking" \
    "$(eval_source_tracking "$TRACKED_SOURCE" 0 0 pinned)" true
check "missing registry and provenance reach shared repair" \
    "$(eval_source_tracking '')" false
check "malformed registry cannot be certified current" \
    "$(eval_source_tracking '{broken')" false
check "invalid registry shape reaches shared repair" \
    "$(eval_source_tracking '[]')" false
check "bootstrap already bypasses version checks without remote resolution" \
    "$(eval_source_tracking "$TRACKED_SOURCE" 1)" false
check "explicit checkout already reaches its pinned shared pass" \
    "$(eval_source_tracking "$TRACKED_SOURCE" 0 1)" false

echo "Testing shared-base Transformers installation:"
check "fixed shadows are no longer pre-provisioned" \
    "$(grep -Eq 'VENV_T5_|fast_install_sidecar|_NEED_T5_INSTALL' "$SETUP_SH" && echo false || echo true)" true
check "legacy repository environments are not deleted" \
    "$(grep -Eq 'rm -rf "\$REPO_ROOT/\.venv' "$SETUP_SH" && echo false || echo true)" true
check "the shared installer supplies base dependencies" \
    "$(grep -qF 'python "$SCRIPT_DIR/install_python_stack.py"' "$SETUP_SH" && echo true || echo false)" true

echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
