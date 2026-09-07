# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2026-present the Unsloth AI Inc. team. All rights reserved.
"""The managed environment is independent of Studio's persistent data root."""

import os
import sys
from pathlib import Path


def environment_dir(studio_home: Path) -> Path:
    stage = (os.environ.get("UNSLOTH_STUDIO_STAGE_ROOT") or "").strip()
    if stage:
        return Path(stage).expanduser().resolve() / "unsloth_studio"
    override = (os.environ.get("UNSLOTH_ENV_DIR") or "").strip()
    if override:
        path = Path(override)
        if not path.is_absolute():
            raise ValueError("UNSLOTH_ENV_DIR must be an absolute virtual environment path")
        return path.resolve()
    prefix = Path(sys.prefix)
    try:
        if (prefix / ".unsloth-studio-owned").is_file():
            recorded_home = (prefix / ".unsloth-studio-home").read_text(encoding = "utf-8").strip()
            if recorded_home and Path(recorded_home).resolve() == studio_home.resolve():
                return prefix.resolve()
    except (OSError, ValueError):
        pass
    return studio_home / "unsloth_studio"
