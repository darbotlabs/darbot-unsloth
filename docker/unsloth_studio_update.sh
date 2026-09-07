#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2026-present the Unsloth AI Inc. team. All rights reserved.
set -euo pipefail

# Shared native libraries and the vendored companion must move together.
echo "This fork requires rebuilding matching base and Studio images." >&2
echo "An in-place PyPI update cannot preserve the vendored Zoo companion and CUDA ABI." >&2
echo "Back up Studio data, build from one darbotlabs/darbot-unsloth commit, then recreate the container." >&2
exit 1
