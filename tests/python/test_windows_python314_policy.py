"""Standard-GIL Python policy, without importing the training runtime."""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "studio" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "version,implementation,free_threaded,expected",
    [
        ("3.14.7", "cpython", False, True),
        ("3.14.8", "cpython", False, True),
        ("3.14.6", "cpython", False, False),
        ("3.13.15", "cpython", False, False),
        ("3.12.12", "cpython", False, False),
        ("3.15.0", "cpython", False, False),
        ("3.14.7", "cpython", True, False),
        ("3.14.7", "pypy", False, False),
        ("3.14.7rc1", "cpython", False, False),
        ("3.14", "cpython", False, False),
    ],
)
def test_interpreter_policy(version, implementation, free_threaded, expected):
    policy = load("python_policy")
    assert policy.supported_interpreter({
        "version": version,
        "implementation": implementation,
        "free_threaded": free_threaded,
    }) is expected


def test_manifest_rejects_interpreter_change(tmp_path, monkeypatch):
    manifest = load("install_manifest")
    monkeypatch.setattr(manifest, "_installed_version", lambda *a, **k: "2026.9.2")
    monkeypatch.setattr(manifest, "installed_version_probe", lambda *a: ("2026.9.2", False))
    monkeypatch.setattr(manifest, "missing_requirements", lambda *a, **k: [])
    monkeypatch.setattr(manifest, "requirement_digests", lambda *a: {})
    manifest.write_manifest(root = tmp_path)
    state = manifest.verify_install(root = tmp_path)
    assert state["ok"]
    old = manifest.interpreter_identity()
    monkeypatch.setattr(manifest, "interpreter_identity", lambda: dict(old, soabi = "cp314t"))
    assert manifest.verify_install(root = tmp_path)["reason"] == "studio_install_interpreter_changed"


def test_manifest_rejects_legacy_python_even_for_foreign_venv(tmp_path, monkeypatch):
    import json

    manifest = load("install_manifest")
    monkeypatch.setattr(manifest, "missing_requirements", lambda *a, **k: [])
    payload = {"schema": manifest.MANIFEST_SCHEMA, "python": "3.13.15"}
    (tmp_path / manifest.MANIFEST_NAME).write_text(json.dumps(payload), encoding = "utf-8")
    assert manifest.verify_install(root = tmp_path, installed = {})["reason"] == "studio_install_python_unsupported"


def test_manifest_requirement_parser_preserves_url_hash_and_marker():
    manifest = load("install_manifest")
    requirement = (
        "descript-audiotools @ https://github.com/descriptinc/audiotools/archive/commit.zip"
        "#sha256=abcdef ; sys_platform == 'win32'  # optional audio"
    )
    assert manifest._parse_requirement_line(requirement) == (
        "descript-audiotools", 'sys_platform == "win32"', "",
    )


def test_windows_requirement_filter_preserves_source_hash(tmp_path):
    stack = load("install_python_stack")
    requirement = (
        "descript-audiotools @ https://github.com/descriptinc/audiotools/archive/commit.zip"
        "#sha256=abcdef\n"
    )
    source = tmp_path / "requirements.txt"
    source.write_text(requirement + "triton_kernels @ https://example.invalid/kernel.zip\n", encoding = "utf-8")
    filtered = stack._filter_requirements(source, {"triton_kernels"})
    try:
        assert filtered.read_text(encoding = "utf-8") == requirement
    finally:
        filtered.unlink()


@pytest.mark.parametrize(
    "version,tag,repair",
    [
        ("4.25.9", "cp310-abi3-win_amd64", True),
        ("4.25.9", "cp37-abi3-manylinux2014_x86_64", True),
        ("4.25.9", "py3-none-any", False),
        ("7.36.1", "cp310-abi3-win_amd64", False),
    ],
)
def test_protobuf_same_version_artifact_repair(monkeypatch, tmp_path, version, tag, repair):
    import importlib.metadata
    from types import SimpleNamespace

    stack = load("install_python_stack")
    url = "https://example.invalid/protobuf-4.25.9-py3-none-any.whl#sha256=" + "a" * 64
    constraints = tmp_path / "constraints.txt"
    constraints.write_text(f"protobuf @ {url}\n", encoding = "utf-8")
    monkeypatch.setattr(stack, "CONSTRAINTS", constraints)
    state = {"tag": tag}
    monkeypatch.setattr(
        importlib.metadata, "distribution",
        lambda name: SimpleNamespace(version = version, read_text = lambda path: f"Tag: {state['tag']}\n"),
    )
    calls = []

    def install(label, *args, **kwargs):
        calls.append(args)
        state["tag"] = "py3-none-any"

    monkeypatch.setattr(stack, "pip_install", install)
    stack._repair_incompatible_protobuf_wheel()
    assert calls == ([("--force-reinstall", url)] if repair else [])


def test_protobuf_repair_requires_verified_artifact_and_success(monkeypatch, tmp_path):
    import importlib.metadata
    from types import SimpleNamespace

    stack = load("install_python_stack")
    constraints = tmp_path / "constraints.txt"
    constraints.write_text("protobuf==4.25.9\n", encoding = "utf-8")
    monkeypatch.setattr(stack, "CONSTRAINTS", constraints)
    monkeypatch.setattr(
        importlib.metadata, "distribution",
        lambda name: SimpleNamespace(version = "4.25.9", read_text = lambda path: "Tag: cp310-abi3-win_amd64\n"),
    )
    calls = []
    monkeypatch.setattr(stack, "pip_install", lambda label, *args: calls.append(args))
    with pytest.raises(RuntimeError, match = "checksum-pinned"):
        stack._repair_incompatible_protobuf_wheel()
    assert calls == []
    url = "https://example.invalid/protobuf-4.25.9-py3-none-any.whl#sha256=" + "b" * 64
    constraints.write_text(f"protobuf @ {url}\n", encoding = "utf-8")
    with pytest.raises(RuntimeError, match = "did not install"):
        stack._repair_incompatible_protobuf_wheel()
    assert calls == [("--force-reinstall", url)]


def test_windows_entrypoints_do_not_install_older_python_or_triton():
    for filename in ("install.ps1", "studio/setup.ps1"):
        source = (ROOT / filename).read_text(encoding = "utf-8")
        assert "Py_GIL_DISABLED" in source
        assert "(3,14,7)" in source
        assert 'UNSLOTH_ENV_DIR' in source
        assert '@("3.13", "3.12", "3.11")' not in source
        assert "Python.Python.3.12" not in source
        assert "triton-windows<3.7" not in source
        assert "transformers==5.3.0" not in source
        assert "transformers==5.5.0" not in source
        assert "transformers==5.10.2" not in source


def test_root_rebuild_keeps_custom_env_rollback_on_same_volume():
    source = (ROOT / "install.ps1").read_text(encoding = "utf-8")
    assert '$rollbackParent = Split-Path -Parent $ExistingDir' in source
    assert "retaining previous environment and any user files" in source
    assert "not an owned Studio venv" in source


@pytest.mark.parametrize("checkout_kind", ["complete", "incomplete", "missing"])
def test_windows_ci_checkout_is_validated_before_package_resolution(tmp_path, checkout_kind):
    import json
    import os
    import shutil

    from unsloth_pwsh_runner import run_pwsh

    if shutil.which("pwsh") is None:
        pytest.skip("PowerShell is unavailable")
    checkout = ROOT if checkout_kind == "complete" else tmp_path / "checkout"
    if checkout_kind == "incomplete":
        checkout.mkdir()
        (checkout / "pyproject.toml").write_text("", encoding = "utf-8")
    source = (ROOT / "install.ps1").read_text(encoding = "utf-8")
    start = source.index("    # A CI checkout must supply the fork")
    end = source.index("    # Validate --package", start)
    assert end < source.index("$_unslothReleaseInstallSpec =")
    script = """
$ErrorActionPreference = 'Stop'
$StudioLocalInstall = $false
$RepoRoot = ''
function Exit-InstallFailure { param($Message) throw $Message }
function Write-StudioLine {}
""" + source[start:end] + """
ConvertTo-Json @{ local = $StudioLocalInstall; root = $RepoRoot }
"""
    result = run_pwsh(
        ["pwsh", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output = True,
        text = True,
        env = dict(os.environ, UNSLOTH_CI_SOURCE_OVERLAY = str(checkout)),
    )
    if checkout_kind == "complete":
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout) == {"local": True, "root": str(ROOT)}
    else:
        assert result.returncode != 0
        assert "UNSLOTH_CI_SOURCE_OVERLAY" in result.stderr


def test_windows_uv_release_and_published_checksums_match():
    import re

    expected = {
        "F65744F94072152B1F86BA2AACE4D01F1124D9A8ECB235805039E3718C36CAC2",
        "EE985C51C0C9C1F82267A5D80F959B34A7FF888C109182BD3B2B35C4661BBCDE",
        "CBF375FE6BF8A4E9FFB2F09C1FF4F8ED29BA96594A604749F84FA4E08C9A4586",
    }
    for filename in ("install.ps1", "studio/setup.ps1"):
        source = (ROOT / filename).read_text(encoding = "utf-8")
        assert '$UvPinnedVersion = "0.12.10"' in source
        block = re.search(r"\$UvPinnedAssets = @\{(.*?)\n\s*\}", source, re.DOTALL).group(1)
        assert set(re.findall(r'Sha256 = "([A-F0-9]{64})"', block)) == expected


def test_shared_stack_does_not_cap_requested_torch():
    source = (ROOT / "studio" / "install_python_stack.py").read_text(encoding = "utf-8")
    assert '"torch==2.14.0"' in source
    assert '"torchvision==0.29.0"' in source
    assert '"torchaudio==2.11.0"' in source
    assert '"torch>=2.4,<2.12.0"' not in source
    assert '"torch>=2.11.0,<2.12.0"' not in source
    assert '"patch_metadata.py"' not in source


def test_accelerator_specs_and_latest_python_only_torchao():
    stack = load("install_python_stack")
    expected = ("torch==2.14.0", "torchvision==0.29.0", "torchaudio==2.11.0")
    for name in ("_CUDA_TORCH_PKG_SPEC", "_CPU_TORCH_PKG_SPEC", "_XPU_TORCH_PKG_SPEC", "_TORCH_FLAVOR_REPAIR_PKG_SPEC"):
        assert getattr(stack, name) == expected
    assert all(spec == expected for spec in stack._ROCM_TORCH_PKG_SPECS.values())
    assert stack._select_torchao_spec("2.14.0+cu130") == "torchao==0.18.0"
    assert stack._select_torchao_spec("2.14.0+xpu") == "torchao==0.18.0"


def test_unsupported_stack_fails_before_mutation(monkeypatch):
    stack = load("install_python_stack")
    monkeypatch.setattr(stack.install_manifest, "supported_interpreter", lambda: False)
    monkeypatch.setattr(stack.install_manifest, "remove_manifest", lambda: pytest.fail("must not mutate an incompatible venv"))
    monkeypatch.setattr(stack, "run", lambda *a, **k: pytest.fail("must not install packages"))
    assert stack.install_python_stack() == 1


def test_local_companion_comes_from_maintained_source(monkeypatch, tmp_path):
    stack = load("install_python_stack")
    monkeypatch.setenv("STUDIO_LOCAL_REPO", str(tmp_path))
    monkeypatch.delenv("UNSLOTH_ZOO_REF", raising = False)
    expected = tmp_path / "studio" / "backend" / "vendor" / "unsloth_zoo_compat"
    assert Path(stack._unsloth_zoo_git_spec()) == expected
    monkeypatch.setenv("UNSLOTH_ZOO_REF", "main")
    with pytest.raises(RuntimeError, match = "maintained"):
        stack._unsloth_zoo_git_spec()


@pytest.mark.parametrize("has_constraints", [True, False])
@pytest.mark.parametrize("core_refreshed", [True, False])
def test_companion_bootstrap_honors_shared_constraints(tmp_path, has_constraints, core_refreshed):
    import ast
    from types import SimpleNamespace

    tree = ast.parse((ROOT / "studio" / "install_python_stack.py").read_text(encoding = "utf-8"))
    install = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "install_python_stack")
    bootstrap = next(
        node for node in install.body
        if isinstance(node, ast.If) and any(
            isinstance(child, ast.Constant) and child.value == "Bootstrapping maintained Zoo companion"
            for child in ast.walk(node)
        )
    )
    constraints = tmp_path / "constraints.txt"
    if has_constraints:
        constraints.write_text("rich==14.3.4\nclick==8.4.2\n", encoding = "utf-8")
    helper = tmp_path / "install_zoo.py"
    interpreter = str(tmp_path / "target-python.exe")
    calls = []
    namespace = {
        "NO_TORCH": False,
        "core_refreshed": core_refreshed,
        "local_repo": "",
        "Path": Path,
        "SCRIPT_DIR": tmp_path,
        "_progress": lambda *args: None,
        "zoo_helper": helper,
        "sys": SimpleNamespace(executable = interpreter),
        "CONSTRAINTS": constraints,
        "run": lambda label, command: calls.append(command),
    }
    exec(compile(ast.Module(body = [bootstrap], type_ignores = []), "<bootstrap>", "exec"), namespace)
    expected = [interpreter, str(helper), "--python", interpreter, "--reinstall-source"]
    if has_constraints:
        expected += ["--constraints", str(constraints)]
    assert calls == ([] if core_refreshed else [expected])
    windows = (ROOT / "install.ps1").read_text(encoding = "utf-8")
    assert '$ZooBootstrapArgs += @("--constraints", $ZooConstraints)' in windows
    assert "& $VenvPython @ZooBootstrapArgs" in windows
    assert '"--installer", "uv", "--reinstall-source"' in windows


def test_turing_warning_does_not_disable_cuda_or_abort():
    import ast

    tree = ast.parse((ROOT / "studio" / "install_python_stack.py").read_text(encoding = "utf-8"))
    install = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "install_python_stack")
    advisory = next(
        node for node in install.body
        if isinstance(node, ast.If) and any(
            isinstance(child, ast.Constant) and isinstance(child.value, str)
            and "CUDA remains" in child.value for child in ast.walk(node)
        )
    )
    assert not any(isinstance(node, (ast.Raise, ast.Return)) for node in ast.walk(advisory))
    messages = []
    namespace = {
        "NO_TORCH": False,
        "_nvidia_smi_path": lambda: "nvidia-smi",
        "_nvidia_compute_sms": lambda _: [75, 75],
        "_safe_print": messages.append,
    }
    exec(compile(ast.Module(body = [advisory], type_ignores = []), "<advisory>", "exec"), namespace)
    assert len(messages) == 1
    assert "CUDA remains enabled" in messages[0]
    assert "qualify compiled training features individually" in messages[0]
