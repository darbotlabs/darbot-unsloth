"""Source companion packaging and interpreter-explicit installation contract."""

import ast
import io
import importlib.util
from importlib.metadata import PackageNotFoundError
import json
from pathlib import Path
import subprocess
import sys
import tomllib
from types import ModuleType, SimpleNamespace

from packaging.requirements import Requirement
from packaging.version import Version
import pytest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "studio" / "backend" / "vendor" / "unsloth_zoo_compat"


def installer():
    spec = importlib.util.spec_from_file_location(
        "zoo_installer_under_test", ROOT / "studio" / "install_zoo.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_companion_preserves_provenance_and_license():
    metadata = tomllib.loads((SOURCE / "pyproject.toml").read_text(encoding = "utf-8"))
    provenance = json.loads(
        (SOURCE / "unsloth_zoo" / "_darbot_provenance.json").read_text(encoding = "utf-8")
    )
    assert metadata["project"]["version"] == provenance["version"] == "2026.9.1+darbot.1"
    assert provenance["upstream_commit"] == "46d1da9558e9bec8d5de2f0de3911cce11e2b9c1"
    assert provenance["upstream_commit_timestamp"] == installer().COMPANION_SOURCE_DATE_EPOCH
    assert set(metadata["project"]["license-files"]) == {"LICENSE", "COPYING"}
    assert "GNU LESSER GENERAL PUBLIC LICENSE" in (SOURCE / "LICENSE").read_text(encoding = "utf-8")
    assert "GNU AFFERO GENERAL PUBLIC LICENSE" in (SOURCE / "COPYING").read_text(encoding = "utf-8")
    for name, version in {
        "torch": "2.14.0",
        "trl": "1.12.0",
        "transformers": "5.16.1",
        "datasets": "5.0.1",
    }.items():
        requirement = next(
            Requirement(value)
            for value in metadata["project"]["dependencies"]
            if Requirement(value).name == name
        )
        assert str(requirement.specifier) == f"=={version}"


def test_companion_leaves_compiler_namespace_to_backend_selection():
    metadata = tomllib.loads((SOURCE / "pyproject.toml").read_text(encoding = "utf-8"))["project"]
    extras = metadata["optional-dependencies"]
    base_names = {Requirement(value).name for value in metadata["dependencies"] + extras["core"]}
    assert base_names.isdisjoint(
        {"triton", "triton-windows", "triton-xpu", "triton-rocm", "cut-cross-entropy"}
    )
    intel = [Requirement(value) for value in extras["intelgpu"]]
    assert [(requirement.name, str(requirement.specifier)) for requirement in intel] == [
        ("triton-xpu", "==3.8.0")
    ]
    rocm = [Requirement(value) for value in extras["rocm"]]
    assert [(requirement.name, str(requirement.specifier)) for requirement in rocm] == [
        ("triton-rocm", "==3.8.0")
    ]
    cuda = {Requirement(value).name for value in extras["cuda"]}
    assert cuda == {"triton", "triton-windows", "cut-cross-entropy"}


@pytest.mark.parametrize("backend", ["uv", "pip"])
def test_installs_into_explicit_interpreter_without_ignoring_dependencies(
    monkeypatch, tmp_path, backend
):
    module = installer()
    calls = []
    constraints = tmp_path / "stack constraints.txt"
    constraints.write_text("torch==2.14.0\n", encoding = "utf-8")
    monkeypatch.setattr(module.shutil, "which", lambda name: "uv.exe" if backend == "uv" else None)

    def run(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(
            stdout = json.dumps(
                {
                    "implementation": "cpython",
                    "version": [3, 14, 7],
                    "releaselevel": "final",
                    "free_threaded": False,
                }
            )
        )

    monkeypatch.setattr(module.subprocess, "run", run)
    module.install_zoo(sys.executable, constraints = constraints)
    command = next(command for command in calls if "install" in command)
    assert str(SOURCE) == command[-1]
    assert "--no-deps" not in command
    assert "--force-reinstall" not in command
    assert "--constraint" in command
    if backend == "uv":
        assert command[command.index("--python") + 1] == sys.executable
    else:
        assert command[:4] == [sys.executable, "-m", "pip", "install"]
    assert calls[-1][0] == sys.executable
    assert "importlib.metadata" in calls[-1][-1]


@pytest.mark.parametrize("policy_source", ["constraints", "project"])
@pytest.mark.parametrize(
    ("installed", "repair"),
    [
        (None, False),
        ({"version": "7.36.1", "wheel": "Tag: cp310-abi3-win_amd64"}, False),
        ({"version": "4.25.9", "wheel": "Tag: py3-none-any"}, False),
        ({"version": "4.25.9", "wheel": "Tag: cp310-abi3-win_amd64"}, True),
        ({"version": "4.25.9", "wheel": ""}, True),
    ],
)
def test_pip_repairs_only_same_version_unqualified_protobuf(
    monkeypatch, tmp_path, policy_source, installed, repair
):
    module = installer()
    url = "https://example.invalid/protobuf-4.25.9-py3-none-any.whl#sha256=" + "a" * 64
    requirement = f"protobuf @ {url}"
    source = tmp_path / "companion"
    source.mkdir()
    source.joinpath("pyproject.toml").write_text(
        "[project]\ndependencies = "
        + json.dumps([requirement if policy_source == "project" else "protobuf==4.25.9"]),
        encoding = "utf-8",
    )
    constraints = tmp_path / "constraints.txt"
    constraints.write_text(
        requirement if policy_source == "constraints" else "torch==2.14.0",
        encoding = "utf-8",
    )
    monkeypatch.setattr(module, "COMPANION_SOURCE", source)
    monkeypatch.setattr(module, "_target_python", lambda python: python)
    monkeypatch.setattr(module.shutil, "which", lambda name: None)
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(
            stdout = json.dumps(installed) if command[-1] == module._PROTOBUF_PROBE else "",
        )

    monkeypatch.setattr(module.subprocess, "run", run)
    module.install_zoo(sys.executable, constraints = constraints, installer = "pip")
    installs = [command for command in calls if "install" in command]
    assert len(installs) == 1 + repair
    assert installs[-1][-1] == str(source)
    assert "--force-reinstall" not in installs[-1]
    assert all("--no-deps" not in command for command in calls)
    if repair:
        assert installs[0][-1] == url
        assert installs[0][:4] == [sys.executable, "-m", "pip", "install"]
        assert "--force-reinstall" in installs[0]
        assert "--constraint" in installs[0]
    assert "tags == {'py3-none-any'}" in calls[-1][-1]
    assert "api_implementation.Type() == 'python'" in calls[-1][-1]
    assert "Struct.FromString(value.SerializeToString())" in calls[-1][-1]
    assert "import google" not in module._PROTOBUF_PROBE


def test_rejects_relative_interpreter_before_install():
    with pytest.raises(ValueError, match = "absolute"):
        installer().install_zoo("python")


@pytest.mark.parametrize("backend", ["uv", "pip"])
@pytest.mark.parametrize("refresh", [False, True])
def test_source_refresh_targets_only_zoo_and_verifies_code(monkeypatch, tmp_path, backend, refresh):
    module = installer()
    source = tmp_path / "source"
    package = source / "unsloth_zoo"
    package.mkdir(parents = True)
    package.joinpath("__init__.py").write_text("revision = 'B'\n", encoding = "utf-8")
    stale_build = source / "build" / "lib" / "unsloth_zoo"
    stale_build.mkdir(parents = True)
    stale_build.joinpath("__init__.py").write_text("revision = 'A'\n", encoding = "utf-8")
    source.joinpath("pyproject.toml").write_text("[project]\ndependencies = []\n", encoding = "utf-8")
    monkeypatch.setattr(module, "COMPANION_SOURCE", source)
    monkeypatch.setattr(module, "_target_python", lambda python: python)
    monkeypatch.setattr(module.shutil, "which", lambda name: "uv.exe" if backend == "uv" else None)
    calls, inputs = [], []

    def run(command, **kwargs):
        calls.append(command)
        inputs.append(kwargs.get("input"))
        if refresh and "install" in command:
            stage = Path(command[-1])
            assert not (stage / "build").exists()
            assert (stage / "unsloth_zoo" / "__init__.py").read_text(
                encoding = "utf-8"
            ) == "revision = 'B'\n"
        return SimpleNamespace(stdout = "")

    monkeypatch.setattr(module.subprocess, "run", run)
    module.install_zoo(sys.executable, installer = backend, reinstall_source = refresh)
    assert len(calls) == 2
    command = calls[0]
    if refresh:
        assert Path(command[-1]).name.startswith(".unsloth-zoo-refresh-")
        assert not Path(command[-1]).exists()
        assert stale_build.joinpath("__init__.py").is_file()
    else:
        assert command[-1] == str(source)
    assert "--force-reinstall" not in command
    assert "--no-deps" not in command
    if refresh and backend == "uv":
        assert command[command.index("--reinstall-package") + 1] == "unsloth-zoo"
    elif refresh:
        assert "--no-cache-dir" in command
    else:
        assert "--reinstall-package" not in command
        assert "--no-cache-dir" not in command
    if refresh:
        assert json.loads(inputs[-1]) == module._source_code_manifest(source)
        assert module._SOURCE_VERIFICATION in calls[-1][-1]
    else:
        assert inputs[-1] is None


@pytest.mark.parametrize("active_revision", ["A", "B", "B-with-stale-module"])
def test_same_version_source_verification_rejects_old_or_stale_code(
    monkeypatch, tmp_path, active_revision
):
    module = installer()
    selected = tmp_path / "selected"
    installed = tmp_path / "installed"
    for directory, revision in ((selected, "B"), (installed, active_revision[:1])):
        package = directory / "unsloth_zoo"
        package.mkdir(parents = True)
        package.joinpath("__init__.py").write_text(
            f"__version__ = {module.COMPANION_VERSION!r}\nrevision = {revision!r}\n",
            encoding = "utf-8",
        )
    if active_revision == "B-with-stale-module":
        installed.joinpath("unsloth_zoo", "removed_in_B.py").write_text(
            "old = True\n", encoding = "utf-8"
        )
    manifest = module._source_code_manifest(selected)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(manifest)))
    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: SimpleNamespace(origin = str(installed / "unsloth_zoo" / "__init__.py")),
    )
    if active_revision == "B":
        exec(module._SOURCE_VERIFICATION, {})
    else:
        with pytest.raises(AssertionError, match = "Zoo"):
            exec(module._SOURCE_VERIFICATION, {})


def test_cli_forwards_explicit_source_refresh(monkeypatch):
    module = installer()
    calls = []
    monkeypatch.setattr(
        module, "install_zoo", lambda python, **kwargs: calls.append((python, kwargs))
    )
    assert module.main(["--python", sys.executable, "--reinstall-source"]) == 0
    assert calls == [
        (
            sys.executable,
            {
                "constraints": None,
                "installer": "auto",
                "reinstall_source": True,
            },
        )
    ]


def test_failed_source_refresh_cleans_only_its_stage(monkeypatch, tmp_path):
    module = installer()
    source = tmp_path / "source"
    source.mkdir()
    source.joinpath("retained.txt").write_text("original", encoding = "utf-8")
    stages = []

    def fail(command, **kwargs):
        stages.append(Path(command[-1]))
        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(module.subprocess, "run", fail)
    with pytest.raises(subprocess.CalledProcessError):
        module._install_source(["pip", "install"], source, {}, True)
    assert len(stages) == 1 and not stages[0].exists()
    assert source.joinpath("retained.txt").read_text(encoding = "utf-8") == "original"


@pytest.mark.parametrize(
    ("version", "releaselevel", "accepted"),
    [
        ([3, 14, 6], "final", False),
        ([3, 14, 7], "alpha", False),
        ([3, 14, 7], "beta", False),
        ([3, 14, 7], "candidate", False),
        ([3, 14, 7], None, False),
        ([3, 14, 7], "final", True),
        ([3, 14, 8], "final", True),
        ([3, 15, 0], "final", False),
    ],
)
def test_print_source_requires_a_final_supported_python(
    monkeypatch, capsys, version, releaselevel, accepted
):
    module = installer()
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(
            stdout = json.dumps(
                {
                    "implementation": "cpython",
                    "version": version,
                    "releaselevel": releaselevel,
                    "free_threaded": False,
                }
            )
        )

    monkeypatch.setattr(module.subprocess, "run", run)
    if accepted:
        assert module.main(["--python", sys.executable, "--print-source"]) == 0
        assert capsys.readouterr().out.strip() == str(SOURCE)
    else:
        with pytest.raises(SystemExit) as error:
            module.main(["--python", sys.executable, "--print-source"])
        assert error.value.code == 1
        captured = capsys.readouterr()
        assert captured.out == ""
        assert "final, standard" in captured.err
    assert len(calls) == 1
    assert "sys.version_info.releaselevel" in calls[0][-1]


def test_print_source_supports_one_combined_resolution_without_installing(monkeypatch, capsys):
    module = installer()
    probes = []
    monkeypatch.setattr(module, "_target_python", lambda python: probes.append(python) or python)

    def no_install(*args, **kwargs):
        pytest.fail("--print-source must not install or write package metadata")

    monkeypatch.setattr(module, "install_zoo", no_install)
    assert module.main(["--python", sys.executable, "--print-source"]) == 0
    assert probes == [sys.executable]
    assert capsys.readouterr().out.strip() == str(SOURCE)


def test_rejects_free_threaded_build_before_install(monkeypatch):
    module = installer()
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            stdout = json.dumps(
                {
                    "implementation": "cpython",
                    "version": [3, 14, 7],
                    "releaselevel": "final",
                    "free_threaded": True,
                }
            ),
        ),
    )
    with pytest.raises(ValueError, match = "GIL-enabled"):
        module.install_zoo(sys.executable)


def test_dependency_resolution_failure_is_not_hidden_by_a_fallback(monkeypatch):
    module = installer()
    monkeypatch.setattr(module, "_target_python", lambda python: python)
    monkeypatch.setattr(module.shutil, "which", lambda name: "uv.exe")
    calls = []

    def fail(command, **kwargs):
        calls.append(command)
        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(module.subprocess, "run", fail)
    with pytest.raises(subprocess.CalledProcessError):
        module.install_zoo(sys.executable)
    assert len(calls) == 1


@pytest.mark.parametrize("version", ["2026.9.1", "2026.8.15", None, "2026.9.1+darbot.1"])
def test_runtime_refuses_unmaintained_zoo_with_resolvable_install_hint(monkeypatch, version):
    source = ROOT / "unsloth" / "_gpu_init.py"
    tree = ast.parse(source.read_text(encoding = "utf-8"))
    guard = next(
        node
        for node in tree.body
        if isinstance(node, ast.Try)
        and any(
            isinstance(child, ast.Assign)
            and any(
                getattr(target, "id", None) == "unsloth_zoo_version" for target in child.targets
            )
            for child in node.body
        )
    )

    def installed_version(name):
        if version is None:
            raise PackageNotFoundError(name)
        return version

    monkeypatch.setitem(sys.modules, "unsloth_zoo", ModuleType("unsloth_zoo"))
    namespace = {
        "importlib_version": installed_version,
        "Version": Version,
        "sys": sys,
        "PackageNotFoundError": PackageNotFoundError,
    }
    code = compile(ast.Module(body = [guard], type_ignores = []), str(source), "exec")
    if version == "2026.9.1+darbot.1":
        exec(code, namespace)
    else:
        with pytest.raises(ImportError, match = "studio.install_zoo") as error:
            exec(code, namespace)
        assert "--no-deps" not in str(error.value)
