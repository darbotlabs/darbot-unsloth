#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2026-present the Unsloth AI Inc. team. All rights reserved. See /studio/LICENSE.AGPL-3.0

"""Check stdlib/API compatibility against the declared supported Python minor.

This fork runs one full CPython 3.14.7 CI leg, not an older-interpreter matrix.
The workflow declares the exact patch floor; vermin checks the corresponding
major/minor. Runtime guards enforce the patch floor and reject free-threaded
builds. Static analysis supplements, rather than replaces, runtime tests.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WORKFLOW = REPO / ".github" / "workflows" / "studio-backend-ci.yml"

# Both trees the matrix legs actually execute.
# studio-backend-ci lists 'unsloth_cli/**' in its own paths filter and runs `pytest unsloth_cli/tests` as a step on
# every leg, so a post-floor stdlib name on a shipped CLI path was covered by the old 3.10 leg exactly as a backend
# one was. Scanning only the backend would have moved that coverage to the push to main while looking like it had
# replaced it.
ROOTS = (
    REPO / "studio" / "backend",
    REPO / "unsloth_cli",
)

# Everything shipped under studio/backend is scanned.
# The first version of this listed the packages instead, and that is exactly the wrong shape for a floor check: it named
# core, utils and routes and silently missed 116 files, including all of hub, plugins, models, storage, auth, picker and
# state, plus _platform_compat.py which main.py imports directly.
# It also named "loggers.py", which is a directory, so that entry matched nothing at all.
# studio-backend-ci runs `pytest tests/` from studio/backend on every leg, so a 3.11 API in a test file is executed by
# the 3.10 leg exactly as one in a shipped module is.
# With the pull request down to a single 3.13 leg, that leg and this lint would both pass and the failure would arrive
# on the push to main, which is the whole gap this exists to close.
EXCLUDE_PARTS = ("vendor", "node_modules", "__pycache__", ".venv")


# An above-floor symbol reached deliberately is suppressed AT THE SITE, with `# novermin` and a comment saying why, not
# by dropping its file from the scan.
# The one live case is locale.getencoding() in the data-designer plugin's state_store, inside a try/except
# AttributeError with a pre-3.11 fallback.


# The explicit workflow declaration keeps the support floor independent of which
# matrix jobs happen to run. The current declaration includes the 3.14.7 patch
# floor; Vermin checks its minor while runtime policy enforces patch/build details.
FLOOR_KEY = "PYTHON_FLOOR"


def declared_floor() -> tuple[int, int]:
    """The floor the workflow declares, as (major, minor)."""
    text = WORKFLOW.read_text(encoding = "utf-8")
    found = re.search(rf"^\s*{FLOOR_KEY}:\s*['\"]?(\d+)\.(\d+)(?:\.\d+)?['\"]?\s*$", text, re.M)
    if not found:
        raise SystemExit(
            f"{WORKFLOW.name} declares no {FLOOR_KEY}, so this lint has no target. It is "
            f"declared there rather than here so that the number lives with the CI that "
            f"used to test it."
        )
    return int(found.group(1)), int(found.group(2))


def targets() -> list[str]:
    """Every .py the matrix legs ship or execute, found rather than listed."""
    found = []
    for root in ROOTS:
        if not root.is_dir():
            raise SystemExit(f"{root} is gone; the scan would silently stop covering it")
        found.extend(
            str(path)
            for path in sorted(root.rglob("*.py"))
            if not any(part in EXCLUDE_PARTS for part in path.relative_to(root).parts)
        )
    if not found:
        raise SystemExit(f"no python files found under {ROOTS}; the scan would pass on nothing")
    return found


def command_batches(command: list[str], files: list[str], limit: int = 30000):
    """Bound the Windows UTF-16 command line, including quoting and its terminator."""
    batch = []
    for path in files:
        candidate = [*command, *batch, path]
        units = len(subprocess.list2cmdline(candidate).encode("utf-16-le")) // 2 + 1
        if units > limit:
            if not batch:
                raise SystemExit(f"floor checker argument exceeds the command-line limit: {path}")
            yield [*command, *batch]
            batch = []
            units = len(subprocess.list2cmdline([*command, path]).encode("utf-16-le")) // 2 + 1
            if units > limit:
                raise SystemExit(f"floor checker argument exceeds the command-line limit: {path}")
        batch.append(path)
    if batch:
        yield [*command, *batch]


def main() -> int:
    floor = declared_floor()
    target = f"{floor[0]}.{floor[1]}"
    # The console script, not `python -m vermin`: the package has no __main__, so that
    # form exits nonzero for the wrong reason and this lint would fail on every run while
    # looking like it had found something.
    vermin = shutil.which("vermin")
    if vermin is None:
        raise SystemExit(
            "vermin is not installed, so the backend floor is unchecked. Install it in "
            "the job that runs this, rather than letting the check quietly pass."
        )
    files = targets()
    print(f"[floor] {len(files)} files must run on Python {target}, " f"the declared floor")
    command = [
        vermin,
        "--processes=2",
        "--no-tips",
        "--violations",
        f"-t={target}-",
    ]
    failed = False
    for batch in command_batches(command, files):
        result = subprocess.run(
            batch, capture_output = True, text = True, encoding = "utf-8",
            env = {**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
        failed |= result.returncode != 0
    if not failed:
        print(f"[floor] OK: nothing needs more than {target}")
        return 0
    print(
        f"::error title=Backend needs a newer Python than the matrix floor::"
        f"something under studio/backend or unsloth_cli requires more than Python {target}, "
        f"which is the "
        f"floor studio-backend-ci declares. The full suite runs on that supported "
        f"interpreter as well. Either guard an optional newer API appropriately, or "
        f"raise {FLOOR_KEY} in the workflow and say why."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
