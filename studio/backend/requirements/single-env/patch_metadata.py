#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2026-present the Unsloth AI Inc. team. All rights reserved. See /studio/LICENSE.AGPL-3.0

"""Compatibility entry point for older installers; never rewrite METADATA.

Data Designer 0.9.2 and datasets 5 share the supported hub 1.x / Arrow 24
contract. Resolve the published requirements with constraints.txt instead of
concealing incompatible distributions from pip check.
"""


def main() -> int:
    print("single-env metadata patch: unnecessary; published metadata is unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
