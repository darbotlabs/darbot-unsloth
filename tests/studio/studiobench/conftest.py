# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2026-present the Unsloth AI Inc. team. All rights reserved.

import subprocess
import sys

import pytest


@pytest.fixture
def studiobench_dead_pid():
    # Retain the Windows process handle until teardown so its exited PID cannot be reused.
    with subprocess.Popen([sys.executable, "-c", "pass"]) as child:
        assert child.wait(timeout = 30) == 0
        yield child.pid
