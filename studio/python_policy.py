# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2026-present the Unsloth AI Inc. team. All rights reserved.
"""Interpreter policy shared by dependency installation and completion checks."""

import platform
import sys
import sysconfig

PYTHON_REQUIREMENT = "standard-GIL CPython >=3.14.7,<3.15 (not 3.14t)"


def interpreter_identity() -> dict:
    return {
        "implementation": sys.implementation.name,
        "version": platform.python_version(),
        "cache_tag": sys.implementation.cache_tag,
        "soabi": sysconfig.get_config_var("SOABI"),
        "free_threaded": bool(sysconfig.get_config_var("Py_GIL_DISABLED")),
        "platform": sysconfig.get_platform(),
    }


def supported_interpreter(identity: dict | None = None) -> bool:
    identity = interpreter_identity() if identity is None else identity
    try:
        version = tuple(int(part) for part in identity["version"].split("."))
    except (KeyError, TypeError, ValueError, AttributeError):
        return False
    return (
        identity.get("implementation") == "cpython"
        and len(version) == 3
        and (3, 14, 7) <= version < (3, 15, 0)
        and identity.get("free_threaded") is False
    )


def require_supported_interpreter() -> None:
    identity = interpreter_identity()
    if not supported_interpreter(identity):
        raise RuntimeError(f"Unsloth requires {PYTHON_REQUIREMENT}; found {identity}")
