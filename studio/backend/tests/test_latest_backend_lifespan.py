# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2026-present the Unsloth AI Inc. team. All rights reserved. See /studio/LICENSE.AGPL-3.0

"""Real application lifespans with isolated data and no external connections."""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


BACKEND = Path(__file__).resolve().parents[1]
NO_TORCH_IMPORT_GUARD = r"""
import importlib.abc
import importlib.metadata
import importlib.util

missing_packages = {
    "torch", "torchvision", "torchaudio", "triton", "unsloth_zoo", "accelerate",
    "peft", "trl", "sentence_transformers", "torchao", "torchcodec", "xformers",
    "bitsandbytes", "cut_cross_entropy", "audiotools", "dac", "snac", "timm",
    "whisper", "julius", "torch_stoi", "torch_c_dlpack_ext", "pytorch_tokenizers",
}
assert not missing_packages.intersection(sys.modules)
class MissingMLPackages(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".", 1)[0] in missing_packages:
            raise ModuleNotFoundError(f"No module named {fullname!r}", name=fullname)
        return None
sys.meta_path.insert(0, MissingMLPackages())
original_find_spec = importlib.util.find_spec
def find_spec(name, *args, **kwargs):
    if name.split(".", 1)[0] in missing_packages:
        return None
    return original_find_spec(name, *args, **kwargs)
importlib.util.find_spec = find_spec
missing_distributions = {name.replace("_", "-") for name in missing_packages} | {
    "triton-windows", "triton-xpu", "triton-rocm", "descript-audiotools",
    "descript-audio-codec", "openai-whisper",
}
original_distribution = importlib.metadata.distribution
def distribution(name):
    if name.lower().replace("_", "-") in missing_distributions:
        raise importlib.metadata.PackageNotFoundError(name)
    return original_distribution(name)
importlib.metadata.distribution = distribution
os.environ["USE_TORCH"] = "0"
os.environ["USE_TF"] = "0"
"""
SCRIPT = r"""
import asyncio
import ipaddress
import json
import os
from pathlib import Path
import sys

blocked = []

def audit(event, args):
    if event == "socket.connect":
        address = args[1]
        if isinstance(address, tuple):
            host = address[0]
            try:
                local = ipaddress.ip_address(host).is_loopback
            except ValueError:
                local = host == "localhost"
            if not local:
                blocked.append(str(host))
                raise RuntimeError("External connections are disabled in this startup smoke")

sys.addaudithook(audit)
import main
import httpx

# Startup's legacy repository-overlay migration must not touch another user's
# directory. All other startup/shutdown work uses the isolated roots below.
overlay = Path(main.__file__).resolve().parents[2] / ".venv_overlay"
original_is_dir = Path.is_dir
Path.is_dir = lambda self: False if self == overlay else original_is_dir(self)

async def smoke():
    async with main.app.router.lifespan_context(main.app):
        if os.environ["STUDIO_TEST_WITHOUT_TORCH"] == "1":
            assert await asyncio.to_thread(main.join_background_warm, 30)
            warm = main.warm_status()
            assert warm["stages"]["inference_backend"]["ok"], warm
        schema = main.app.openapi()
        assert "/api/health" in schema["paths"]
        transport = httpx.ASGITransport(app=main.app, client=("127.0.0.1", 12345))
        async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1") as client:
            health = await client.get("/api/health")
            assert health.status_code == 200, health.text
            assert health.json()["status"] == "healthy"
            if os.environ["UNSLOTH_STUDIO_ENABLE_MCP"] == "1":
                denied = await client.get("/mcp/")
                assert denied.status_code == 401, denied.text
    assert main.app.state.idle_unload_task.done()
    assert not blocked, blocked
    print("STUDIO_LIFESPAN_RESULT " + json.dumps({
        "mcp": os.environ["UNSLOTH_STUDIO_ENABLE_MCP"] == "1",
        "health": health.status_code,
        "openapi_paths": len(schema["paths"]),
        "shutdown": True,
    }))

asyncio.run(smoke())
"""


@pytest.mark.parametrize("profile", ["full", "gguf-only"])
@pytest.mark.parametrize("enable_mcp", [False, True])
def test_real_backend_lifespan_with_current_stack(tmp_path, enable_mcp, profile):
    without_torch = profile == "gguf-only"
    home = tmp_path / "home"
    studio = tmp_path / "studio"
    cache = tmp_path / "cache"
    work = tmp_path / "work"
    for directory in (home, studio, cache, work):
        directory.mkdir()
    env = dict(os.environ)
    for key in (
        "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy",
        "HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "UNSLOTH_STUDIO_DESKTOP_OWNER_TOKEN",
    ):
        env.pop(key, None)
    env.update({
        "HOME": str(home),
        "USERPROFILE": str(home),
        "APPDATA": str(home / "AppData" / "Roaming"),
        "LOCALAPPDATA": str(home / "AppData" / "Local"),
        "STUDIO_HOME": str(studio),
        "UNSLOTH_STUDIO_HOME": str(studio),
        "UNSLOTH_STUDIO_DOCUMENTS_HOME": str(home / "Documents"),
        "UNSLOTH_STUDIO_PROJECTS_HOME": str(home / "Documents" / "Projects"),
        "UNSLOTH_ENV_DIR": sys.prefix,
        "TEMP": str(work),
        "TMP": str(work),
        "HF_HOME": str(cache / "huggingface"),
        "HF_HUB_CACHE": str(cache / "huggingface" / "hub"),
        "HUGGINGFACE_HUB_CACHE": str(cache / "huggingface" / "hub"),
        "HF_TOKEN_PATH": str(cache / "huggingface" / "token"),
        "HF_XET_CACHE": str(cache / "huggingface" / "xet"),
        "XDG_CACHE_HOME": str(cache),
        "XDG_CONFIG_HOME": str(home / "config"),
        "TORCH_HOME": str(cache / "torch"),
        "TORCHINDUCTOR_CACHE_DIR": str(cache / "inductor"),
        "TRITON_CACHE_DIR": str(cache / "triton"),
        "NUMBA_CACHE_DIR": str(cache / "numba"),
        "MPLCONFIGDIR": str(cache / "matplotlib"),
        "UNSLOTH_COMPILE_LOCATION": str(cache / "compiled"),
        "HF_HUB_OFFLINE": "1",
        "HF_DATASETS_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "UNSLOTH_STUDIO_DISABLE_TORCH_WARM": "0" if without_torch else "1",
        "STUDIO_TEST_WITHOUT_TORCH": "1" if without_torch else "0",
        "UNSLOTH_DISABLE_UPDATE_CHECK": "1",
        "UNSLOTH_DISABLE_MLX_AUTOREPAIR": "1",
        "UNSLOTH_HELPER_MODEL_DISABLE": "1",
        "UNSLOTH_STUDIO_ENABLE_MCP": "1" if enable_mcp else "0",
        "UNSLOTH_STUDIO_MCP_TOKEN": "isolated-lifespan-test-token",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUTF8": "1",
        "NO_PROXY": "*",
    })
    script = SCRIPT
    if without_torch:
        # Model an absent ML installation without uninstalling from the shared
        # test environment. Keep DD and both seed plugins available.
        script = script.replace("import main\n", NO_TORCH_IMPORT_GUARD + "\nimport main\n")
    result = subprocess.run(
        [sys.executable, "-X", "utf8", "-c", script],
        cwd = BACKEND,
        env = env,
        capture_output = True,
        text = True,
        encoding = "utf-8",
        timeout = 90,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    line = next(
        line for line in result.stdout.splitlines() if line.startswith("STUDIO_LIFESPAN_RESULT ")
    )
    report = json.loads(line.removeprefix("STUDIO_LIFESPAN_RESULT "))
    assert report["mcp"] is enable_mcp
    assert report["health"] == 200
    assert report["shutdown"]
    assert (studio / "studio.db").exists()
