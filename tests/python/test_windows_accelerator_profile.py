"""Fresh installs and repairs share the maintained Torch 2.14 profiles."""

import importlib.util
import os
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]


def stack():
    spec = importlib.util.spec_from_file_location(
        "maintained_profile_stack", ROOT / "studio" / "install_python_stack.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("family", ["cpu", "xpu", "cu130", "rocm7.2"])
def test_explicit_maintained_profile_preserves_mirror_without_gpu_probe(monkeypatch, family):
    module = stack()
    monkeypatch.delenv("UNSLOTH_TORCH_INDEX_URL", raising = False)
    monkeypatch.setenv("UNSLOTH_TORCH_INDEX_FAMILY", family)
    monkeypatch.setattr(module, "_PYTORCH_WHL_BASE", "https://mirror.example/whl")
    monkeypatch.setattr(module, "_nvidia_smi_path", lambda: pytest.fail("explicit profile must not probe GPU"))
    assert module._detect_cuda_torch_index_url() == f"https://mirror.example/whl/{family}"


@pytest.mark.parametrize("family", ["cu118", "cu124", "cu126", "cu128", "rocm7.1", "gfx1151"])
def test_explicit_legacy_profile_rejected_without_alias_or_secret_leak(monkeypatch, family):
    module = stack()
    monkeypatch.setenv(
        "UNSLOTH_TORCH_INDEX_URL",
        f"https://user:secret@mirror.example/whl/{family}/?token=private",
    )
    with pytest.raises(ValueError, match = "never silently aliased") as error:
        module._detect_cuda_torch_index_url()
    assert family in str(error.value)
    assert "secret" not in str(error.value)
    assert "private" not in str(error.value)


@pytest.mark.parametrize("driver_version", ["13.0", "13.1", "12.9", "11.8", None])
def test_auto_cuda_never_falls_back_to_legacy_family(monkeypatch, driver_version):
    module = stack()
    monkeypatch.delenv("UNSLOTH_TORCH_INDEX_URL", raising = False)
    monkeypatch.delenv("UNSLOTH_TORCH_INDEX_FAMILY", raising = False)
    monkeypatch.setattr(module, "_PYTORCH_WHL_BASE", "https://mirror.example/whl")
    monkeypatch.setattr(module, "_nvidia_smi_path", lambda: "nvidia-smi")
    output = f"CUDA Version: {driver_version}" if driver_version else "unavailable"
    monkeypatch.setattr(
        module.subprocess, "run",
        lambda *a, **k: SimpleNamespace(returncode = 0, stdout = output),
    )
    monkeypatch.setattr(
        module, "_cap_cuda_family_for_pre_turing",
        lambda *a: pytest.fail("architecture alone must not change the CUDA profile"),
    )
    if driver_version in ("12.9", "11.8"):
        with pytest.raises(RuntimeError, match = "Upgrade the driver"):
            module._detect_cuda_torch_index_url()
    else:
        assert module._detect_cuda_torch_index_url() == "https://mirror.example/whl/cu130"


def test_invalid_explicit_profile_fails_before_install_mutation(monkeypatch):
    module = stack()
    monkeypatch.setattr(module, "NO_TORCH", False)
    monkeypatch.delenv("UNSLOTH_TORCH_INDEX_URL", raising = False)
    monkeypatch.setenv("UNSLOTH_TORCH_INDEX_FAMILY", "cu126")
    monkeypatch.setattr(module.install_manifest, "supported_interpreter", lambda: True)
    monkeypatch.setattr(
        module.install_manifest, "remove_manifest",
        lambda: pytest.fail("invalid profile must fail before manifest mutation"),
    )
    monkeypatch.setattr(module, "run", lambda *a, **k: pytest.fail("must not install packages"))
    assert module.install_python_stack() == 1


@pytest.mark.parametrize("filename", ["install.ps1", "studio/setup.ps1"])
def test_windows_profile_helpers_match_shared_policy(filename):
    from unsloth_pwsh_runner import run_pwsh

    if shutil.which("pwsh") is None:
        pytest.skip("PowerShell is unavailable")
    script = r"""
$ErrorActionPreference = 'Stop'
$tokens = $null; $errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($env:PROFILE_SOURCE, [ref]$tokens, [ref]$errors)
if ($errors) { throw ($errors | Out-String) }
$names = @('Get-TorchIndexUrl', 'Get-PytorchCudaTag', 'Get-PinnedTorchIndexUrl', 'Trim-IndexPathSlashes', 'Assert-MaintainedTorchIndex')
$functions = $ast.FindAll({
    param($node)
    $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -in $names
}, $true)
foreach ($fn in $functions) { Invoke-Expression $fn.Extent.Text }
function substep {}
function Invoke-NvidiaSmiBounded { return "CUDA Version: $script:DriverVersion" }
$NvidiaSmiExe = 'fake'
$script:NvidiaSmiExe = 'fake'
$script:DriverVersion = '13.0'
$env:UNSLOTH_TORCH_INDEX_URL = $null
$env:UNSLOTH_PYTORCH_MIRROR = 'https://mirror.example/whl'
function Get-SelectedIndex {
    if (Get-Command Get-TorchIndexUrl -ErrorAction SilentlyContinue) { return Get-TorchIndexUrl }
    $pin = Get-PinnedTorchIndexUrl
    if ($pin) { return $pin }
    return "https://mirror.example/whl/$(Get-PytorchCudaTag)"
}
foreach ($family in @('cpu', 'xpu', 'cu130', 'rocm7.2')) {
    $env:UNSLOTH_TORCH_INDEX_FAMILY = $family
    if ((Get-SelectedIndex) -ne "https://mirror.example/whl/$family") { throw "Wrong family: $family" }
}
foreach ($family in @('cu118', 'cu124', 'cu126', 'cu128', 'rocm7.1', 'gfx1151')) {
    $env:UNSLOTH_TORCH_INDEX_FAMILY = $family
    try { $unused = Get-SelectedIndex; throw "Accepted legacy family: $family" }
    catch { if ("$_" -notlike '*Unsupported Torch 2.14 index family*') { throw } }
}
$env:UNSLOTH_TORCH_INDEX_FAMILY = $null
if ((Get-SelectedIndex) -ne 'https://mirror.example/whl/cu130') { throw 'CUDA 13 profile not selected' }
$script:DriverVersion = '12.9'
try { $unused = Get-SelectedIndex; throw 'Accepted incompatible driver' }
catch { if ("$_" -notlike '*Upgrade the driver*') { throw } }
Write-Output 'PASS'
"""
    result = run_pwsh(
        ["pwsh", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output = True,
        text = True,
        env = dict(os.environ, PROFILE_SOURCE = str(ROOT / filename)),
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "PASS"


def test_windows_install_and_repair_specs_are_exact():
    for filename in ("install.ps1", "studio/setup.ps1", "studio/install_python_stack.py"):
        source = (ROOT / filename).read_text(encoding = "utf-8")
        assert '"torch==2.14.0"' in source
        assert '"torchvision==0.29.0"' in source
        assert '"torchaudio==2.11.0"' in source
        assert "torch>=2.14.0" not in source
        assert "torchvision>=0.29.0" not in source
