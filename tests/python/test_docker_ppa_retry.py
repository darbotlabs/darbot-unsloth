# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2026-Present the Unsloth team. See /studio/LICENSE.AGPL-3.0
"""Docker uses a shared managed interpreter, never a minor-only apt package."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_both_stages_share_the_exact_supported_interpreter():
    text = (REPO_ROOT / "docker" / "Dockerfile").read_text(encoding = "utf-8")
    assert "ARG PYTHON_VERSION=3.14.7" in text
    assert 'uv python install "${PYTHON_VERSION}"' in text
    assert "COPY --from=builder /opt/python /opt/python" in text
    assert "add-apt-repository" not in text
    assert "python${PYTHON_VERSION}-dev" not in text
    assert 'not sysconfig.get_config_var("Py_GIL_DISABLED")' in text


def test_studio_uses_base_interpreter_and_checks_abi_before_dedup():
    text = (REPO_ROOT / "docker" / "Dockerfile.studio").read_text(encoding = "utf-8")
    assert "UNSLOTH_PYTHON=/opt/unsloth-venv/bin/python" in text
    assert 'test "${BASE_PYTHON}" = "${STUDIO_PYTHON}"' in text
    assert 'diff -qr "$s" "$b"' in text
    assert "libnvrtc.so.12.cu13" not in text


def test_companion_and_cuda_torch_resolve_with_local_core():
    text = (REPO_ROOT / "docker" / "Dockerfile").read_text(encoding = "utf-8")
    bootstrap = text.split("# vLLM is optional", 1)[0]
    assert "--python ${VENV}/bin/python --print-source)" in bootstrap
    assert bootstrap.count("${VENV}/bin/uv pip install") == 1
    install = bootstrap.split("${VENV}/bin/uv pip install", 1)[1]
    assert '"torch==2.14.0+cu130"' in install
    assert '"${ZOO_SOURCE}"' in install
    assert '"/opt/unsloth-src[${UNSLOTH_EXTRA}]"' in install
    assert "--no-deps" not in bootstrap


def test_notebook_audio_dependencies_preserve_the_core_graph():
    text = (REPO_ROOT / "docker" / "Dockerfile").read_text(encoding = "utf-8")
    notebook = text.split("# JupyterLab so the image", 1)[1].split("# decord (ERNIE", 1)[0]
    for spec in ("librosa==1.0.0", "numpy==2.5.3", "numba==0.67.0"):
        assert f'"{spec}"' in notebook
    assert "protobuf==" not in notebook
    assert "api_implementation.Type() == 'python'" in notebook
    assert "${VENV}/bin/uv pip check --python ${VENV}/bin/python" in notebook


def test_completed_images_check_dependencies_after_the_last_install():
    text = (REPO_ROOT / "docker" / "Dockerfile").read_text(encoding = "utf-8")
    final_check = text.rindex("/bin/uv pip check --python /opt/unsloth-venv/bin/python")
    assert final_check > text.rindex("/bin/uv pip install")
    assert "version('protobuf') == '4.25.9'" in text[final_check:]
    assert "api_implementation.Type() == 'python'" in text[final_check:]
    assert "protobuf==6.33.6" not in text
    studio = (REPO_ROOT / "docker" / "Dockerfile.studio").read_text(encoding = "utf-8")
    assert studio.index("/bin/uv pip check") > studio.index("bash install.sh --local")
    assert (
        'pip check --python "${UNSLOTH_STUDIO_HOME}/unsloth_studio/bin/python"'
        in studio
    )


def test_training_smoke_does_not_blanket_reject_turing(monkeypatch):
    import importlib.util
    import sys
    import sysconfig
    from types import SimpleNamespace

    spec = importlib.util.spec_from_file_location(
        "docker_smoke_policy", REPO_ROOT / "docker" / "smoke_test.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(
        module,
        "sys",
        SimpleNamespace(
            implementation = SimpleNamespace(name = "cpython"),
            version_info = (3, 14, 7),
            exit = sys.exit,
        ),
    )
    monkeypatch.setattr(sysconfig, "get_config_var", lambda name: None)
    monkeypatch.setitem(
        sys.modules,
        "torch",
        SimpleNamespace(
            __version__ = "2.14.0+cu130",
            version = SimpleNamespace(cuda = "13.0"),
            _C = SimpleNamespace(_cuda_getArchFlags = lambda: "sm_75 sm_100 sm_120"),
            cuda = SimpleNamespace(
                is_available = lambda: True,
                get_device_capability = lambda index: (7, 5),
                get_device_name = lambda index: "NVIDIA T1000",
            ),
        ),
    )
    assert module.check_torch() == (7, 5)
