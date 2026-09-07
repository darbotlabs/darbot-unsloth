"""Standard-CPython policy and truthful, per-device accelerator eligibility."""

import ast
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]


def load_runtime():
    spec = importlib.util.spec_from_file_location(
        "runtime_under_test", ROOT / "unsloth" / "runtime_compat.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("version", "implementation", "free_threaded", "supported"),
    [
        ((3, 13, 15), "cpython", False, False),
        ((3, 14, 6), "cpython", False, False),
        ((3, 14, 7), "cpython", False, True),
        ((3, 14, 8), "cpython", False, True),
        ((3, 15, 0), "cpython", False, False),
        ((3, 14, 7), "cpython", True, False),
        ((3, 14, 7), "pypy", False, False),
    ],
)
@pytest.mark.parametrize("releaselevel", ["final", "candidate"])
def test_interpreter_policy(
    monkeypatch, version, implementation, free_threaded, supported, releaselevel
):
    runtime = load_runtime()
    monkeypatch.setattr(
        runtime,
        "sys",
        SimpleNamespace(
            version_info = (*version, releaselevel, 0),
            implementation = SimpleNamespace(name = implementation),
        ),
    )
    monkeypatch.setattr(runtime.sysconfig, "get_config_var", lambda name: free_threaded)
    if supported and releaselevel == "final":
        runtime.require_supported_python()
    else:
        with pytest.raises(RuntimeError, match = "standard .*CPython"):
            runtime.require_supported_python()


def test_turing_does_not_disable_cuda_and_other_devices(monkeypatch):
    runtime = load_runtime()
    cuda = SimpleNamespace(
        is_available = lambda: True,
        current_device = lambda: 0,
        get_device_capability = lambda device: [(7, 5), (8, 6)][device],
        get_device_name = lambda device: ["T1000", "RTX A6000"][device],
    )
    monkeypatch.setitem(
        sys.modules, "torch", SimpleNamespace(cuda = cuda, version = SimpleNamespace(hip = None))
    )
    turing = runtime.get_cuda_feature_support(0)
    assert turing["cuda_available"] is True
    assert turing["compute_capability"] == (7, 5)
    assert turing["triton_policy_supported"] is False
    assert turing["triton_kernels"] is None
    assert turing["torch_compile_cuda"] is None
    assert "not automatically disabled" in turing["reason"]
    assert cuda.is_available()
    ampere = runtime.get_cuda_feature_support(1)
    assert ampere["triton_policy_supported"] is True
    assert ampere["triton_kernels"] is None
    assert ampere["torch_compile_cuda"] is None


def test_common_kernel_settings_do_not_veto_devices_from_policy():
    source = ROOT / "unsloth" / "kernels" / "utils.py"
    tree = ast.parse(source.read_text(encoding = "utf-8"))
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "calculate_settings"
    )
    namespace = {
        "next_power_of_2": lambda value: 1 << (value - 1).bit_length(),
        "MAX_FUSED_SIZE": 65536,
    }
    exec(compile(ast.Module(body = [function], type_ignores = []), str(source), "exec"), namespace)
    assert namespace["calculate_settings"](17) == (32, 4)


def test_no_cuda_returns_unavailable_instead_of_claiming_a_pass(monkeypatch):
    runtime = load_runtime()
    monkeypatch.setitem(
        sys.modules,
        "torch",
        SimpleNamespace(
            cuda = SimpleNamespace(is_available = lambda: False), version = SimpleNamespace(hip = None)
        ),
    )
    report = runtime.get_cuda_feature_support()
    assert not report["cuda_available"]
    assert not report["triton_kernels"]
    assert report["compute_capability"] is None
