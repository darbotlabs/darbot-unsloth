# Copyright 2023-present Daniel Han-Chen & the Unsloth team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Print resolver-safe commands for the maintained fork's verified stack."""

import os
from pathlib import Path
import shlex
import sys
import sysconfig

from packaging.version import Version


def select_extra(torch):
    version = Version(torch.__version__)
    if version.is_prerelease or version.is_devrelease or version.base_version != "2.14.0":
        raise RuntimeError(f"Torch {version} is unsupported; install stable Torch 2.14.0.")
    if (
        getattr(torch.version, "hip", None)
        or getattr(torch.version, "xpu", None)
        or "xpu" in (version.local or "")
        or "rocm" in (version.local or "")
    ):
        raise RuntimeError("Automatic ROCm/XPU selection is not qualified; use the platform installer.")
    cuda = torch.version.cuda
    if cuda is None:
        return "cpu", "https://download.pytorch.org/whl/cpu"
    if str(cuda) != "13.0":
        raise RuntimeError(
            f"This helper exposes the canonical CUDA 13.0 extra, not CUDA {cuda}. "
            "Verified Torch 2.14.0 CUDA 12.6 wheels are available upstream, "
            "but are outside this fork's maintained CUDA profile. "
            "CUDA families are not aliases."
        )
    return "cu130-torch2140", "https://download.pytorch.org/whl/cu130"


def install_commands(torch, python = None):
    python = str(python or sys.executable)
    if not Path(python).is_absolute():
        raise ValueError("The target Python executable must be absolute.")
    extra, index = select_extra(torch)
    root = Path(__file__).resolve().parents[1]
    if not (root / "studio" / "install_zoo.py").is_file():
        raise RuntimeError("Run this helper from the maintained Darbot checkout or its installed package.")
    companion = root / "studio" / "backend" / "vendor" / "unsloth_zoo_compat"
    if not (companion / "pyproject.toml").is_file():
        raise RuntimeError("The maintained Zoo source is missing; restore the complete Darbot package.")
    project = str(root) if (root / "pyproject.toml").is_file() else "unsloth"
    # The core itself requires the unpublished Zoo version, so its first
    # resolver transaction must already include the explicit source candidate.
    return [
        [python, "-m", "pip", "install", str(companion), f"{project}[{extra}]", "--extra-index-url", index],
    ]


def main():
    if (
        sys.implementation.name != "cpython"
        or not ((3, 14, 7) <= sys.version_info[:3] < (3, 15, 0))
        or sys.version_info[3] != "final"
        or sysconfig.get_config_var("Py_GIL_DISABLED")
    ):
        raise RuntimeError("Use final, standard (GIL-enabled) CPython >=3.14.7,<3.15.")
    override = os.environ.get("UNSLOTH_ENV_DIR")
    if override and (
        not Path(override).is_absolute()
        or Path(override).resolve() != Path(sys.prefix).resolve()
    ):
        raise RuntimeError(
            "Run this helper using the interpreter in the absolute UNSLOTH_ENV_DIR environment "
            "so its Torch/CUDA build, not another interpreter's, is inspected."
        )
    try:
        import torch
    except ImportError as error:
        raise ImportError("Install Torch 2.14.0 from the matching official cu130 or CPU index first.") from error
    commands = install_commands(torch)
    if torch.version.cuda and torch.cuda.is_available():
        capability = torch.cuda.get_device_capability()
        if capability < (8, 0):
            print(
                f"# sm_{capability[0]}{capability[1]}: CUDA eager remains available, "
                "but this device is outside Triton 3.8's support policy; qualify kernels individually."
            )
    if os.name == "nt":
        for command in commands:
            print("& " + " ".join("'" + arg.replace("'", "''") + "'" for arg in command))
            print("if ($LASTEXITCODE -ne 0) { throw 'Installation failed' }")
    else:
        print(" && ".join(shlex.join(command) for command in commands))


if __name__ == "__main__":
    main()