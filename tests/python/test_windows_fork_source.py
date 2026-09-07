"""Source provenance and Git-free Windows bootstrap regressions."""

import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import shutil
from types import SimpleNamespace
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[2]
COMMIT = "a" * 40
DIGEST = "b" * 64
ARCHIVE_URL = f"https://codeload.github.com/darbotlabs/darbot-unsloth/zip/{COMMIT}"


def stack():
    spec = importlib.util.spec_from_file_location(
        "fork_source_stack", ROOT / "studio" / "install_python_stack.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_checkout(module, path):
    for filename in module._CORE_CHECKOUT_FILES:
        target = path / filename
        target.parent.mkdir(parents = True, exist_ok = True)
        target.write_text("", encoding = "utf-8")
    for filename in ("pyproject.toml", "studio/backend/vendor/unsloth_zoo_compat/pyproject.toml"):
        (path / filename).write_bytes((ROOT / filename).read_bytes())
    (path / "unsloth" / "_version.py").write_text('__version__ = "2026.9.3"\n', encoding = "utf-8")
    return path


@pytest.fixture(autouse = True)
def isolate_source_registry(monkeypatch, tmp_path):
    root = tmp_path / "venv"
    root.mkdir()
    monkeypatch.setattr(stack().install_manifest, "venv_root", lambda: root)


@pytest.mark.parametrize("kind", ["archive", "git", "upstream", "missing"])
def test_core_repair_keeps_fork_provenance(monkeypatch, tmp_path, kind):
    module = stack()
    monkeypatch.setattr(module, "SCRIPT_DIR", tmp_path / "site-packages" / "studio")
    provenance = {
        "archive": {"url": ARCHIVE_URL, "archive_info": {"hashes": {"sha256": DIGEST}}},
        "git": {
            "url": "https://github.com/darbotlabs/darbot-unsloth.git",
            "vcs_info": {"vcs": "git", "commit_id": COMMIT},
        },
        "upstream": {
            "url": "https://github.com/unslothai/unsloth.git",
            "vcs_info": {"vcs": "git", "commit_id": COMMIT},
        },
        "missing": {},
    }[kind]
    monkeypatch.setattr(
        importlib.metadata, "distribution",
        lambda name: SimpleNamespace(read_text = lambda path: json.dumps(provenance)),
    )
    monkeypatch.setattr(module.install_manifest, "_installed_metadata_records", lambda name: [])
    if kind in ("upstream", "missing"):
        with pytest.raises(RuntimeError, match = "PyPI package will not be substituted"):
            module._core_repair_source("unsloth")
    else:
        expected = f"unsloth @ {ARCHIVE_URL}"
        if kind == "archive":
            expected += f"#sha256={DIGEST}"
        assert module._core_repair_source("unsloth") == expected


def test_ci_checkout_selects_both_core_and_companion(monkeypatch, tmp_path):
    module = stack()
    selected = make_checkout(module, tmp_path / "candidate")
    monkeypatch.setenv("STUDIO_LOCAL_REPO", str(tmp_path / "unrelated"))
    assert Path(module._core_repair_source("unsloth", ci_source_overlay = str(selected))) == selected
    assert Path(module._core_repair_source("unsloth-zoo", ci_source_overlay = str(selected))) == (
        selected / "studio" / "backend" / "vendor" / "unsloth_zoo_compat"
    )


@pytest.mark.parametrize("retained", [False, True])
def test_installed_container_with_uroman_pyproject_is_not_core_source(
    monkeypatch, tmp_path, retained,
):
    import subprocess
    import sys

    module = stack()
    environment = module.install_manifest.venv_root()
    site = make_checkout(module, environment / "Lib" / "site-packages")
    foreign_project = b'[build-system]\nrequires=["setuptools"]\nbuild-backend="setuptools.build_meta"\n[project]\nname="uroman"\nversion="1.3.1.1"\n'
    (site / "pyproject.toml").write_bytes(foreign_project)
    dist = site / "unsloth-2026.9.3.dist-info"
    dist.mkdir()
    (dist / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: unsloth\nVersion: 2026.9.3\n", encoding = "utf-8",
    )
    provenance = {"url": (tmp_path / "unsloth-2026.9.3-py3-none-any.whl").as_uri(), "archive_info": {}}
    (dist / "direct_url.json").write_text(json.dumps(provenance), encoding = "utf-8")
    monkeypatch.setattr(module, "SCRIPT_DIR", site / "studio")
    monkeypatch.setattr(module.install_manifest, "_installed_metadata_records", lambda name: [])
    monkeypatch.setattr(
        importlib.metadata, "distribution",
        lambda name: SimpleNamespace(read_text = lambda path: json.dumps(provenance)),
    )
    if retained:
        module._remember_core_source(str(ROOT), tracking = None)
        assert Path(module._core_repair_source("unsloth")) == ROOT
    else:
        with pytest.raises(RuntimeError, match = "complete.*checkout"):
            module._core_repair_source("unsloth")
    assert not module._is_core_checkout(site)
    with pytest.raises(RuntimeError, match = "complete maintained checkout"):
        module._core_source_record(str(site))

    probe = """
import importlib.util,sys
from pathlib import Path
script,site,root=map(Path,sys.argv[1:])
sys.path.insert(0,str(site))
spec=importlib.util.spec_from_file_location('production_source_probe',script)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
m.SCRIPT_DIR=site/'studio'
m.install_manifest.venv_root=lambda:root
m.install_manifest._metadata_scan_paths=lambda:[str(site)]
try:
    print('SOURCE='+m._core_repair_source('unsloth'))
except RuntimeError as error:
    print('ERROR='+str(error)); sys.exit(3)
"""
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-c", probe, str(ROOT / "studio" / "install_python_stack.py"), str(site), str(environment)],
        capture_output = True, text = True,
    )
    assert result.returncode == (0 if retained else 3), result.stdout + result.stderr
    assert (f"SOURCE={ROOT}" if retained else "ERROR=Cannot identify") in result.stdout
    assert (site / "pyproject.toml").read_bytes() == foreign_project


def test_git_free_source_archive_has_valid_checkout_identity(tmp_path):
    module = stack()
    checkout = make_checkout(module, tmp_path / "source-archive")
    assert not (checkout / ".git").exists()
    assert module._is_core_checkout(checkout)
    assert module._core_source_record(str(checkout)) == {"kind": "checkout", "path": str(checkout)}


@pytest.mark.parametrize(
    "invalid",
    ["foreign-project", "foreign-backend", "wrong-entrypoint", "missing-version-input", "venv", "site-packages", "dist-packages"],
)
def test_all_core_source_selection_paths_reject_non_checkouts(monkeypatch, tmp_path, invalid):
    module = stack()
    name = invalid if invalid.endswith("packages") else "candidate"
    checkout = make_checkout(module, tmp_path / name)
    project = checkout / "pyproject.toml"
    if invalid == "foreign-project":
        project.write_text(project.read_text().replace('name = "unsloth"', 'name = "uroman"', 1), encoding = "utf-8")
    elif invalid == "foreign-backend":
        project.write_text(project.read_text().replace("setuptools.build_meta", "hatchling.build"), encoding = "utf-8")
    elif invalid == "wrong-entrypoint":
        project.write_text(project.read_text().replace("unsloth_cli:app", "uroman:main"), encoding = "utf-8")
    elif invalid == "missing-version-input":
        (checkout / "unsloth" / "_version.py").unlink()
    elif invalid == "venv":
        (checkout / "pyvenv.cfg").write_text("home = python\n", encoding = "utf-8")
    assert not module._is_core_checkout(checkout)
    with pytest.raises(RuntimeError, match = "complete maintained checkout"):
        module._core_source_record(str(checkout))
    with pytest.raises(RuntimeError, match = "not a complete"):
        module._core_repair_source("unsloth", local_repo = str(checkout))
    with pytest.raises(RuntimeError, match = "not a complete"):
        module._core_repair_source("unsloth-zoo", ci_source_overlay = str(checkout))
    provenance = {"url": checkout.as_uri(), "dir_info": {"editable": True}}
    monkeypatch.setattr(module, "SCRIPT_DIR", tmp_path / "installed" / "studio")
    monkeypatch.setattr(
        importlib.metadata, "distribution",
        lambda name: SimpleNamespace(read_text = lambda path: json.dumps(provenance)),
    )
    with pytest.raises(RuntimeError, match = "working checkout"):
        module._core_repair_source("unsloth")
    with pytest.raises(RuntimeError, match = "complete maintained checkout"):
        module._core_source_from_record({"kind": "checkout", "path": str(checkout)})


@pytest.mark.parametrize("repair", ["payload", "duplicates"])
def test_next_update_keeps_origin_after_offline_wheel_and_staging_cleanup(
    monkeypatch, tmp_path, repair,
):
    import subprocess
    import sys

    module = stack()
    environment = module.install_manifest.venv_root()
    site = environment / "Lib" / "site-packages"
    installed_studio = site / "studio"
    installed_studio.mkdir(parents = True)
    monkeypatch.setattr(module, "SCRIPT_DIR", installed_studio)
    monkeypatch.syspath_prepend(str(site))
    monkeypatch.setattr(module.install_manifest, "_metadata_scan_paths", lambda: [str(site)])
    provenance = {"url": ARCHIVE_URL, "archive_info": {"hashes": {"sha256": DIGEST}}}

    def write_metadata(version, with_origin):
        metadata = site / f"unsloth-{version}.dist-info"
        metadata.mkdir()
        (metadata / "METADATA").write_text(
            f"Metadata-Version: 2.1\nName: unsloth\nVersion: {version}\n", encoding = "utf-8",
        )
        if with_origin:
            (metadata / "direct_url.json").write_text(json.dumps(provenance), encoding = "utf-8")
        return metadata

    write_metadata("2026.9.1", True)
    if repair == "duplicates":
        write_metadata("2026.9.0", True)
    prepared = tmp_path / "prepared-wheel"
    repaired = {"done": False}
    expected = f"unsloth @ {ARCHIVE_URL}#sha256={DIGEST}"

    def stage(source):
        assert source == expected
        prepared.mkdir()
        (prepared / "unsloth-2026.9.1-py3-none-any.whl").write_bytes(b"offline fixture")
        return str(prepared)

    def uninstall(label, command):
        shutil.rmtree(next(site.glob("unsloth-*.dist-info")))
        importlib.invalidate_caches()
        return True

    def install(label, *args, **kwargs):
        assert "--no-index" in args
        # This models the filesystem result of the named --find-links install:
        # fresh wheel metadata exists, but the original direct_url.json is gone.
        for old in site.glob("unsloth-*.dist-info"):
            shutil.rmtree(old)
        write_metadata("2026.9.1", False)
        repaired["done"] = True
        importlib.invalidate_caches()
        return True

    monkeypatch.setattr(module, "_stage_replacement", stage)
    monkeypatch.setattr(module, "_run_ok", uninstall)
    monkeypatch.setattr(module, "pip_install_try", install)
    monkeypatch.setattr(module, "_step", lambda *a, **k: None)
    monkeypatch.setattr(
        module.install_manifest, "damaged_payload_files",
        lambda *a, **k: [] if repaired["done"] else ["missing"],
    )
    function = module._repair_damaged_core_payload if repair == "payload" else module._repair_duplicate_core_metadata
    assert function(("unsloth",))
    assert not prepared.exists()
    assert not list(site.glob("unsloth-*.dist-info/direct_url.json"))
    registry = environment / module._CORE_SOURCE_REGISTRY
    assert registry.is_file()
    assert not registry.is_relative_to(site)
    assert json.loads(registry.read_text(encoding = "utf-8")) == {
        "schema": 1, "core": {"kind": "archive", "commit": COMMIT, "sha256": DIGEST},
    }

    # A new module instance has no in-memory source state from the repair.
    next_update = stack()
    monkeypatch.setattr(next_update, "SCRIPT_DIR", installed_studio)
    assert next_update._core_repair_source("unsloth") == expected
    probe = r"""
import importlib.util, sys
from pathlib import Path
script, site, root = map(Path, sys.argv[1:])
sys.path.insert(0, str(site))
spec = importlib.util.spec_from_file_location("next_update_stack", script)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.SCRIPT_DIR = site / "studio"
module.install_manifest.venv_root = lambda: root
module.install_manifest._metadata_scan_paths = lambda: [str(site)]
print("CORE_SOURCE=" + module._core_repair_source("unsloth"))
"""
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-c", probe, str(ROOT / "studio" / "install_python_stack.py"), str(site), str(environment)],
        capture_output = True, text = True, check = True,
    )
    assert f"CORE_SOURCE={expected}" in result.stdout.splitlines()
    registry.unlink()
    with pytest.raises(RuntimeError, match = "PyPI package will not be substituted"):
        next_update._core_repair_source("unsloth")


def test_failed_source_retention_stops_before_uninstall(monkeypatch, tmp_path):
    module = stack()
    expected = f"unsloth @ {ARCHIVE_URL}#sha256={DIGEST}"
    staged = tmp_path / "prepared"
    staged.mkdir()
    monkeypatch.setattr(module, "_core_repair_source", lambda *a: expected)
    monkeypatch.setattr(module, "_stage_replacement", lambda source: str(staged))
    monkeypatch.setattr(module.install_manifest, "damaged_payload_files", lambda *a, **k: ["missing"])
    monkeypatch.setattr(module, "pip_install_try", lambda *a, **k: pytest.fail("must retain source before uninstall"))
    monkeypatch.setattr(module.os, "replace", lambda *a: (_ for _ in ()).throw(PermissionError("blocked")))
    assert module._repair_damaged_core_payload(("unsloth",)) is False
    assert not staged.exists()
    assert not list(module.install_manifest.venv_root().glob(".unsloth-source-*.json"))


@pytest.mark.parametrize(
    "source",
    [
        f"unsloth @ https://user:secret@codeload.github.com/darbotlabs/darbot-unsloth/zip/{COMMIT}",
        f"unsloth @ {ARCHIVE_URL}?token=secret",
        f"unsloth @ https://codeload.github.com/unslothai/unsloth/zip/{COMMIT}",
    ],
)
def test_source_registry_never_stores_credentials_or_unapproved_origins(source):
    module = stack()
    with pytest.raises(RuntimeError, match = "unverified"):
        module._remember_core_source(source)
    assert not (module.install_manifest.venv_root() / module._CORE_SOURCE_REGISTRY).exists()


def test_current_update_captures_source_before_any_repair():
    import inspect

    source = inspect.getsource(stack().install_python_stack)
    assert source.count("_core_repair_source(") == 1
    assert source.index("selected_core_source =") < source.index("_repair_duplicate_core_metadata(")
    assert source.count("unsloth_spec = selected_core_source") == 1
    assert source.count("_studio_core_install_spec(selected_core_source)") == 1


@pytest.mark.parametrize("repair", ["payload", "duplicates"])
@pytest.mark.parametrize("unavailable", [False, True])
def test_all_replacements_are_prepared_before_core_can_remove_zoo(
    monkeypatch, tmp_path, repair, unavailable,
):
    module = stack()
    packages = ("unsloth", "unsloth-zoo")
    sources = {name: tmp_path / name for name in packages}
    for source in sources.values():
        source.mkdir()
    make_checkout(module, sources["unsloth"])
    events = []
    restored = set()
    records = {name: ["old", "new"] for name in packages}
    monkeypatch.setattr(module, "_core_repair_source", lambda name, *a: str(sources[name]))
    monkeypatch.setattr(module, "_step", lambda *a, **k: None)
    monkeypatch.setattr(module.install_manifest, "invalid_metadata_paths", lambda name: [])
    monkeypatch.setattr(module.install_manifest, "pip_backup_metadata_paths", lambda name: [])
    monkeypatch.setattr(module.install_manifest, "installed_versions", lambda name: records[name])
    monkeypatch.setattr(module.install_manifest, "installed_version_probe", lambda name: ("new", False))
    monkeypatch.setattr(
        module.install_manifest, "damaged_payload_files",
        lambda name, **kwargs: [] if name in restored else ["missing"],
    )

    def stage(source):
        name = Path(source).name
        assert sources[name].is_dir(), "Core removed Zoo's source before it was prepared"
        events.append(("stage", name))
        if unavailable and name == "unsloth-zoo":
            return None
        destination = tmp_path / f"staged-{name}"
        destination.mkdir()
        return str(destination)

    def uninstall(label, command):
        name = command[-1]
        events.append(("uninstall", name))
        records[name].pop()
        if name == "unsloth" and sources["unsloth-zoo"].exists():
            shutil.rmtree(sources["unsloth-zoo"])
        return True

    def install(label, *args, **kwargs):
        name = args[-1]
        events.append(("install", name))
        assert "--no-index" in args
        assert args[args.index("--find-links") + 1] == str(tmp_path / f"staged-{name}")
        if name == "unsloth" and sources["unsloth-zoo"].exists():
            shutil.rmtree(sources["unsloth-zoo"])
        restored.add(name)
        records[name] = ["new"]
        return True

    monkeypatch.setattr(module, "_stage_replacement", stage)
    monkeypatch.setattr(module, "_run_ok", uninstall)
    monkeypatch.setattr(module, "pip_install_try", install)
    function = module._repair_damaged_core_payload if repair == "payload" else module._repair_duplicate_core_metadata
    assert function(packages) is not unavailable
    assert events[:2] == [("stage", "unsloth"), ("stage", "unsloth-zoo")]
    if unavailable:
        assert events == [("stage", "unsloth"), ("stage", "unsloth-zoo")]
        assert all(source.is_dir() for source in sources.values())
    else:
        assert restored == set(packages)


@pytest.mark.parametrize("case", ["complete", "missing-companion", "traversal", "bad-commit"])
def test_windows_archive_bootstrap_needs_no_git_and_rejects_unpublished_source(tmp_path, case):
    from unsloth_pwsh_runner import run_pwsh

    if shutil.which("pwsh") is None:
        pytest.skip("PowerShell unavailable")
    archive = tmp_path / "fixture.zip"
    root_name = f"darbot-unsloth-{COMMIT}"
    files = [
        "pyproject.toml", "unsloth/__init__.py", "unsloth_cli/__init__.py",
        "studio/install_zoo.py", "studio/python_policy.py", "studio/install_python_stack.py",
        "studio/backend/vendor/unsloth_zoo_compat/pyproject.toml",
    ]
    with zipfile.ZipFile(archive, "w") as handle:
        for filename in files:
            if case == "missing-companion" and "vendor" in filename:
                continue
            handle.writestr(f"{root_name}/{filename}", "")
        if case == "traversal":
            handle.writestr(f"{root_name}/../../should-not-appear", "")
    script = r"""
$ErrorActionPreference = 'Stop'
$tokens = $null; $errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($env:INSTALLER_SOURCE, [ref]$tokens, [ref]$errors)
if ($errors) { throw ($errors | Out-String) }
$fn = $ast.FindAll({
    param($node)
    $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Get-MaintainedForkSourceArchive'
}, $true)
Invoke-Expression $fn[0].Extent.Text
function git { throw 'Git must not be invoked' }
function Invoke-RestMethod {
    [CmdletBinding()]param($Uri, $Headers)
    if ($Uri -ne 'https://api.github.com/repos/darbotlabs/darbot-unsloth/commits/main') { throw 'Wrong source authority' }
    return @{ sha = $env:FIXTURE_COMMIT }
}
function Invoke-WebRequest {
    [CmdletBinding()]param($Uri, $OutFile, [switch]$UseBasicParsing)
    if ($Uri -ne "https://codeload.github.com/darbotlabs/darbot-unsloth/zip/$env:FIXTURE_COMMIT") { throw 'Archive is not pinned to selected fork commit' }
    Copy-Item -LiteralPath $env:FIXTURE_ARCHIVE -Destination $OutFile
}
$result = Get-MaintainedForkSourceArchive -DestinationParent $env:FIXTURE_ROOT
ConvertTo-Json $result -Compress
"""
    result = run_pwsh(
        ["pwsh", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output = True,
        text = True,
        env = dict(
            os.environ, INSTALLER_SOURCE = str(ROOT / "install.ps1"),
            FIXTURE_ARCHIVE = str(archive), FIXTURE_ROOT = str(tmp_path),
            FIXTURE_COMMIT = "invalid" if case == "bad-commit" else COMMIT,
        ),
    )
    if case == "complete":
        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout)
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        assert payload["Spec"] == f"unsloth @ {ARCHIVE_URL}#sha256={digest}"
        assert Path(payload["Checkout"], "studio", "install_zoo.py").is_file()
    else:
        assert result.returncode != 0
    assert not (tmp_path / "should-not-appear").exists()


def test_ci_marker_follows_successful_selected_source_install():
    source = (ROOT / "install.ps1").read_text(encoding = "utf-8")
    marker = source.index('substep "CI: overlaying source checkout (completed')
    assert source.index('$overlayExit = Invoke-InstallCommand -Label "overlay local repo"') < marker
    assert source.index('return (Exit-InstallFailure "Failed to overlay local repo') < marker
    assert marker < source.index("# ── Run studio setup")
    assert "bootstrap fork source" not in source
    assert "unsloth @ git+https://" not in source


@pytest.mark.parametrize("local,overlay", [(True, True), (True, False), (False, True)])
def test_ci_marker_only_reports_the_selected_checkout(local, overlay):
    from unsloth_pwsh_runner import run_pwsh

    if shutil.which("pwsh") is None:
        pytest.skip("PowerShell unavailable")
    script = r"""
$tokens = $null; $errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($env:INSTALLER_SOURCE, [ref]$tokens, [ref]$errors)
$marker = $ast.FindAll({
    param($node)
    $node -is [System.Management.Automation.Language.IfStatementAst] -and
    $node.Extent.Text.StartsWith('if ($StudioLocalInstall -and $env:UNSLOTH_CI_SOURCE_OVERLAY)')
}, $true)
if ($marker.Count -ne 1) { throw 'Expected one source provenance marker' }
function substep { param($Message) Write-Output $Message }
$StudioLocalInstall = $env:FIXTURE_LOCAL -eq '1'
$RepoRoot = $env:FIXTURE_CHECKOUT
$env:UNSLOTH_CI_SOURCE_OVERLAY = if ($env:FIXTURE_OVERLAY -eq '1') { $RepoRoot } else { $null }
Invoke-Expression $marker[0].Extent.Text
"""
    result = run_pwsh(
        ["pwsh", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output = True,
        text = True,
        env = dict(
            os.environ, INSTALLER_SOURCE = str(ROOT / "install.ps1"),
            FIXTURE_CHECKOUT = str(ROOT), FIXTURE_LOCAL = str(int(local)),
            FIXTURE_OVERLAY = str(int(overlay)),
        ),
    )
    assert result.returncode == 0, result.stderr
    if local and overlay:
        assert "CI: overlaying source checkout (completed, editable)" in result.stdout
        assert str(ROOT) in result.stdout
    else:
        assert result.stdout.strip() == ""
