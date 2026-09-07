# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2026-present the Unsloth AI Inc. team. All rights reserved. See /studio/LICENSE.AGPL-3.0

"""Regression contracts for the CPython 3.14 / Data Designer 0.9 stack."""

import ast
import importlib.metadata
import importlib.util
import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


BACKEND = Path(__file__).resolve().parents[1]
REQUIREMENTS = BACKEND / "requirements"
PROTOBUF_PURE_WHEEL_URL = (
    "https://files.pythonhosted.org/packages/16/28/"
    "d5065b212685875d3924bcdb3201cbf467cb4d58a18aa19a8dfd99ea80a9/"
    "protobuf-4.25.9-py3-none-any.whl"
    "#sha256=d49b615e7c935194ac161f0965699ac84df6112c378e05ec53da65d2e4cbb6d4"
)
TORCH_ONLY_REQUIREMENTS = {
    "torch", "torchvision", "torchaudio", "unsloth-zoo", "accelerate", "peft",
    "trl", "sentence-transformers", "cut-cross-entropy", "triton", "triton-windows",
    "triton-xpu", "triton-rocm",
}


def _requirements(path, *, platform = "win32", machine = "AMD64"):
    env = {
        **default_environment(),
        "python_version": "3.14",
        "python_full_version": "3.14.7",
        "sys_platform": platform,
        "platform_system": {"win32": "Windows", "darwin": "Darwin", "linux": "Linux"}[platform],
        "platform_machine": machine,
    }
    result = {}
    for line in path.read_text(encoding = "utf-8").splitlines():
        line = re.split(r"\s+#", line, maxsplit = 1)[0].strip()
        if not line or line.startswith(("#", "-")):
            continue
        requirement = Requirement(line)
        if requirement.marker is None or requirement.marker.evaluate(env):
            result[canonicalize_name(requirement.name)] = requirement
    return result


@pytest.mark.parametrize(
    ("platform", "machine"),
    [("win32", "AMD64"), ("linux", "x86_64"), ("darwin", "arm64"), ("darwin", "x86_64")],
)
def test_manifests_agree_on_shared_pins(platform, machine):
    pinned = {}
    for path in REQUIREMENTS.rglob("*.txt"):
        for name, requirement in _requirements(path, platform = platform, machine = machine).items():
            versions = [s.version for s in requirement.specifier if s.operator == "=="]
            if name == "protobuf":
                assert requirement.url == PROTOBUF_PURE_WHEEL_URL
                versions = ["4.25.9"]
            if versions:
                version = versions[0]
                if name in pinned:
                    assert pinned[name] == version, (name, path, pinned[name], version)
                pinned[name] = version
    assert pinned["datasets"] == "5.0.1"
    assert pinned["scikit-learn"] == "1.9.0"
    assert pinned["pyarrow"] == "24.0.0"
    assert pinned["pandas"] == "2.3.3"
    assert pinned["pydantic-core"] == "2.46.5"
    assert pinned["protobuf"] == "4.25.9"
    assert pinned["tensorboard"] == "2.20.0"
    assert pinned["fastmcp"] == "3.4.7"
    assert pinned["mcp"] == "1.29.1"
    assert pinned["av"] == ("15.1.0" if platform == "darwin" else "18.1.0")
    audio = _requirements(REQUIREMENTS / "extras-no-deps.txt")["descript-audiotools"]
    assert audio.url == (
        "https://github.com/descriptinc/audiotools/archive/"
        "ffe03e96b4d2dfb3ddecad289a6a95a7e96cc8c6.zip"
        "#sha256=c5093d26afeeec1e9dc2ecfac6a7a6e74ce9c349ff10668c1d3c9f11d7685689"
    )


def test_no_obsolete_interpreter_branches():
    for path in REQUIREMENTS.rglob("*.txt"):
        for line in path.read_text(encoding = "utf-8").splitlines():
            if line.strip() and not line.lstrip().startswith("#"):
                assert "python_version" not in line, (path, line)


def test_no_torch_runtime_does_not_select_cuda_training_packages():
    requirements = _requirements(
        REQUIREMENTS / "no-torch-runtime.txt", platform = "linux", machine = "x86_64"
    )
    assert not TORCH_ONLY_REQUIREMENTS.intersection(requirements)


def test_no_torch_constraints_fail_closed_without_adding_dependencies():
    constraints = _requirements(REQUIREMENTS / "no-torch-constraints.txt")
    assert constraints.keys() == {
        "torch", "torchvision", "torchaudio", "unsloth-zoo", "triton",
        "triton-windows", "triton-xpu", "triton-rocm",
    }
    for requirement in constraints.values():
        assert str(requirement.specifier) == "<0"
        assert requirement.url is None and requirement.marker is None
        assert not requirement.extras
        for version in ("0", "0.1.0", "2.14.0", "3.8.0", "2026.9.1+darbot.1"):
            assert not requirement.specifier.contains(version, prereleases = True)


@pytest.mark.parametrize(
    "filename", ["test_studio_import_no_torch.py", "test_e2e_no_torch_sandbox.py"]
)
def test_no_torch_sandbox_fixtures_use_supported_python(filename):
    path = BACKEND.parents[1] / "tests" / "python" / filename
    tree = ast.parse(path.read_text(encoding = "utf-8"))
    fixture = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "no_torch_venv"
    )
    parameters = next(
        keyword.value
        for decorator in fixture.decorator_list if isinstance(decorator, ast.Call)
        for keyword in decorator.keywords if keyword.arg == "params"
    )
    assert ast.literal_eval(parameters) == ["3.14.7"]
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "_create_no_torch_venv":
            assert ast.literal_eval(node.args.defaults[-1]) == "3.14.7"


@pytest.mark.parametrize(
    ("platform", "machine"),
    [("win32", "AMD64"), ("linux", "x86_64"), ("darwin", "arm64"), ("darwin", "x86_64")],
)
def test_no_torch_runtime_contains_studio_api_requirements(platform, machine):
    runtime = _requirements(
        REQUIREMENTS / "no-torch-runtime.txt", platform = platform, machine = machine
    )
    studio = _requirements(REQUIREMENTS / "studio.txt", platform = platform, machine = machine)
    assert studio.keys() <= runtime.keys()
    for name, requirement in studio.items():
        assert requirement.specifier == runtime[name].specifier, name
        assert requirement.url == runtime[name].url, name
        assert requirement.extras <= runtime[name].extras, name


def test_no_torch_runtime_normal_dependency_graph():
    import tomllib

    environment = default_environment()
    roots = []
    for path in (
        REQUIREMENTS / "no-torch-runtime.txt",
        REQUIREMENTS / "single-env" / "data-designer.txt",
        REQUIREMENTS / "single-env" / "data-designer-deps.txt",
    ):
        roots.extend(_requirements(
            path,
            platform = environment["sys_platform"],
            machine = environment["platform_machine"],
        ).values())
    root_project = BACKEND.parents[1] / "pyproject.toml"
    for path in (root_project, *(BACKEND / "plugins").glob("*/pyproject.toml")):
        project = tomllib.loads(path.read_text(encoding = "utf-8"))["project"]
        declared = list(project.get("dependencies", []))
        if path == root_project:
            declared.extend(project["optional-dependencies"]["studio"])
        for raw in declared:
            requirement = Requirement(raw)
            if requirement.marker is None or requirement.marker.evaluate({"extra": ""}):
                roots.append(requirement)
    pending = [(requirement, ("no-torch",)) for requirement in roots]
    visited = set()
    while pending:
        requirement, chain = pending.pop()
        name = canonicalize_name(requirement.name)
        assert name not in TORCH_ONLY_REQUIREMENTS, " -> ".join((*chain, name))
        distribution = importlib.metadata.distribution(name)
        assert requirement.specifier.contains(distribution.version, prereleases = True), requirement
        key = (name, frozenset(requirement.extras))
        if key in visited:
            continue
        visited.add(key)
        for raw in distribution.requires or []:
            dependency = Requirement(raw)
            if dependency.marker and not any(
                dependency.marker.evaluate({"extra": extra})
                for extra in requirement.extras or {""}
            ):
                continue
            pending.append((dependency, (*chain, name)))


def test_plugin_python_contract_tracks_supported_patch_releases():
    import tomllib
    from packaging.specifiers import SpecifierSet

    for path in (BACKEND / "plugins").glob("*/pyproject.toml"):
        project = tomllib.loads(path.read_text(encoding = "utf-8"))["project"]
        supported = SpecifierSet(project["requires-python"])
        assert "3.14.7" in supported
        assert "3.14.8" in supported
        assert "3.14.6" not in supported
        assert "3.15.0" not in supported


def test_data_designer_direct_dependency_closure():
    pytest.importorskip("data_designer")
    declared = {
        **_requirements(REQUIREMENTS / "single-env" / "data-designer.txt"),
        **_requirements(REQUIREMENTS / "single-env" / "data-designer-deps.txt"),
    }
    for distribution in ("data-designer", "data-designer-config", "data-designer-engine"):
        assert importlib.metadata.version(distribution) == "0.9.2"
        for raw in importlib.metadata.requires(distribution) or []:
            dependency = Requirement(raw)
            if dependency.marker and not dependency.marker.evaluate({"extra": ""}):
                continue
            name = canonicalize_name(dependency.name)
            assert name in declared, (distribution, dependency)
            selected = next(iter(declared[name].specifier)).version
            assert dependency.specifier.contains(selected, prereleases = True), dependency
            assert dependency.extras <= declared[name].extras, dependency


def test_dac_audio_roundtrip_with_compatible_tensorboard(tmp_path):
    for module in ("audiotools", "dac"):
        if importlib.util.find_spec(module) is None:
            pytest.skip(f"Optional audio runtime {module} is not installed")

    assert importlib.metadata.version("descript-audiotools") == "0.7.4"
    for distribution in ("descript-audiotools", "tensorboard"):
        for raw in importlib.metadata.requires(distribution) or []:
            dependency = Requirement(raw)
            if dependency.marker and not dependency.marker.evaluate({"extra": ""}):
                continue
            installed = importlib.metadata.version(dependency.name)
            assert dependency.specifier.contains(installed), (distribution, dependency, installed)

    import torch
    from audiotools import AudioSignal
    from dac import DAC
    from torch.utils.tensorboard import SummaryWriter
    from tensorboard.backend.event_processing.event_accumulator import EventAccumulator

    signal = AudioSignal(torch.randn(1, 1, 1024), sample_rate = 24000)
    codec = DAC(
        encoder_dim = 8,
        encoder_rates = [2, 2],
        decoder_dim = 32,
        decoder_rates = [2, 2],
        n_codebooks = 2,
        sample_rate = 24000,
    ).eval()
    with torch.inference_mode():
        result = codec(signal.audio_data, sample_rate = signal.sample_rate)
        decoded = codec.decode(codec.quantizer.from_codes(result["codes"])[0])
    assert result["audio"].shape == signal.audio_data.shape
    assert torch.isfinite(result["audio"]).all()
    torch.testing.assert_close(decoded[..., :1024], result["audio"])
    checkpoint = tmp_path / "codec.pth"
    codec.save(str(checkpoint), package = False)
    restored = DAC.load(str(checkpoint), strict = True).eval()
    with torch.inference_mode():
        restored_audio = restored(signal.audio_data, sample_rate = signal.sample_rate)["audio"]
    torch.testing.assert_close(restored_audio, result["audio"])

    with SummaryWriter(log_dir = str(tmp_path)) as writer:
        writer.add_scalar("codec/peak", result["audio"].abs().max().item(), 1)
    events = EventAccumulator(str(tmp_path)).Reload()
    assert len(events.Scalars("codec/peak")) == 1


def _base_transformers_metadata(monkeypatch, tmp_path, version):
    import utils.transformers_version as versions

    base = tmp_path / "base"
    metadata = base / f"transformers-{version}.dist-info" / "METADATA"
    metadata.parent.mkdir(parents = True)
    metadata.write_text(f"Name: transformers\nVersion: {version}\n", encoding = "utf-8")
    monkeypatch.setattr(versions.sysconfig, "get_path", lambda name: str(base))
    return versions


@pytest.mark.parametrize(
    ("version", "supported"),
    [("5.15.0", False), ("5.16.1", True), ("5.16.2", True), ("6.0.0", False)],
)
def test_fixed_transformers_base_metadata_support(monkeypatch, tmp_path, version, supported):
    versions = _base_transformers_metadata(monkeypatch, tmp_path, version)
    assert versions._base_transformers_supports("530") is supported
    assert versions._base_transformers_supports("latest") is False


@pytest.mark.parametrize("tier", ["default", "530", "550", "510"])
def test_fixed_transformers_tiers_use_base_without_shadow_installs(monkeypatch, tmp_path, tier):
    versions = _base_transformers_metadata(monkeypatch, tmp_path, "5.16.1")
    shadows = []
    for label in ("530", "550", "510", "LATEST"):
        path = tmp_path / f".venv_t5_{label.lower()}"
        path.mkdir()
        shadows.append(str(path))
        monkeypatch.setattr(versions, f"_VENV_T5_{label}_DIR", str(path))
    marker = Path(shadows[0]) / "preserve.txt"
    marker.write_text("existing installation", encoding = "utf-8")
    monkeypatch.setattr(versions.sys, "path", [*shadows, *versions.sys.path])
    keep = str(tmp_path / "custom-pythonpath")
    monkeypatch.setenv("PYTHONPATH", os.pathsep.join([*shadows, keep]))
    monkeypatch.setattr(versions, "get_transformers_activation_tier", lambda *args: tier)
    for label in ("530", "550", "510"):
        monkeypatch.setattr(
            versions,
            f"_ensure_venv_t5_{label}_exists",
            lambda: pytest.fail("The supported base must not install a fixed sidecar"),
        )

    versions.activate_transformers_for_subprocess("example/model")
    assert not set(shadows).intersection(versions.sys.path)
    assert os.environ["PYTHONPATH"] == keep
    assert marker.read_text(encoding = "utf-8") == "existing installation"


def test_fixed_transformers_probe_uses_base_without_installing_shadows(monkeypatch, tmp_path):
    versions = _base_transformers_metadata(monkeypatch, tmp_path, "5.16.1")
    for label in ("530", "550", "510"):
        monkeypatch.setattr(
            versions,
            f"_ensure_venv_t5_{label}_exists",
            lambda: pytest.fail("Probing must not install redundant fixed shadows"),
        )
    probes = versions._probe_tier_venvs()
    for tier in ("530", "550", "510"):
        target, ensure = probes[tier]
        assert target == ""
        assert ensure()

    monkeypatch.delenv("UNSLOTH_DISABLE_TIER_PROBE", raising = False)
    monkeypatch.setattr(versions, "_probe_tier_cache", {})
    monkeypatch.setattr(versions, "_latest_tier_disabled", lambda: True)
    attempts = []

    def probe(target, *args):
        attempts.append(target)
        return False

    monkeypatch.setattr(versions, "_probe_autoconfig", probe)
    assert versions._probe_tier("example/model", None, "test") == "530"
    assert attempts == [""]


def test_base_transformers_probe_strips_inherited_shadow_paths(monkeypatch, tmp_path):
    import utils.transformers_version as versions

    shadow = str(tmp_path / ".venv_t5_530")
    keep = str(tmp_path / "custom-pythonpath")
    inherited = os.pathsep.join([shadow, keep])
    monkeypatch.setattr(versions, "_VENV_T5_530_DIR", shadow)
    monkeypatch.setenv("PYTHONPATH", inherited)
    captured = []

    def run(*args, **kwargs):
        captured.append(kwargs["env"])
        return SimpleNamespace(returncode = 0, stderr = "")

    monkeypatch.setattr(versions.subprocess, "run", run)
    assert versions._probe_autoconfig("", "example/model", None)
    assert captured[0]["PYTHONPATH"] == keep
    assert os.environ["PYTHONPATH"] == inherited


@pytest.mark.parametrize("tier", ["default", "530"])
def test_export_replaces_older_transformers_even_within_same_major(monkeypatch, tmp_path, tier):
    versions = _base_transformers_metadata(monkeypatch, tmp_path, "5.16.1")
    monkeypatch.setattr(versions, "_is_lora_adapter_dir", lambda path: False)
    monkeypatch.setattr(versions, "_remote_lora_base", lambda model: None)
    monkeypatch.setattr(versions, "get_transformers_tier", lambda model: tier)
    monkeypatch.setattr(versions, "_get_in_memory_version", lambda: "5.3.0")
    deactivated = []
    monkeypatch.setattr(versions, "_deactivate_5x", lambda: deactivated.append(True))

    versions.ensure_transformers_version("example/model")
    assert deactivated == [True]


def _sampler_recipe():
    return {
        "columns": [
            {
                "name": "number",
                "column_type": "sampler",
                "sampler_type": "uniform",
                "params": {"low": 0.0, "high": 1.0},
            }
        ],
        "processors": [
            {
                "name": "copy",
                "processor_type": "schema_transform",
                "template": {"value": "{{ number }}"},
            }
        ],
    }


def test_data_designer_preserves_processors_once_and_application_logging(tmp_path):
    dd = pytest.importorskip("data_designer.config")
    from data_designer.interface import DataDesigner
    from core.data_recipe.service import build_config_builder, create_data_designer

    calls = []
    original = dd.DataDesignerConfigBuilder.add_processor

    def record_processor(self, *args, **kwargs):
        calls.append((args, kwargs))
        return original(self, *args, **kwargs)

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(dd.DataDesignerConfigBuilder, "add_processor", record_processor)
        builder = build_config_builder(_sampler_recipe())
    assert builder is not None
    assert len(calls) == 1
    handlers = list(logging.getLogger().handlers)
    level = logging.getLogger().level
    designer = create_data_designer(_sampler_recipe(), artifact_path = str(tmp_path))
    assert isinstance(designer, DataDesigner)
    assert designer.artifact_path == tmp_path
    assert logging.getLogger().handlers == handlers
    assert logging.getLogger().level == level


def test_data_designer_embedded_metrics_listener_is_opt_in():
    pytest.importorskip("data_designer.config")
    from core.data_recipe.service import build_run_config

    assert build_run_config().otel_metrics_port is None
    assert build_run_config({"buffer_size": 25}).otel_metrics_port is None
    assert build_run_config({"otel_metrics_port": 9465}).otel_metrics_port == 9465


def test_data_designer_sampler_preview_runs_without_model_or_metrics_server():
    pytest.importorskip("data_designer.config")
    from core.data_recipe.service import preview_recipe

    rows, artifacts, analysis = preview_recipe(_sampler_recipe(), num_records = 3)
    assert len(rows) == 3
    assert all(0.0 <= row["number"] <= 1.0 for row in rows)
    assert artifacts is not None
    assert analysis is not None


def test_nullable_numpy_pandas_recipe_values_are_strict_json():
    np = pytest.importorskip("numpy")
    pd = pytest.importorskip("pandas")
    from core.data_recipe.jsonable import to_jsonable

    row = {
        "array": np.array([np.nan, np.inf, 1.0]),
        "missing": pd.NA,
        "date": pd.NaT,
        "scalar": np.float64("-inf"),
        "extended": np.longdouble("1.25"),
    }
    assert json.loads(json.dumps(to_jsonable(row), allow_nan = False)) == {
        "array": [None, None, 1.0],
        "missing": None,
        "date": None,
        "scalar": None,
        "extended": 1.25,
    }


def _trainer_function(name):
    path = BACKEND / "core" / "training" / "trainer.py"
    tree = ast.parse(path.read_text(encoding = "utf-8"))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    return ast.Module(body = [fn], type_ignores = [])


def test_tensorboard_directory_is_per_callback_not_training_arguments(monkeypatch, tmp_path):
    import sys
    from types import ModuleType

    integrations = ModuleType("transformers.integrations")
    callback_type = type("TensorBoardCallback", (), {})
    integrations.TensorBoardCallback = callback_type
    monkeypatch.setitem(sys.modules, "transformers.integrations", integrations)
    namespace = {"resolve_tensorboard_dir": lambda value: tmp_path / value}
    exec(compile(_trainer_function("_configure_tensorboard_callback"), "<trainer>", "exec"), namespace)
    callback = callback_type()
    trainer = SimpleNamespace(callback_handler = SimpleNamespace(callbacks = [callback]))
    namespace["_configure_tensorboard_callback"](
        trainer, {"enable_tensorboard": True, "tensorboard_dir": "metrics"}
    )
    assert callback.logging_dir == str(tmp_path / "metrics")
    namespace["_configure_tensorboard_callback"](trainer, {"enable_tensorboard": False})
    assert callback.logging_dir == str(tmp_path / "metrics")


def test_current_trainer_constructor_names():
    source = (BACKEND / "core" / "training" / "trainer.py").read_text(encoding = "utf-8")
    assert '"max_length": training_args.get("max_seq_length", 2048)' in source
    assert '"max_seq_length": training_args.get("max_seq_length", 2048)' not in source
    assert 'config_args["warmup_ratio"]' not in source
    assert 'config_args["warmup_steps"] = _hf_warmup_ratio(warmup_ratio_val)' in source
    assert '"tokenizer": sft_tokenizer' not in source
    assert 'config_args["logging_dir"]' not in source


def test_real_trl_config_uses_current_transformers_arguments(tmp_path):
    import inspect
    import math

    pytest.importorskip("trl")
    from trl import SFTConfig, SFTTrainer

    config = SFTConfig(
        output_dir = str(tmp_path),
        max_length = 128,
        warmup_steps = math.nextafter(1.0, 0.0),
        use_cpu = True,
        bf16 = False,
        fp16 = False,
        report_to = "none",
    )
    assert config.max_length == 128
    assert config.get_warmup_steps(100) == 100
    assert "processing_class" in inspect.signature(SFTTrainer.__init__).parameters


def test_actual_tensorboard_callback_writes_configured_directory(tmp_path):
    pytest.importorskip("tensorboard")
    from tensorboard.backend.event_processing.event_accumulator import EventAccumulator
    from transformers import TrainerControl, TrainerState, TrainingArguments
    from transformers.integrations import TensorBoardCallback
    from utils.paths import resolve_tensorboard_dir

    callback = TensorBoardCallback()
    trainer = SimpleNamespace(callback_handler = SimpleNamespace(callbacks = [callback]))
    namespace = {"resolve_tensorboard_dir": resolve_tensorboard_dir}
    exec(
        compile(_trainer_function("_configure_tensorboard_callback"), "<trainer>", "exec"),
        namespace,
    )
    namespace["_configure_tensorboard_callback"](
        trainer, {"enable_tensorboard": True, "tensorboard_dir": "integration-events"}
    )
    args = TrainingArguments(
        output_dir = str(tmp_path), use_cpu = True, bf16 = False, fp16 = False,
        report_to = "none",
    )
    state = TrainerState(global_step = 1, is_world_process_zero = True)
    control = TrainerControl()
    callback.on_train_begin(args, state, control)
    callback.on_log(args, state, control, logs = {"loss": 0.5})
    callback.on_train_end(args, state, control)
    events = EventAccumulator(str(resolve_tensorboard_dir("integration-events"))).Reload()
    assert events.Scalars("train/loss")[0].value == 0.5


@pytest.mark.parametrize("text_field", ["text", "content"])
def test_current_trl_cpu_training_step(tmp_path, text_field):
    from dataclasses import replace

    pytest.importorskip("trl")
    import torch
    from datasets import Dataset
    from tokenizers import Tokenizer
    from tokenizers.models import WordLevel
    from tokenizers.pre_tokenizers import Whitespace
    from tokenizers.processors import TemplateProcessing
    from transformers import GPT2Config, GPT2LMHeadModel, PreTrainedTokenizerFast
    from trl import SFTConfig, SFTTrainer
    from utils.datasets.online_tokenization import (
        attach_online_tokenization,
        resolve_add_special_tokens,
    )

    tokenizer = Tokenizer(WordLevel(
        {"[UNK]": 0, "[PAD]": 1, "[EOS]": 2, "hello": 3, "world": 4, "[BOS]": 5},
        unk_token = "[UNK]",
    ))
    tokenizer.pre_tokenizer = Whitespace()
    tokenizer.post_processor = TemplateProcessing(single = "[BOS] $A", special_tokens = [("[BOS]", 5)])
    processing_class = PreTrainedTokenizerFast(
        tokenizer_object = tokenizer, unk_token = "[UNK]", pad_token = "[PAD]",
        eos_token = "[EOS]", bos_token = "[BOS]",
    )
    model = GPT2LMHeadModel(GPT2Config(
        vocab_size = 6, n_positions = 16, n_embd = 16, n_layer = 1, n_head = 1,
        bos_token_id = 5, eos_token_id = 2, pad_token_id = 1,
    ))
    dataset = Dataset.from_dict({
        text_field: ["hello world", "world hello[EOS]", "[BOS]hello", "hello world " * 20],
    })
    trainer = SFTTrainer(
        model = model,
        processing_class = processing_class,
        train_dataset = dataset,
        args = SFTConfig(
            output_dir = str(tmp_path), max_length = 16, max_steps = 1,
            dataset_text_field = text_field,
            per_device_train_batch_size = 1, gradient_checkpointing = False,
            use_cpu = True, fp16 = False, bf16 = False, optim = "adamw_torch",
            report_to = "none", save_strategy = "no", disable_tqdm = True,
        ),
    )
    lazy_dataset = attach_online_tokenization(
        dataset, tokenizer = processing_class, text_field = text_field, max_length = 16,
        add_special_tokens = resolve_add_special_tokens(processing_class, dataset[0][text_field]),
    )
    for eager, lazy in zip(trainer.train_dataset, lazy_dataset):
        assert lazy["input_ids"] == eager["input_ids"]
        assert lazy["labels"] == eager["labels"]
    lazy_trainer = SFTTrainer(
        model = model,
        processing_class = processing_class,
        train_dataset = lazy_dataset,
        args = replace(
            trainer.args,
            dataset_kwargs = {"skip_prepare_dataset": True},
            remove_unused_columns = False,
        ),
    )
    eager_batch = trainer.data_collator(list(trainer.train_dataset))
    lazy_batch = lazy_trainer.data_collator(list(lazy_dataset))
    assert eager_batch.keys() == lazy_batch.keys()
    for key in eager_batch:
        torch.testing.assert_close(lazy_batch[key], eager_batch[key])
    result = lazy_trainer.train()
    assert result.global_step == 1
    assert result.training_loss > 0


def test_sentence_transformer_six_training_arguments(tmp_path):
    pytest.importorskip("sentence_transformers")
    from sentence_transformers import SentenceTransformerTrainingArguments
    from sentence_transformers.training_args import BatchSamplers

    args = SentenceTransformerTrainingArguments(
        output_dir = str(tmp_path), use_cpu = True, bf16 = False, fp16 = False,
        warmup_steps = 0.03, batch_sampler = BatchSamplers.NO_DUPLICATES, report_to = "none",
    )
    assert args.get_warmup_steps(100) == 3


def test_pydantic_data_recipe_models_resolve_annotations():
    from models.data_recipe import RecipePayload

    schema = RecipePayload.model_json_schema()
    assert schema["type"] == "object"


@pytest.mark.parametrize("ratio", [0.0, 0.03, 0.5, 1.0])
@pytest.mark.parametrize("steps", [1, 100, 1_000_000])
def test_warmup_ratio_preserves_hf5_step_semantics(ratio, steps):
    import math

    namespace = {"math": math}
    exec(compile(_trainer_function("_hf_warmup_ratio"), "<trainer>", "exec"), namespace)
    warmup = namespace["_hf_warmup_ratio"](ratio)
    actual = int(warmup) if warmup >= 1 else math.ceil(steps * warmup)
    assert actual == math.ceil(steps * ratio)


def _text_length(row):
    return {"length": len(row["text"])}


def test_datasets_five_parallel_map_and_arrow_roundtrip(tmp_path):
    datasets = pytest.importorskip("datasets")
    dataset = datasets.Dataset.from_dict({"text": ["one", "two", "three", "four"]})
    mapped = dataset.map(
        _text_length, num_proc = 2, keep_in_memory = True, load_from_cache_file = False
    )
    assert list(mapped["length"]) == [3, 3, 5, 4]
    mapped.save_to_disk(str(tmp_path / "dataset"))
    restored = datasets.load_from_disk(str(tmp_path / "dataset"))
    assert restored.to_dict() == mapped.to_dict()


def test_seed_plugins_use_current_reader_attachment(monkeypatch, tmp_path):
    pytest.importorskip("data_designer.engine.resources.seed_reader")
    from data_designer.engine.secret_resolver import PlaintextResolver
    from core.data_recipe.service import build_config_builder

    for plugin in ("data-designer-unstructured-seed", "data-designer-github-repo-seed"):
        monkeypatch.syspath_prepend(str(BACKEND / "plugins" / plugin / "src"))
    from data_designer_unstructured_seed.config import UnstructuredSeedSource
    from data_designer_unstructured_seed.impl import UnstructuredSeedReader
    from data_designer_unstructured_seed import chunking
    from data_designer_github_repo_seed.config import GitHubRepoSeedSource
    from data_designer_github_repo_seed.impl import GitHubRepoSeedReader

    monkeypatch.setattr(chunking, "_CACHE_DIR", tmp_path / "chunks")
    path = tmp_path / "source.txt"
    path.write_text("One useful seed document.", encoding = "utf-8")
    source = UnstructuredSeedSource(paths = [str(path)])
    reader = UnstructuredSeedReader()
    reader.attach(source, PlaintextResolver())
    assert Path(reader.get_dataset_uri()).is_file()
    github_source = GitHubRepoSeedSource(repos = ["owner/repository"])
    github_reader = GitHubRepoSeedReader()
    github_reader.attach(github_source, PlaintextResolver())
    assert github_reader.source.repos == ["owner/repository"]
    for registered_source in (source, github_source):
        builder = build_config_builder({
            "seed_config": {"source": registered_source.model_dump(mode = "json")},
            "columns": [{"column_type": "expression", "name": "x", "expr": "1"}],
        })
        assert builder is not None


@pytest.mark.parametrize(
    "first_import",
    [
        "data_designer.engine.resources.seed_reader",
        "data_designer.config",
        "data_designer_unstructured_seed",
    ],
)
def test_installed_seed_plugins_register_regardless_of_import_order(tmp_path, first_import):
    pytest.importorskip("data_designer")
    document = tmp_path / "seed.txt"
    document.write_text("A local seed document.", encoding = "utf-8")
    script = """
import importlib
import sys
importlib.import_module(sys.argv[1])
if sys.argv[1] == "data_designer_unstructured_seed":
    assert "data_designer.engine.resources.seed_reader" not in sys.modules
from core.data_recipe.service import build_config_builder
for source in (
    {"seed_type": "unstructured", "paths": [sys.argv[2]]},
    {"seed_type": "github_repo", "repos": ["owner/repository"]},
):
    assert build_config_builder({
        "seed_config": {"source": source},
        "columns": [{"column_type": "expression", "name": "x", "expr": "1"}],
    }) is not None
from data_designer_unstructured_seed import UnstructuredSeedReader, resolve_chunking
assert callable(UnstructuredSeedReader) and callable(resolve_chunking)
"""
    result = subprocess.run(
        [sys.executable, "-X", "utf8", "-c", script, first_import, str(document)],
        cwd = BACKEND,
        env = {**os.environ, "UNSLOTH_STUDIO_HOME": str(tmp_path / "studio")},
        capture_output = True,
        text = True,
        encoding = "utf-8",
        timeout = 60,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr


def test_fixed_sidecars_cannot_downgrade_the_supported_transformers():
    tree = ast.parse(
        (BACKEND / "utils" / "transformers_version.py").read_text(encoding = "utf-8")
    )
    selected = [
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name)
            and (
                target.id.startswith("TRANSFORMERS_")
                or target.id in {
                    "_VENV_T5_530_PACKAGES", "_VENV_T5_550_PACKAGES", "_VENV_T5_510_PACKAGES"
                }
            )
            for target in node.targets
        )
    ]
    namespace = {}
    exec(compile(ast.Module(body = selected, type_ignores = []), "<sidecars>", "exec"), namespace)
    for tier in ("530", "550", "510"):
        packages = namespace[f"_VENV_T5_{tier}_PACKAGES"]
        assert "transformers==5.16.1" in packages
        assert "tokenizers==0.23.2" in packages
        assert "huggingface_hub==1.30.0" in packages


def test_compressor_never_installs_an_unsupported_torch_shadow(monkeypatch):
    tree = ast.parse(
        (BACKEND / "utils" / "transformers_version.py").read_text(encoding = "utf-8")
    )
    fn = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_ensure_venv_llmcompressor_exists"
    )
    messages = []
    namespace = {"logger": SimpleNamespace(error = lambda *args: messages.append(args))}
    monkeypatch.setattr(importlib.metadata, "version", lambda name: "2.14.0")
    exec(compile(ast.Module(body = [fn], type_ignores = []), "<compressor>", "exec"), namespace)
    assert namespace["_ensure_venv_llmcompressor_exists"]() is False
    assert "torch<=2.13.0" in messages[0][0]
