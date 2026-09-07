# SPDX-License-Identifier: AGPL-3.0-only
"""The generated installer command must resolve only verified Torch/CUDA extras."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace
import tomllib

from packaging.requirements import Requirement
import pytest


ROOT = Path(__file__).resolve().parents[1]


def auto_installer():
    spec = importlib.util.spec_from_file_location(
        "auto_installer_under_test", ROOT / "unsloth" / "_auto_install.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def torch_stub(
    version = "2.14.0+cu130",
    cuda = "13.0",
    hip = None,
    xpu = None,
):
    return SimpleNamespace(
        __version__ = version, version = SimpleNamespace(cuda = cuda, hip = hip, xpu = xpu)
    )


def test_cuda2140_trio_uses_real_independent_companion_versions():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding = "utf-8"))
    requirements = [
        Requirement(value)
        for value in project["project"]["optional-dependencies"]["cu130onlytorch2140"]
    ]
    for name, version in {
        "torch": "2.14.0",
        "torchvision": "0.29.0",
        "torchaudio": "2.11.0",
    }.items():
        requirement = next(requirement for requirement in requirements if requirement.name == name)
        assert str(requirement.specifier) == f"=={version}+cu130"
    xformers = [requirement for requirement in requirements if requirement.name == "xformers"]
    assert len(xformers) == 2
    assert all(
        "/whl/cu130/xformers-0.0.35-py39-none-" in requirement.url for requirement in xformers
    )


@pytest.mark.parametrize("cuda", ["11.8", "12.1", "12.4", "12.6", "12.8"])
def test_old_cuda_profiles_are_not_silent_aliases(cuda):
    with pytest.raises(RuntimeError, match = "not aliases"):
        auto_installer().select_extra(torch_stub(cuda = cuda))


@pytest.mark.parametrize("version", ["2.11.0", "2.12.1", "2.13.0", "2.14.0rc1", "2.15.0"])
def test_other_torch_releases_are_not_silent_aliases(version):
    with pytest.raises(RuntimeError, match = "unsupported"):
        auto_installer().select_extra(torch_stub(version = version))


@pytest.mark.parametrize("backend", ["hip", "xpu"])
def test_unqualified_backends_are_explicit(backend):
    with pytest.raises(RuntimeError, match = "not qualified"):
        auto_installer().select_extra(torch_stub(cuda = None, **{backend: "7.0"}))


@pytest.mark.parametrize("version", ["2.14.0+xpu", "2.14.0+rocm7.0"])
def test_accelerator_local_builds_do_not_fall_back_to_cpu(version):
    with pytest.raises(RuntimeError, match = "not qualified"):
        auto_installer().select_extra(torch_stub(version = version, cuda = None))


@pytest.mark.parametrize(
    ("torch", "extra", "index"),
    [
        (torch_stub(), "cu130-torch2140", "cu130"),
        (torch_stub(version = "2.14.0+cpu", cuda = None), "cpu", "cpu"),
    ],
)
def test_first_resolve_includes_maintained_companion_and_core_extras(torch, extra, index):
    commands = auto_installer().install_commands(torch)
    assert len(commands) == 1
    assert commands[0][1:5] == [
        "-m",
        "pip",
        "install",
        str(ROOT / "studio" / "backend" / "vendor" / "unsloth_zoo_compat"),
    ]
    assert commands[0][-3:] == [
        f"{ROOT}[{extra}]",
        "--extra-index-url",
        f"https://download.pytorch.org/whl/{index}",
    ]
    assert not any(
        "--no-deps" in argument or "unslothai/" in argument
        for command in commands
        for argument in command
    )


def test_cu126_is_a_profile_boundary_not_an_absent_wheel_claim():
    with pytest.raises(RuntimeError, match = "CUDA 12.6 wheels are available") as error:
        auto_installer().select_extra(torch_stub(version = "2.14.0+cu126", cuda = "12.6"))
    assert "platform installer" not in str(error.value)


def test_command_printer_rejects_prerelease_python(monkeypatch):
    module = auto_installer()
    monkeypatch.setattr(
        module,
        "sys",
        SimpleNamespace(
            implementation = SimpleNamespace(name = "cpython"),
            version_info = (3, 14, 7, "candidate", 1),
        ),
    )
    with pytest.raises(RuntimeError, match = "final"):
        module.main()
