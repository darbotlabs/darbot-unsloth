"""Unsupported compressed export fails before installation, merging, or downgrade."""

import importlib.util
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
BASELINE = {"torch": "2.13.0+cu130", "transformers": "5.14.1", "numpy": "2.4.6"}


def policy():
    spec = importlib.util.spec_from_file_location(
        "quantization_policy", ROOT / "unsloth" / "quantization_compat.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_published_ceiling_ignores_torch_backend_local_suffix():
    assert policy().llm_compressor_compatibility_error(BASELINE) is None


@pytest.mark.parametrize(
    ("package", "version"),
    [("torch", "2.14.0+cu130"), ("transformers", "5.16.1"), ("numpy", "2.5.3")],
)
def test_latest_fork_stack_is_explicitly_unsupported(package, version):
    error = policy().llm_compressor_compatibility_error({**BASELINE, package: version})
    assert f"{package} {version}" in error
    assert "unsupported" in error
    assert "Do not downgrade" in error
    assert "merged_16bit or GGUF" in error


def test_missing_or_invalid_versions_do_not_authorize_an_install():
    assert "cannot be verified" in policy().llm_compressor_compatibility_error({})
    assert "cannot be verified" in policy().llm_compressor_compatibility_error(
        {**BASELINE, "torch": "unknown"}
    )


def test_shadow_environment_cannot_bypass_torch_incompatibility(monkeypatch):
    module = policy()
    versions = {**BASELINE, "torch": "2.14.0+cu130"}
    monkeypatch.setattr(module, "version", versions.__getitem__)
    monkeypatch.setenv("UNSLOTH_COMPRESSED_QUANTIZE_PYTHONPATH", "an-older-transformers-shadow")
    with pytest.raises(RuntimeError, match = "torch 2.14.0"):
        module.require_llm_compressor_compatibility()


def test_converter_refuses_current_stack_before_creating_output(tmp_path):
    module = policy()
    if module.llm_compressor_compatibility_error() is None:
        pytest.skip("This environment is within the published quantizer ceiling")
    output = tmp_path / "must-not-exist"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "unsloth" / "_compressed_quantize.py"),
            "--model",
            str(tmp_path / "not-a-checkpoint"),
            "--scheme",
            "FP8",
            "--out",
            str(output),
        ],
        text = True,
        encoding = "utf-8",
        capture_output = True,
        timeout = 30,
    )
    assert result.returncode != 0
    assert "llmcompressor 0.13.0" in result.stderr
    assert "unsupported" in result.stderr
    assert not output.exists()
