import pytest

from unsloth_cli._environment import environment_dir


def test_default_environment_is_under_data_root(monkeypatch, tmp_path):
    monkeypatch.delenv("UNSLOTH_ENV_DIR", raising = False)
    monkeypatch.delenv("UNSLOTH_STUDIO_STAGE_ROOT", raising = False)
    assert environment_dir(tmp_path) == tmp_path / "unsloth_studio"


def test_exact_environment_is_not_a_parent_directory(monkeypatch, tmp_path):
    target = tmp_path / "existing-environment"
    monkeypatch.setenv("UNSLOTH_ENV_DIR", f" {target} ")
    monkeypatch.delenv("UNSLOTH_STUDIO_STAGE_ROOT", raising = False)
    assert environment_dir(tmp_path / "data") == target.resolve()


def test_relative_environment_override_is_rejected(monkeypatch, tmp_path):
    import pytest

    monkeypatch.setenv("UNSLOTH_ENV_DIR", "existing-environment")
    monkeypatch.delenv("UNSLOTH_STUDIO_STAGE_ROOT", raising = False)
    with pytest.raises(ValueError, match = "absolute"):
        environment_dir(tmp_path / "data")


def test_staging_never_mutates_the_live_override(monkeypatch, tmp_path):
    monkeypatch.setenv("UNSLOTH_ENV_DIR", str(tmp_path / "live"))
    monkeypatch.setenv("UNSLOTH_STUDIO_STAGE_ROOT", str(tmp_path / "stage"))
    assert environment_dir(tmp_path / "data") == (tmp_path / "stage").resolve() / "unsloth_studio"


def test_installed_interpreter_remembers_its_data_root(monkeypatch, tmp_path):
    import sys

    target = tmp_path / "existing-environment"
    target.mkdir()
    data = tmp_path / "data"
    (target / ".unsloth-studio-owned").touch()
    (target / ".unsloth-studio-home").write_text(str(data), encoding = "utf-8")
    monkeypatch.setattr(sys, "prefix", str(target))
    monkeypatch.delenv("UNSLOTH_ENV_DIR", raising = False)
    monkeypatch.delenv("UNSLOTH_STUDIO_STAGE_ROOT", raising = False)
    assert environment_dir(data) == target.resolve()
    assert environment_dir(tmp_path / "other-data") == tmp_path / "other-data" / "unsloth_studio"


def test_repair_instructions_preserve_exact_environment(monkeypatch, tmp_path, capsys):
    import pytest
    import typer
    from unsloth_cli.commands import studio

    target = tmp_path / "existing environment"
    monkeypatch.setenv("UNSLOTH_ENV_DIR", str(target))
    monkeypatch.delenv("UNSLOTH_STUDIO_STAGE_ROOT", raising = False)
    monkeypatch.setattr(studio, "STUDIO_HOME", tmp_path / "data")
    monkeypatch.setattr(studio, "_STUDIO_HOME_IS_CUSTOM", True)
    monkeypatch.setattr(studio._studio_deps, "running_outside_managed_venv", lambda *a: False)
    monkeypatch.setattr(studio._studio_deps, "damaged_installed_files", lambda *a, **k: ["x: missing"])
    with pytest.raises(typer.Exit):
        studio._fail_if_install_damaged()
    message = capsys.readouterr().err
    assert "UNSLOTH_ENV_DIR" in message
    assert "existing environment" in message
    assert "darbotlabs/darbot-unsloth" in message


@pytest.mark.parametrize(
    "version,free_threaded,supported",
    [
        ((3, 13, 15), False, False),
        ((3, 14, 6), False, False),
        ((3, 14, 7), False, True),
        ((3, 14, 8), False, True),
        ((3, 15, 0), False, False),
        ((3, 14, 7), True, False),
    ],
)
def test_managed_trampoline_checks_the_runtime_range(version, free_threaded, supported):
    import ast
    import collections
    import sys
    import types
    from unsloth_cli.commands import studio

    entry = ast.parse(studio._WINDOWS_CLI_ENTRYPOINT)
    guard = next(node for node in entry.body if isinstance(node, ast.Expr) and isinstance(node.value, ast.IfExp))
    info = collections.namedtuple("Version", "major minor micro releaselevel serial")
    namespace = {
        "sys": types.SimpleNamespace(
            implementation = types.SimpleNamespace(name = "cpython"),
            version_info = info(*version, "final", 0),
            exit = sys.exit,
        ),
        "sysconfig": types.SimpleNamespace(get_config_var = lambda _: free_threaded),
    }
    code = compile(ast.Module(body = [guard], type_ignores = []), "<runtime-guard>", "exec")
    if supported:
        exec(code, namespace)
    else:
        with pytest.raises(SystemExit, match = "standard-GIL CPython"):
            exec(code, namespace)


def test_windows_installer_and_cli_use_the_same_trampoline():
    import re
    from pathlib import Path
    from unsloth_cli.commands import studio

    source = (Path(__file__).resolve().parents[2] / "install.ps1").read_text(encoding = "utf-8")
    match = re.search(r'^\s*\$script:UnslothCliTrampoline = "(.*)"$', source, re.MULTILINE)
    assert match.group(1) == studio._WINDOWS_CLI_ENTRYPOINT
