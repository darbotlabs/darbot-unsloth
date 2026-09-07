"""Immutable repair snapshots and moving same-version Core/Zoo source updates."""

import base64
import csv
import hashlib
import importlib.metadata
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace
import venv
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[2]
A = "a" * 40
B = "b" * 40
CORE_VERSION = "2026.9.2"
ZOO_VERSION = "2026.9.1+darbot.1"


def source(commit):
    return f"unsloth @ https://codeload.github.com/darbotlabs/darbot-unsloth/zip/{commit}"


@pytest.fixture
def stack(monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location("tracking_stack", ROOT / "studio" / "install_python_stack.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    managed = tmp_path / "managed"
    managed.mkdir()
    monkeypatch.setattr(module.install_manifest, "venv_root", lambda: managed)
    monkeypatch.setattr(module, "SCRIPT_DIR", managed / "Lib" / "site-packages" / "studio")
    monkeypatch.setattr(module.install_manifest, "_installed_metadata_records", lambda name: [])
    for name in ("UNSLOTH_CORE_TRACKING_REF", "STUDIO_LOCAL_REPO", "UNSLOTH_CI_SOURCE_OVERLAY", "UV_OFFLINE"):
        monkeypatch.delenv(name, raising = False)
    return module


def test_repair_retains_snapshot_and_separate_main_intent(stack, monkeypatch):
    stack._remember_core_source(source(A), tracking = "main")
    stack._remember_core_source(source(A))
    assert stack._remembered_core_source() == source(A)
    assert stack._core_tracking_intent(source(A)) == "main"
    monkeypatch.setenv("UNSLOTH_CORE_TRACKING_REF", "pinned")
    assert stack._core_tracking_intent(source(A)) is None
    stack._remember_core_source(source(A), tracking = None)
    monkeypatch.delenv("UNSLOTH_CORE_TRACKING_REF")
    assert stack._core_tracking_intent(source(A)) is None


def test_explicit_checkout_stays_fixed_even_with_inherited_main(stack, monkeypatch, tmp_path):
    checkout = tmp_path / "wip"
    for name in stack._CORE_CHECKOUT_FILES:
        path = checkout / name
        path.parent.mkdir(parents = True, exist_ok = True)
        path.write_text("work in progress", encoding = "utf-8")
    for name in ("pyproject.toml", "studio/backend/vendor/unsloth_zoo_compat/pyproject.toml"):
        (checkout / name).write_bytes((ROOT / name).read_bytes())
    monkeypatch.setenv("UNSLOTH_CORE_TRACKING_REF", "main")
    assert stack._core_tracking_intent(str(checkout)) is None
    stack._remember_core_source(str(checkout), tracking = "main")
    assert "tracking" not in stack._core_source_payload()


def test_missing_editable_checkout_never_falls_back_to_the_old_archive(
    stack, monkeypatch, tmp_path,
):
    stack._remember_core_source(source(A), tracking = "main")
    provenance = {"url": (tmp_path / "missing-wip").as_uri(), "dir_info": {"editable": True}}
    monkeypatch.setattr(
        importlib.metadata, "distribution",
        lambda name: SimpleNamespace(read_text = lambda path: json.dumps(provenance)),
    )
    assert stack._core_is_editable() is True
    with pytest.raises(RuntimeError, match = "working checkout"):
        stack._core_repair_source("unsloth")


def test_an_editable_source_keeps_the_local_overlay_path(stack):
    import inspect
    code = inspect.getsource(stack.install_python_stack)
    selection = code.index('record["kind"] == "checkout" and not local_repo and (')
    assert selection < code.index("_repair_duplicate_core_metadata(")
    assert 'local_repo = record["path"]' in code[selection:code.index("_repair_duplicate_core_metadata(")]
    assert '_core_is_editable() or SCRIPT_DIR.parent.resolve() == Path(record["path"])' in code


def test_repair_of_a_new_explicit_pin_does_not_inherit_old_tracking(stack):
    stack._remember_core_source(source(A), tracking = "main")
    stack._remember_core_source(source(B))
    assert stack._core_tracking_intent(source(B)) is None


@pytest.mark.parametrize("uv_succeeds", [False, True])
def test_uv_refresh_is_package_scoped_and_pip_fallback_does_not_force_the_graph(
    stack, monkeypatch, tmp_path, uv_succeeds,
):
    monkeypatch.setattr(stack, "USE_UV", True)
    monkeypatch.setattr(stack, "NO_TORCH", False)
    calls = []
    def install(label, *args, **kwargs):
        calls.append((args, kwargs))
        return uv_succeeds if len(calls) == 1 else True

    monkeypatch.setattr(stack, "pip_install_try", install)
    wheels = {"unsloth-zoo": tmp_path / "zoo.whl", "unsloth": tmp_path / "core.whl"}
    assert stack._install_core_update_wheels(wheels, tmp_path / "constraints.txt")
    assert calls[0][0][:4] == (
        "--reinstall-package", "unsloth-zoo", "--reinstall-package", "unsloth",
    )
    assert "--force-reinstall" not in calls[0][0]
    assert len(calls) == (1 if uv_succeeds else 4)
    for args, kwargs in calls[1:]:
        assert kwargs["force_pip"] is True
        if "--force-reinstall" in args:
            assert "--no-deps" in args and "--no-index" in args
        else:
            assert "--no-deps" not in args


@pytest.mark.parametrize("revision,expected", [("main", "main"), (None, "main"), (A, None)])
def test_pep610_distinguishes_branch_intent_from_an_explicit_commit(stack, monkeypatch, revision, expected):
    provenance = {
        "url": "https://github.com/darbotlabs/darbot-unsloth.git",
        "vcs_info": {"commit_id": A, "requested_revision": revision},
    }
    monkeypatch.setattr(
        importlib.metadata, "distribution",
        lambda name: SimpleNamespace(read_text = lambda path: json.dumps(provenance)),
    )
    assert stack._core_tracking_intent(source(A)) == expected


def test_legacy_unmarked_snapshot_can_recover_original_vcs_tracking(stack, monkeypatch):
    stack._remember_core_source(source(A))
    provenance = {
        "url": "https://github.com/darbotlabs/darbot-unsloth.git",
        "vcs_info": {"vcs": "git", "commit_id": A},
    }
    monkeypatch.setattr(
        importlib.metadata, "distribution",
        lambda name: SimpleNamespace(read_text = lambda path: json.dumps(provenance)),
    )
    assert stack._core_tracking_intent(source(A)) == "main"
    stack._remember_core_source(source(A), tracking = None)
    assert stack._core_tracking_intent(source(A)) is None


def test_tracking_resolver_uses_only_the_official_main_endpoint(stack, monkeypatch):
    requests = []
    def open_url(request, **kwargs):
        requests.append(request.full_url)
        return io.BytesIO(json.dumps({"sha": B}).encode())

    monkeypatch.setattr(stack.urllib.request, "urlopen", open_url)
    assert stack._resolve_tracked_core_source() == source(B)
    assert requests == ["https://api.github.com/repos/darbotlabs/darbot-unsloth/commits/main"]


@pytest.mark.parametrize("payload", [[], {"sha": "main"}, {"sha": "https://example.invalid"}])
def test_tracking_rejects_unverified_main_responses(stack, monkeypatch, payload):
    monkeypatch.setattr(
        stack.urllib.request, "urlopen",
        lambda *args, **kwargs: io.BytesIO(json.dumps(payload).encode()),
    )
    with pytest.raises(RuntimeError):
        stack._resolve_tracked_core_source()


def make_wheel(directory, name, version, marker, requires = (), extra_files = None):
    directory.mkdir(parents = True, exist_ok = True)
    normalized = name.replace("-", "_")
    info = f"{normalized}-{version}.dist-info"
    files = {
        f"{normalized}/__init__.py": f"MARKER = {marker!r}\n".encode(),
        f"{info}/METADATA": (
            f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n"
            + "".join(f"Requires-Dist: {requirement}\n" for requirement in requires)
        ).encode(),
        f"{info}/WHEEL": b"Wheel-Version: 1.0\nGenerator: fixture\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
    }
    files.update(extra_files or {})
    records = io.StringIO(newline = "")
    writer = csv.writer(records, lineterminator = "\n")
    for path, contents in files.items():
        digest = base64.urlsafe_b64encode(hashlib.sha256(contents).digest()).rstrip(b"=").decode()
        writer.writerow([path, f"sha256={digest}", len(contents)])
    writer.writerow([f"{info}/RECORD", "", ""])
    files[f"{info}/RECORD"] = records.getvalue().encode()
    wheel = directory / f"{normalized}-{version}-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w", zipfile.ZIP_DEFLATED) as archive:
        for path, contents in files.items():
            member = zipfile.ZipInfo(path)
            member.filename = path
            member.orig_filename = path
            archive.writestr(member, contents)
    return wheel


def core_wheel(directory, marker, dependency_version):
    return make_wheel(
        directory, "unsloth", CORE_VERSION, marker,
        [f"unsloth-zoo=={ZOO_VERSION}", "torch==2.14.0"],
        {
            "studio/backend/vendor/unsloth_zoo_compat/pyproject.toml": (
                f'[project]\nname="unsloth-zoo"\nversion="{ZOO_VERSION}"\n'
            ).encode(),
            "studio/backend/vendor/unsloth_zoo_compat/source-marker.txt": marker.encode(),
            "studio/backend/requirements/single-env/constraints.txt": (
                f"tracking-fixture-dep=={dependency_version}\n"
            ).encode(),
        },
    )


@pytest.mark.parametrize("unsafe", ["../escape", "bad\\escape", "trailing. /escape"])
def test_companion_extraction_rejects_unsafe_wheel_paths(stack, tmp_path, unsafe):
    wheel = make_wheel(
        tmp_path, "unsloth", CORE_VERSION, "B",
        extra_files = {f"studio/backend/vendor/unsloth_zoo_compat/{unsafe}": b"bad"},
    )
    with pytest.raises(RuntimeError, match = "unsafe"):
        stack._extract_core_update_sources(wheel, tmp_path / "unpack")


def test_matching_zoo_is_prepared_before_install_and_failure_leaves_snapshot(stack, monkeypatch, tmp_path):
    core = core_wheel(tmp_path / "wheel", "B", "2.0")
    staged = tmp_path / "staged"
    calls = []
    def prepare(spec):
        calls.append(spec)
        if spec == source(B):
            staged.mkdir()
            shutil.copy2(core, staged / core.name)
            return str(staged)
        assert (Path(spec) / "source-marker.txt").read_text() == "B"
        return None

    monkeypatch.setattr(stack, "NO_TORCH", False)
    monkeypatch.setattr(stack, "_resolve_tracked_core_source", lambda: source(B))
    monkeypatch.setattr(stack, "_stage_replacement", prepare)
    monkeypatch.setattr(stack, "_install_core_update_wheels", lambda *a: pytest.fail("No replacement before all staging"))
    stack._remember_core_source(source(A), tracking = "main")
    with pytest.raises(RuntimeError, match = "prepare matching Zoo"):
        stack._refresh_tracked_core(source(A))
    assert len(calls) == 2
    assert stack._remembered_core_source() == source(A)
    assert not staged.exists()


def test_tracked_gguf_refresh_stages_only_core_and_keeps_tracking(stack, monkeypatch, tmp_path):
    wheel = make_wheel(
        tmp_path / "wheel", "unsloth", CORE_VERSION, "B",
        extra_files = {
            "studio/backend/requirements/single-env/constraints.txt": b"",
            "studio/backend/requirements/no-torch-constraints.txt": b"torch<0\n",
        },
    )
    prepared = tmp_path / "prepared"
    calls = []
    def stage(spec):
        calls.append(spec)
        assert spec == source(B)
        prepared.mkdir()
        shutil.copy2(wheel, prepared / wheel.name)
        return str(prepared)

    def install(wheels, constraints):
        assert list(wheels) == ["unsloth"]
        assert constraints.is_file()
        return True

    monkeypatch.setattr(stack, "NO_TORCH", True)
    monkeypatch.setattr(stack, "_resolve_tracked_core_source", lambda: source(B))
    monkeypatch.setattr(stack, "_stage_replacement", stage)
    monkeypatch.setattr(stack, "_install_core_update_wheels", install)
    stack._remember_core_source(source(A), tracking = "main")
    assert stack._refresh_tracked_core(source(A))
    assert calls == [source(B)]
    assert stack._core_source_payload()["tracking"] == "main"
    assert not prepared.exists()


def test_an_unchanged_main_does_not_force_core_or_zoo(stack, monkeypatch):
    monkeypatch.setattr(stack, "_resolve_tracked_core_source", lambda: source(A))
    monkeypatch.setattr(stack, "_stage_replacement", lambda *a: pytest.fail("Unnecessary replacement"))
    assert stack._refresh_tracked_core(source(A)) is False


def test_same_version_main_update_replaces_both_codes_and_survives_cleanup(
    stack, monkeypatch, tmp_path,
):
    # A disposable fixture venv, not another application installation. All wheels
    # are constructed above, all package commands target it explicitly, no index.
    managed = stack.install_manifest.venv_root()
    venv.EnvBuilder(with_pip = False).create(managed)
    python = managed / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    site = Path(subprocess.check_output(
        [str(python), "-I", "-B", "-c", "import sysconfig; print(sysconfig.get_path('purelib'))"],
        text = True,
    ).strip())
    artifacts = tmp_path / "wheels"
    dep1 = make_wheel(artifacts, "tracking-fixture-dep", "1.0", "old dependency")
    make_wheel(artifacts, "tracking-fixture-dep", "2.0", "new dependency")
    torch = make_wheel(artifacts, "torch", "2.14.0", "untouched torch")
    core_a = core_wheel(artifacts / "A", "A", "1.0")
    zoo_a = make_wheel(artifacts / "A", "unsloth-zoo", ZOO_VERSION, "A", ["tracking-fixture-dep==1.0"])
    core_b = core_wheel(artifacts / "B", "B", "2.0")
    zoo_b = make_wheel(artifacts / "B", "unsloth-zoo", ZOO_VERSION, "B", ["tracking-fixture-dep==2.0"])
    env = os.environ.copy()
    env.update({"PIP_NO_INDEX": "1", "PIP_FIND_LINKS": str(artifacts), "PYTHONDONTWRITEBYTECODE": "1"})
    pip = [sys.executable, "-m", "pip", "--python", str(python), "install", "--disable-pip-version-check"]
    subprocess.run(
        [*pip, "--no-deps", str(core_a), str(zoo_a), str(torch), str(dep1)],
        env = env, check = True, capture_output = True,
    )
    original_torch = (site / "torch" / "__init__.py").stat().st_mtime_ns
    original_torch_installer = (site / "torch-2.14.0.dist-info" / "INSTALLER").stat().st_mtime_ns
    stage_paths = []
    def prepare(spec):
        directory = tmp_path / f"staged-{len(stage_paths)}"
        directory.mkdir()
        stage_paths.append(directory)
        if spec == source(B):
            selected = core_b
        else:
            assert (Path(spec) / "source-marker.txt").read_text() == "B"
            selected = zoo_b
        shutil.copy2(selected, directory / selected.name)
        return str(directory)

    calls = []
    def install(label, *args, **kwargs):
        assert kwargs.get("force_pip") is True
        assert len(stage_paths) == 2 and all(path.exists() for path in stage_paths)
        calls.append((label, args))
        result = subprocess.run([*pip, *args], env = env, capture_output = True, text = True)
        assert result.returncode == 0, result.stdout + result.stderr
        return True

    monkeypatch.setattr(stack, "USE_UV", False)
    monkeypatch.setattr(stack, "NO_TORCH", False)
    monkeypatch.setattr(stack, "_resolve_tracked_core_source", lambda: source(B))
    monkeypatch.setattr(stack, "_stage_replacement", prepare)
    monkeypatch.setattr(stack, "pip_install_try", install)
    monkeypatch.setattr(stack, "SCRIPT_DIR", site / "studio")
    stack._remember_core_source(source(A), tracking = "main")
    assert stack._refresh_tracked_core(source(A)) is True
    assert all(not directory.exists() for directory in stage_paths)
    assert (site / "unsloth" / "__init__.py").read_text().strip() == "MARKER = 'B'"
    assert (site / "unsloth_zoo" / "__init__.py").read_text().strip() == "MARKER = 'B'"
    assert (site / "torch" / "__init__.py").stat().st_mtime_ns == original_torch
    assert (site / "torch-2.14.0.dist-info" / "INSTALLER").stat().st_mtime_ns == original_torch_installer
    versions = {
        dist.metadata["Name"]: dist.version
        for dist in importlib.metadata.distributions(path = [str(site)])
    }
    assert versions["unsloth"] == CORE_VERSION
    assert versions["unsloth-zoo"] == ZOO_VERSION
    assert versions["tracking-fixture-dep"] == "2.0"
    forced = [args for _, args in calls if "--force-reinstall" in args]
    assert len(forced) == 1 and "--no-deps" in forced[0]
    assert not any("torch-2.14" in arg for arg in forced[0])
    assert stack._remembered_core_source() == source(B)

    probe = """
import importlib.util,json,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location('next_update',sys.argv[1])
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
m.SCRIPT_DIR=Path(sys.argv[2])/'studio'
snapshot=m._core_repair_source('unsloth')
print(json.dumps({'snapshot':snapshot,'tracking':m._core_tracking_intent(snapshot)}))
"""
    result = subprocess.run(
        [str(python), "-I", "-B", "-c", probe, str(ROOT / "studio" / "install_python_stack.py"), str(site)],
        env = env, check = True, capture_output = True, text = True,
    )
    assert json.loads(result.stdout.strip().splitlines()[-1]) == {
        "snapshot": source(B), "tracking": "main",
    }


def test_tracked_refresh_precedes_any_installed_zoo_bootstrap(stack):
    import inspect
    code = inspect.getsource(stack.install_python_stack)
    assert code.index("_repair_damaged_core_payload(") < code.index("_refresh_tracked_core(")
    assert code.index("_refresh_tracked_core(") < code.index("zoo_helper =")
    assert "if skip_base or core_refreshed:" in code


def test_windows_handoff_and_version_fastpath_preserve_tracking():
    root = (ROOT / "install.ps1").read_text(encoding = "utf-8")
    setup = (ROOT / "studio" / "setup.ps1").read_text(encoding = "utf-8")
    assert '$env:UNSLOTH_CORE_TRACKING_REF = if ($StudioLocalInstall) { "pinned" } else { "main" }' in root
    assert "stack._core_tracking_intent(stack._core_repair_source('unsloth'))" in setup
    assert setup.index("tracking = stack._core_tracking_intent") < setup.index(
        "# install_python_stack.py drops the manifest before its own dependency pass"
    )
