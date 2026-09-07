# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2026-present the Unsloth AI Inc. team. All rights reserved. See /studio/LICENSE.AGPL-3.0

from importlib import import_module

# Plugin discovery can run while SeedReader itself is being imported. Keep the
# package initializer import-light without removing its existing public exports.
_EXPORT_MODULES = {
    "DEFAULT_CHUNK_OVERLAP": "chunking",
    "DEFAULT_CHUNK_SIZE": "chunking",
    "build_unstructured_preview_rows": "chunking",
    "materialize_unstructured_seed_dataset": "chunking",
    "resolve_chunking": "chunking",
    "UnstructuredSeedSource": "config",
    "UnstructuredSeedReader": "impl",
    "unstructured_seed_plugin": "plugin",
}


def __getattr__(name):
    module = _EXPORT_MODULES.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(f"{__name__}.{module}"), name)
    globals()[name] = value
    return value

__all__ = list(_EXPORT_MODULES)
