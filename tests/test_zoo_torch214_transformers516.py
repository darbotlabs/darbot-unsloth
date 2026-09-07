"""Executable regressions for the maintained Zoo's changed upstream APIs."""

import ast
import functools
from pathlib import Path
from types import SimpleNamespace
from typing import Optional

import pytest


ROOT = Path(__file__).resolve().parents[1]
ZOO = ROOT / "studio" / "backend" / "vendor" / "unsloth_zoo_compat" / "unsloth_zoo"


def test_unsloth_training_arguments_accept_current_sft_names(tmp_path):
    from trl import SFTConfig

    source = ROOT / "unsloth" / "trainer.py"
    tree = ast.parse(source.read_text(encoding = "utf-8"))
    definition = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "UnslothTrainingArguments"
    )
    namespace = {"TrainingArguments": SFTConfig, "Optional": Optional, "QGaloreConfig": object}
    exec(compile(ast.Module(body = [definition], type_ignores = []), str(source), "exec"), namespace)
    config = namespace["UnslothTrainingArguments"](
        output_dir = str(tmp_path),
        max_length = 32,
        warmup_steps = 0.1,
        embedding_learning_rate = 5e-5,
        use_cpu = True,
        bf16 = False,
        report_to = "none",
    )
    assert config.max_length == 32
    assert config.warmup_steps == 0.1
    assert config.embedding_learning_rate == 5e-5


def test_unsloth_embedding_optimizer_passes_model_to_transformers(monkeypatch, tmp_path):
    torch = pytest.importorskip("torch")
    from trl import SFTConfig, SFTTrainer

    source = ROOT / "unsloth" / "trainer.py"
    tree = ast.parse(source.read_text(encoding = "utf-8"))
    trainer = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "UnslothTrainer"
    )
    method = next(
        node
        for node in trainer.body
        if isinstance(node, ast.FunctionDef) and node.name == "create_optimizer"
    )
    helper = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_create_unsloth_optimizer"
    )
    namespace = {"SFTTrainer": SFTTrainer}
    exec(
        compile(ast.Module(body = [helper, method], type_ignores = []), str(source), "exec"), namespace
    )
    config = SFTConfig(
        output_dir = str(tmp_path), use_cpu = True, bf16 = False, report_to = "none", optim = "adamw_torch"
    )
    config.embedding_learning_rate = 5e-5
    model = torch.nn.Linear(2, 2)
    original = SFTTrainer.get_optimizer_cls_and_kwargs
    calls = []

    def optimizer_factory(args, passed_model):
        calls.append(passed_model)
        return original(args, passed_model)

    monkeypatch.setattr(SFTTrainer, "get_optimizer_cls_and_kwargs", staticmethod(optimizer_factory))
    instance = SimpleNamespace(args = config, model = model, optimizer = None)
    optimizer = namespace["create_optimizer"](instance)
    assert calls == [model]
    assert optimizer is instance.optimizer


def test_worker_initializer_binds_current_transformers_signature():
    torch = pytest.importorskip("torch")
    from transformers.trainer_utils import seed_worker

    source = ZOO / "training_utils.py"
    tree = ast.parse(source.read_text(encoding = "utf-8"))
    initializer = next(
        keyword.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        for keyword in node.keywords
        if keyword.arg == "worker_init_fn"
    )
    callback = eval(
        compile(ast.Expression(initializer), str(source), "eval"),
        {
            "functools": functools,
            "trainer_utils_seed_worker": seed_worker,
            "training_args": SimpleNamespace(dataloader_num_workers = 2, process_index = 3),
        },
    )
    state = torch.random.get_rng_state()
    try:
        callback(0)
    finally:
        torch.random.set_rng_state(state)
    assert callback.keywords == {"num_workers": 2, "rank": 3}


def test_disabled_dynamo_never_enters_a_fullgraph_wrapper(monkeypatch):
    torch = pytest.importorskip("torch")
    import unsloth_zoo.temporary_patches.utils as utils

    def compiler(function, **kwargs):
        def forbidden(*args, **kwargs):
            raise RuntimeError("torch.compile with fullgraph=True found no compiled frames.")

        return forbidden

    monkeypatch.setattr(torch, "compile", compiler)
    function = utils.torch_compile_with_fallback(fullgraph = True)(lambda value: value.square().sum())
    value = torch.tensor([2.0, 3.0], requires_grad = True)
    with torch._dynamo.config.patch(disable = True):
        result = function(value)
        result.backward()
    assert result.item() == 13.0
    assert value.grad.tolist() == [4.0, 6.0]
