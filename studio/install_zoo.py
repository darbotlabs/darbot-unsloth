# SPDX-License-Identifier: Apache-2.0
"""Install the source-maintained Zoo companion into an explicit interpreter."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tomllib
from typing import Sequence
import uuid


COMPANION_VERSION = "2026.9.1+darbot.1"
COMPANION_SOURCE_DATE_EPOCH = 1788694117
COMPANION_SOURCE = Path(__file__).resolve().parent / "backend" / "vendor" / "unsloth_zoo_compat"

_PYTHON_PROBE = (
    "import json, sys, sysconfig; "
    "print(json.dumps({'implementation': sys.implementation.name, "
    "'version': list(sys.version_info[:3]), "
    "'releaselevel': sys.version_info.releaselevel, "
    "'free_threaded': bool(sysconfig.get_config_var('Py_GIL_DISABLED'))}))"
)

_PROTOBUF_PROBE = """\
import json
from importlib.metadata import PackageNotFoundError, distribution
try:
    dist = distribution('protobuf')
    result = {'version': dist.version, 'wheel': dist.read_text('WHEEL') or ''}
except PackageNotFoundError:
    result = None
print(json.dumps(result))
"""

_SOURCE_VERIFICATION = """\
import hashlib, json, sys
from importlib.util import find_spec
from pathlib import Path
expected = json.load(sys.stdin)
spec = find_spec('unsloth_zoo')
assert spec is not None and spec.origin, 'Installed Zoo package is not importable'
root = Path(spec.origin).parent
actual_python = {
    path.relative_to(root).as_posix()
    for path in root.rglob('*.py')
    if '__pycache__' not in path.relative_to(root).parts
}
assert actual_python == {name for name in expected if name.endswith('.py')}, (
    'Installed Zoo contains missing or stale Python modules'
)
mismatches = [
    name for name, digest in expected.items()
    if hashlib.sha256((root / name).read_bytes()).hexdigest() != digest
]
assert not mismatches, f'Installed Zoo does not match selected source: {mismatches}'
"""


def _source_code_manifest(source: Path) -> dict[str, str]:
    package = source / "unsloth_zoo"
    if not (package / "__init__.py").is_file():
        raise FileNotFoundError(f"Vendored Zoo package is missing: {package}")
    paths = {
        path
        for path in package.rglob("*.py")
        if "__pycache__" not in path.relative_to(package).parts
    }
    provenance = package / "_darbot_provenance.json"
    if provenance.is_file():
        paths.add(provenance)
    return {
        path.relative_to(package).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(paths)
    }


def _install_source(command, source, environment, refresh):
    if not refresh:
        subprocess.run([*command, str(source)], check = True, env = environment)
        return
    # A clean source tree prevents an old build/lib from winning timestamp-based
    # backend copies when A and B intentionally retain the same version/date.
    stage = Path.cwd() / f".unsloth-zoo-refresh-{uuid.uuid4().hex}"
    stage.mkdir()

    def ignore(directory, names):
        return [
            name
            for name in names
            if name == "__pycache__"
            or name.endswith((".pyc", ".pyo"))
            or (
                Path(directory) == source
                and (name in {"build", "dist", ".git"} or name.endswith(".egg-info"))
            )
        ]

    try:
        shutil.copytree(source, stage, dirs_exist_ok = True, ignore = ignore)
        subprocess.run([*command, str(stage)], check = True, env = environment)
    finally:
        shutil.rmtree(stage)


def _pure_protobuf_requirement(source: Path, constraints: Path | None):
    requirements = []
    if constraints is not None:
        requirements.extend(constraints.read_text(encoding = "utf-8").splitlines())
    metadata = tomllib.loads((source / "pyproject.toml").read_text(encoding = "utf-8"))
    requirements.extend(metadata["project"].get("dependencies", []))
    for requirement in requirements:
        match = re.fullmatch(
            r"\s*protobuf\s*@\s*(\S*/protobuf-([0-9.]+)-py3-none-any\.whl#sha256=[0-9a-f]{64})\s*",
            requirement,
        )
        if match:
            return match.group(1), match.group(2)
    return None


def _repair_pip_protobuf(target, requirement, constraint_args, environment):
    """Pip can retain an installed native wheel even for an explicit same-version URL."""
    url, expected_version = requirement
    result = subprocess.run(
        [target, "-I", "-c", _PROTOBUF_PROBE],
        check = True,
        capture_output = True,
        text = True,
        encoding = "utf-8",
    )
    installed = json.loads(result.stdout)
    if installed and installed.get("version") == expected_version:
        tags = {
            line.removeprefix("Tag:").strip()
            for line in installed.get("wheel", "").splitlines()
            if line.startswith("Tag:")
        }
        if tags != {"py3-none-any"}:
            subprocess.run(
                [
                    target,
                    "-m",
                    "pip",
                    "install",
                    "--disable-pip-version-check",
                    "--force-reinstall",
                    *constraint_args,
                    url,
                ],
                check = True,
                env = environment,
            )


def companion_source() -> Path:
    """Return the local requirement for a combined core/companion resolution."""
    if not (COMPANION_SOURCE / "pyproject.toml").is_file():
        raise FileNotFoundError(f"Vendored Zoo source is missing: {COMPANION_SOURCE}")
    return COMPANION_SOURCE


def _target_python(python: str | os.PathLike[str]) -> str:
    path = Path(python).expanduser()
    if not path.is_absolute() or not path.is_file():
        raise ValueError("--python must name an existing absolute Python executable")
    result = subprocess.run(
        [str(path), "-I", "-c", _PYTHON_PROBE],
        check = True,
        capture_output = True,
        text = True,
        encoding = "utf-8",
    )
    info = json.loads(result.stdout)
    if (
        info.get("implementation") != "cpython"
        or not ((3, 14, 7) <= tuple(info.get("version", ())) < (3, 15, 0))
        or info.get("releaselevel") != "final"
        or info.get("free_threaded")
    ):
        raise ValueError(
            f"Zoo requires a final, standard (GIL-enabled) CPython >=3.14.7,<3.15; target reported {info}"
        )
    return str(path)


def install_zoo(
    python: str | os.PathLike[str],
    *,
    constraints: str | os.PathLike[str] | None = None,
    installer: str = "auto",
    reinstall_source: bool = False,
) -> None:
    """Resolve and install the local companion, preserving dependency validation.

    Index/proxy configuration is inherited from the calling stack installer.
    An already installed CUDA-local Torch 2.14.0 satisfies the public-version
    requirement; this helper does not force-reinstall or downgrade that wheel.
    Explicit source refresh also verifies the installed code, not just its version.
    """
    if installer not in {"auto", "uv", "pip"}:
        raise ValueError("installer must be 'auto', 'uv', or 'pip'")
    target = _target_python(python)
    source = companion_source()
    source_manifest = _source_code_manifest(source) if reinstall_source else None
    constraint_args = []
    constraint_path = None
    if constraints is not None:
        constraint_path = Path(constraints).expanduser().absolute()
        if not constraint_path.is_file():
            raise FileNotFoundError(f"Constraint file is missing: {constraint_path}")
        constraint_args = ["--constraint", str(constraint_path)]
    uv = shutil.which("uv") if installer != "pip" else None
    if installer == "uv" and uv is None:
        raise FileNotFoundError("The requested uv installer is not on PATH")
    if uv:
        command = [uv, "pip", "install", "--python", target]
        if reinstall_source:
            command.extend(["--reinstall-package", "unsloth-zoo"])
    else:
        command = [target, "-m", "pip", "install", "--disable-pip-version-check"]
        if reinstall_source:
            # Pip reinstalls explicitly selected source directories even at
            # the same version. Disable build caches, not dependency reuse.
            command.append("--no-cache-dir")
    build_environment = os.environ.copy()
    build_environment.setdefault("SOURCE_DATE_EPOCH", str(COMPANION_SOURCE_DATE_EPOCH))
    protobuf_requirement = _pure_protobuf_requirement(source, constraint_path)
    if not uv and protobuf_requirement is not None:
        _repair_pip_protobuf(target, protobuf_requirement, constraint_args, build_environment)
    _install_source([*command, *constraint_args], source, build_environment, reinstall_source)
    # Metadata is read, never rewritten. An installer success must leave the
    # maintained companion installed, not an older capped PyPI distribution.
    verification = (
        "from importlib.metadata import version; "
        f"actual = version('unsloth_zoo'); expected = {COMPANION_VERSION!r}; "
        "assert actual == expected, f'Expected Zoo {expected}, found {actual}'"
    )
    if protobuf_requirement is not None:
        verification += (
            "; from importlib.metadata import distribution; dist = distribution('protobuf'); "
            f"assert dist.version == {protobuf_requirement[1]!r}; "
            "tags = {line.removeprefix('Tag:').strip() "
            "for line in (dist.read_text('WHEEL') or '').splitlines() if line.startswith('Tag:')}; "
            "assert tags == {'py3-none-any'}, 'The qualified pure-Python protobuf artifact was not installed'; "
            "from google.protobuf.internal import api_implementation; "
            "assert api_implementation.Type() == 'python', 'Expected the pure-Python protobuf runtime'; "
            "from google.protobuf.struct_pb2 import Struct; value = Struct(); "
            "value.update({'qualified': True}); "
            "assert Struct.FromString(value.SerializeToString())['qualified'] is True"
        )
    verification_kwargs = {}
    if source_manifest is not None:
        verification += "\n" + _SOURCE_VERIFICATION
        verification_kwargs = {
            "input": json.dumps(source_manifest),
            "text": True,
            "encoding": "utf-8",
        }
    subprocess.run(
        [
            target,
            "-I",
            "-c",
            verification,
        ],
        check = True,
        **verification_kwargs,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description = __doc__)
    parser.add_argument("--python", required = True, help = "Absolute target Python executable")
    parser.add_argument("--constraints", help = "Optional shared dependency constraints file")
    parser.add_argument("--installer", choices = ("auto", "uv", "pip"), default = "auto")
    parser.add_argument(
        "--reinstall-source",
        action = "store_true",
        help = "Refresh only Zoo from the selected source and verify its code, even at the same version",
    )
    parser.add_argument(
        "--print-source",
        action = "store_true",
        help = "Print the local requirement for a combined resolver invocation without installing",
    )
    args = parser.parse_args(argv)
    try:
        if args.print_source:
            _target_python(args.python)
            print(companion_source())
        else:
            install_zoo(
                args.python,
                constraints = args.constraints,
                installer = args.installer,
                reinstall_source = args.reinstall_source,
            )
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Zoo companion installation failed: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
