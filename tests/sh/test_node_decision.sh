#!/bin/bash
# Unit tests for decide_node_source() from studio/setup.sh.
# Slices the pure function out of setup.sh and exercises the three outcomes:
#   system  -- Node ^22.13 or >=24 and npm>=11.10 satisfy the frontend toolchain
#   bundled -- otherwise install an isolated Node (the Discord-reported npm-only case)
#   skip    -- UNSLOTH_SKIP_NODE_INSTALL=1 and the system is unsuitable
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SETUP_SH="$SCRIPT_DIR/../../studio/setup.sh"
PASS=0
FAIL=0

_FUNC_FILE=$(mktemp)
sed -n '/^decide_node_source()/,/^}/p' "$SETUP_SH" > "$_FUNC_FILE"
if [ ! -s "$_FUNC_FILE" ]; then
    echo "FAIL: could not extract decide_node_source from $SETUP_SH"
    exit 1
fi
# shellcheck disable=SC1090
. "$_FUNC_FILE"

assert_decision() {
    _label="$1"; _node="$2"; _npm="$3"; _skip="$4"; _expected="$5"
    _actual="$(decide_node_source "$_node" "$_npm" "$_skip")"
    if [ "$_actual" = "$_expected" ]; then
        echo "  PASS: $_label (node='$_node' npm='$_npm' skip='$_skip' -> $_actual)"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: $_label (node='$_node' npm='$_npm' skip='$_skip' expected '$_expected', got '$_actual')"
        FAIL=$((FAIL + 1))
    fi
}

echo "decide_node_source"
# system: both satisfy
assert_decision "node22 + npm11"      "v22.17.1" "11.13.0" "0" system
assert_decision "former node20 floor is no longer supported" "v20.19.0" "11.0.0" "0" bundled
assert_decision "node24 + npm11"      "v24.17.0" "11.13.0" "0" system
assert_decision "former node23 allowance is no longer supported" "v23.5.0" "11.0.0" "0" bundled
assert_decision "exact current floors" "v22.13.0" "11.10.0" "0" system
assert_decision "verified Node and bundled npm" "v26.8.1" "11.19.0" "0" system
assert_decision "newer npm major" "v26.8.1" "12.0.0" "0" system
assert_decision "npm just below floor" "v26.8.1" "11.9.9" "0" bundled
assert_decision "node just below floor" "v22.12.0" "11.10.0" "0" bundled
assert_decision "unsupported node23 with current npm" "v23.5.0" "11.10.0" "0" bundled

# bundled: the reported bug -- fine Node, stale npm
assert_decision "node22 + npm10 (bug)" "v22.17.1" "10.9.2" "0" bundled
# bundled: node too old / wrong line
assert_decision "node18"               "v18.20.0" "11.0.0" "0" bundled
assert_decision "node22.11 (<22.12)"   "v22.11.0" "11.0.0" "0" bundled
assert_decision "node20.18 (<20.19)"   "v20.18.0" "11.0.0" "0" bundled
assert_decision "node21 (odd)"         "v21.7.0"  "11.0.0" "0" bundled
# bundled: missing entirely
assert_decision "no node/npm"          ""         ""       "0" bundled
# bundled: garbage versions
assert_decision "garbage versions"     "vfoo"     "bar"    "0" bundled

# skip: unsuitable + skip flag
assert_decision "npm10 + skip"         "v22.17.1" "10.9.2" "1" skip
assert_decision "missing + skip"       ""         ""       "1" skip
# skip flag does NOT override an already-good system
assert_decision "good system + skip"   "v22.17.1" "11.13.0" "1" system

rm -f "$_FUNC_FILE"
echo ""
echo "Passed: $PASS  Failed: $FAIL"
[ "$FAIL" -eq 0 ] || exit 1
