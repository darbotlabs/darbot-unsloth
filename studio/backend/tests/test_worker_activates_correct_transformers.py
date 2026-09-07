# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2026-present the Unsloth AI Inc. team. All rights reserved. See /studio/LICENSE.AGPL-3.0

"""Worker preflight must not preload Transformers before selecting its installation.

Real tier detection and activation run in a fresh process with minimal package
stubs. The supported 5.16.1 base needs no fixed shadow; an older base must use the
5.16.1 fallback. GPU spoofing exposes the historical eager Zoo import (#6951)
even on CPU CI. No models, weights, or real sidecar installation are required.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
import pytest

_BACKEND_DIR = Path(__file__).resolve().parent.parent  # studio/backend
# Canonical CUDA spoof at the repo root (studio/backend -> studio -> repo root). Loaded by the
# subprocess when present (matches the consolidated CI); absent in a standalone studio checkout, where
# the subprocess falls back to a minimal inline spoof.
_SPOOF_PATH = _BACKEND_DIR.parent.parent / "tests" / "_zoo_aggressive_cuda_spoof.py"

# Runs in a fresh interpreter with cwd == studio/backend so ``utils.*`` resolves like the worker.
# STUB_HOME holds an old or supported base plus the supported fixed-tier shadow.
_SNIPPET = r"""
import os, sys
sys.path.insert(0, os.getcwd())

# CUDA spoof so unsloth_zoo takes its full, transformers-importing init path on a GPU-less runner.
# Without it unsloth_zoo degrades and never preloads transformers, which would MASK the stale-import
# regression under test (verified). Prefer the repo's canonical spoof (single source of truth, and the
# one the consolidated CI already relies on); fall back to a minimal inline spoof so this also works in
# a standalone studio checkout. If torch is absent the fixed tree still passes below; the bug just
# would not be exposable in that shard.
try:
    import torch  # noqa: F401
    _sp = os.environ.get("SPOOF_PATH")
    if _sp and os.path.exists(_sp):
        import importlib.util
        _spec = importlib.util.spec_from_file_location("_zoo_aggressive_cuda_spoof", _sp)
        _mod = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        _mod.apply()
    else:
        torch.cuda.is_available = lambda: True
        torch.cuda.device_count = lambda: 1
        torch.cuda.current_device = lambda: 0
        torch.cuda.get_device_capability = lambda *a, **k: (8, 0)
        torch.cuda.get_device_name = lambda *a, **k: "NVIDIA A100-SPOOFED"
        torch.cuda.is_bf16_supported = lambda *a, **k: True
        class _Props:
            name = "NVIDIA A100-SPOOFED"
            major = 8
            minor = 0
            total_memory = 80 * 1024**3
            multi_processor_count = 108
        torch.cuda.get_device_properties = lambda *a, **k: _Props()
        torch.cuda.mem_get_info = lambda *a, **k: (0, 80 * 1024**3)
except Exception:
    pass
os.environ["UNSLOTH_IS_PRESENT"] = "1"

# Stub 5.x sidecar: activation only edits sys.path, so a package that merely exports __version__ is
# enough to prove the resident transformers switched to it.
home = os.environ["STUB_HOME"]
pkg = os.path.join(home, ".venv_t5_530", "transformers")
os.makedirs(pkg, exist_ok = True)
with open(os.path.join(pkg, "__init__.py"), "w") as f:
    f.write('__version__ = "5.16.1"\n')
os.environ["UNSLOTH_STUDIO_HOME"] = home

# Faithful worker preflight (worker.py: from utils.hf_xet_fallback import child_should_disable_xet).
# This is the exact stale-import trigger: on the buggy tree it pulls unsloth_zoo -> transformers 4.57.x
# into sys.modules BEFORE activation.
from utils.hf_xet_fallback import child_should_disable_xet
child_should_disable_xet({})
_tf = sys.modules.get("transformers")
preload = _tf.__version__ if _tf is not None else None

base = os.path.join(home, "base")
base_version = os.environ["BASE_TRANSFORMERS_VERSION"]
base_pkg = os.path.join(base, "transformers")
os.makedirs(base_pkg, exist_ok = True)
with open(os.path.join(base_pkg, "__init__.py"), "w") as f:
    f.write(f'__version__ = "{base_version}"\n')
dist_info = os.path.join(base, f"transformers-{base_version}.dist-info")
os.makedirs(dist_info, exist_ok = True)
with open(os.path.join(dist_info, "METADATA"), "w") as f:
    f.write(f"Name: transformers\nVersion: {base_version}\n")
sys.path.insert(0, base)

# Real tier detection + real activation, with the 530 sidecar pointed at the stub above.
import utils.transformers_version as tv
tv.sysconfig.get_path = lambda name: base
tv._VENV_T5_530_DIR = os.path.join(home, ".venv_t5_530")
tv._ensure_venv_t5_530_exists = lambda: True
tier = tv.get_transformers_tier("Qwen/Qwen3.5-9B", None)
tv.activate_transformers_for_subprocess("Qwen/Qwen3.5-9B", None)

import transformers
source = (
    "sidecar" if transformers.__file__.startswith(pkg)
    else "base" if transformers.__file__.startswith(base_pkg)
    else "unexpected"
)
print(f"RESULT tier={tier} preload={preload} active={transformers.__version__} source={source}")
"""


def _parse(stdout: str) -> dict[str, str]:
    for line in stdout.splitlines():
        if line.startswith("RESULT "):
            return dict(kv.split("=", 1) for kv in line.split()[1:])
    return {}


@pytest.mark.parametrize(
    ("base_version", "expected_source"), [("4.57.6", "sidecar"), ("5.16.1", "base")]
)
def test_worker_activates_correct_transformers_version(tmp_path, base_version, expected_source):
    result = subprocess.run(
        [sys.executable, "-c", _SNIPPET],
        cwd = str(_BACKEND_DIR),
        env = {
            **__import__("os").environ,
            "STUB_HOME": str(tmp_path),
            "BASE_TRANSFORMERS_VERSION": base_version,
            **({"SPOOF_PATH": str(_SPOOF_PATH)} if _SPOOF_PATH.exists() else {}),
        },
        capture_output = True,
        text = True,
    )
    assert result.returncode == 0, (
        "Worker preflight + activation harness crashed.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    parsed = _parse(result.stdout)
    assert parsed, f"No RESULT line.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"

    # Correct tier chosen for a transformers-5.x model (pure, deterministic; no network/GPU).
    assert parsed["tier"] == "530", (
        f"Wrong transformers tier for Qwen3.5 (expected 530, got {parsed['tier']}). "
        "Tier detection regressed."
    )

    assert parsed["preload"] == "None", "Worker preflight imported Transformers before activation"
    assert parsed["active"] == "5.16.1"
    assert parsed["source"] == expected_source
