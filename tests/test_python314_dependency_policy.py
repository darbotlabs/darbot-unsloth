# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2026-present the Unsloth AI Inc. team. All rights reserved.

"""Packaging contracts for the Darbot CPython 3.14 accelerator baseline."""

from pathlib import Path
import tomllib

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
import pytest


ROOT = Path(__file__).resolve().parents[1]


def project():
    with (ROOT / "pyproject.toml").open("rb") as source:
        return tomllib.load(source)


def requirements(extra):
    return [Requirement(value) for value in project()["project"]["optional-dependencies"][extra]]


@pytest.mark.parametrize(
    ("version", "accepted"),
    [
        ("3.13.15", False),
        ("3.14.0", False),
        ("3.14.6", False),
        ("3.14.7", True),
        ("3.14.8", True),
        ("3.15.0", False),
    ],
)
def test_python_support_window(version, accepted):
    assert (version in SpecifierSet(project()["project"]["requires-python"])) is accepted


@pytest.mark.parametrize(
    ("name", "version"),
    [
        ("torch", "2.14.0+cu130"),
        ("torchvision", "0.29.0+cu130"),
        ("torchaudio", "2.11.0+cu130"),
    ],
)
def test_cuda_companions_have_explicit_published_versions(name, version):
    matching = [req for req in requirements("cu130onlytorch2140") if req.name == name]
    assert len(matching) == 1
    assert str(matching[0].specifier) == f"=={version}"
    assert matching[0].marker is None


@pytest.mark.parametrize(
    ("name", "version"),
    [
        ("unsloth_zoo", "2026.9.1+darbot.1"),
        ("datasets", "5.0.1"),
        ("scikit-learn", "1.9.0"),
        ("dill", "0.4.1"),
        ("multiprocess", "0.70.19"),
        ("transformers", "5.16.1"),
        ("trl", "1.12.0"),
    ],
)
def test_hugging_face_stack_uses_coordinated_versions(name, version):
    matching = [req for req in requirements("huggingfacenotorch") if req.name == name]
    assert len(matching) == 1
    assert str(matching[0].specifier) == f"=={version}"


def test_windows_uses_windows_triton_distribution():
    environment = {
        "sys_platform": "win32",
        "platform_machine": "AMD64",
        "python_version": "3.14",
        "python_full_version": "3.14.7",
    }
    active = [
        req
        for req in requirements("triton")
        if req.marker is None or req.marker.evaluate(environment)
    ]
    assert [(req.name, str(req.specifier)) for req in active] == [
        ("triton-windows", "==3.8.0.post28")
    ]


@pytest.mark.parametrize("extra", ["studio", "huggingfacenotorch"])
def test_protobuf_uses_the_official_python314_compatible_pure_wheel(extra):
    matching = [req for req in requirements(extra) if req.name == "protobuf"]
    assert len(matching) == 1
    assert matching[0].url == (
        "https://files.pythonhosted.org/packages/16/28/"
        "d5065b212685875d3924bcdb3201cbf467cb4d58a18aa19a8dfd99ea80a9/"
        "protobuf-4.25.9-py3-none-any.whl"
        "#sha256=d49b615e7c935194ac161f0965699ac84df6112c378e05ec53da65d2e4cbb6d4"
    )


def test_cuda_selects_optional_cut_cross_entropy_without_leaking_to_other_backends():
    cuda_zoo = [req for req in requirements("huggingface") if req.name == "unsloth_zoo"]
    assert len(cuda_zoo) == 1
    assert cuda_zoo[0].extras == {"cuda"}
    assert all(
        not req.extras for req in requirements("huggingfacenotorch") if req.name == "unsloth_zoo"
    )
    for extra in ("cpu", "intelgputorch2140", "rocm72-torch2140"):
        assert not any(
            req.name == "unsloth" and "huggingface" in req.extras for req in requirements(extra)
        )


def test_cuda_attention_wheel_matches_cuda_family_and_architecture():
    active = [
        req
        for req in requirements("cu130onlytorch2140")
        if req.name == "xformers"
        and req.marker.evaluate({"sys_platform": "win32", "platform_machine": "AMD64"})
    ]
    assert len(active) == 1
    assert active[0].url == (
        "https://download.pytorch.org/whl/cu130/xformers-0.0.35-py39-none-win_amd64.whl"
    )
    assert not active[0].marker.evaluate({"sys_platform": "win32", "platform_machine": "ARM64"})


@pytest.mark.parametrize(
    ("extra", "compiler"),
    [("intelgputorch2140", "triton-xpu"), ("rocm72-torch2140", "triton-rocm")],
)
def test_accelerator_compiler_does_not_select_cuda_triton(extra, compiler):
    reqs = requirements(extra)
    assert any(req.name == compiler and str(req.specifier) == "==3.8.0" for req in reqs)
    assert not any(req.name in {"triton", "triton-windows"} for req in reqs)


def test_retired_cuda_combinations_are_not_silent_aliases():
    extras = project()["project"]["optional-dependencies"]
    assert "cu130-torch2140" in extras
    assert not any(
        name.startswith(("cu118", "cu121", "cu124", "cu126", "cu128")) for name in extras
    )


def test_zoo_companion_is_data_not_a_nested_importable_package():
    setuptools = project()["tool"]["setuptools"]
    assert "studio.backend.vendor.unsloth_zoo_compat*" in setuptools["packages"]["find"]["exclude"]
    assert "backend/vendor/**/*" in setuptools["package-data"]["studio"]


def test_zoo_companion_keeps_upstream_bytes_under_git():
    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "studio/backend/vendor/unsloth_zoo_compat/** -text -whitespace" in attributes
