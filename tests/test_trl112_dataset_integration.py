"""Exercise the actual TRL 1.x preparation pipeline with datasets 5, not stubs."""

import ast
import importlib.util
import inspect
from pathlib import Path
import re
import sys
import textwrap
from types import SimpleNamespace

from packaging.version import Version
import pytest


ROOT = Path(__file__).resolve().parents[1]


def modern_prepare(monkeypatch):
    trl = pytest.importorskip("trl")
    if Version(trl.__version__) < Version("1.12.0"):
        pytest.skip("Requires TRL 1.12's label preparation contract")
    from trl import SFTTrainer

    source = ROOT / "unsloth" / "models" / "rl_replacements.py"
    tree = ast.parse(source.read_text(encoding = "utf-8"))
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "sft_trainer_prepare_dataset"
    )
    namespace = {"re": re, "Version": Version, "trl_version": Version(trl.__version__)}
    exec(compile(ast.Module(body = [function], type_ignores = []), str(source), "exec"), namespace)
    rewritten = namespace["sft_trainer_prepare_dataset"](
        "_prepare_dataset",
        inspect.getsource(SFTTrainer._prepare_dataset),
    )
    globals_ = dict(SFTTrainer._prepare_dataset.__globals__)
    exec(compile(textwrap.dedent(rewritten), "<modern-sft-prepare>", "exec"), globals_)
    policy_path = ROOT / "unsloth" / "dataset_num_proc.py"
    spec = importlib.util.spec_from_file_location("unsloth_zoo.dataset_num_proc", policy_path)
    policy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(policy)
    monkeypatch.setitem(sys.modules, "unsloth_zoo.dataset_num_proc", policy)
    monkeypatch.setattr(policy, "multiprocessing_start_method", lambda: "spawn")
    return globals_["_prepare_dataset"]


@pytest.mark.parametrize("packing", [False, True])
def test_modern_preparation_preserves_masked_labels_and_serial_maps(monkeypatch, packing):
    datasets = pytest.importorskip("datasets")
    prepare = modern_prepare(monkeypatch)
    dataset = datasets.Dataset.from_dict(
        {
            "input_ids": [[1, 2, 3, 4], [5, 6, 7]],
            "completion_mask": [[0, 0, 1, 1], [0, 1, 1]],
            "assistant_masks": [[0, 0, 1, 0], [0, 1, 1]],
        }
    )
    map_calls = []
    original_map = datasets.Dataset.map

    def checked_map(self, *args, **kwargs):
        map_calls.append(kwargs.get("num_proc"))
        return original_map(self, *args, **kwargs)

    monkeypatch.setattr(datasets.Dataset, "map", checked_map)
    config = SimpleNamespace(
        dataset_num_proc = 8,
        max_length = 4,
        packing_strategy = "bfd",
        truncation_mode = "keep_start",
        shuffle_dataset = False,
        use_liger_kernel = False,
    )
    result = prepare(
        SimpleNamespace(completion_only_loss = True),
        dataset,
        None,
        config,
        packing,
        None,
        "train",
    )
    assert list(result["labels"]) == [[-100, -100, 3, -100], [-100, 6, 7]]
    assert map_calls and all(value is None for value in map_calls)
    assert config.dataset_num_proc == 8, "worker normalization must not mutate the caller's config"
    if packing:
        assert list(result["seq_lengths"]) == [[4], [3]]


def test_modern_preparation_keeps_custom_transform_rejection(monkeypatch):
    datasets = pytest.importorskip("datasets")
    prepare = modern_prepare(monkeypatch)
    dataset = datasets.Dataset.from_dict({"input_ids": [[1, 2]]}).with_transform(
        lambda batch: batch
    )
    with pytest.raises(ValueError, match = "with_transform"):
        prepare(
            SimpleNamespace(),
            dataset,
            None,
            SimpleNamespace(dataset_num_proc = 8, max_length = None),
            False,
            None,
            "train",
        )


def test_vendored_helper_packs_labels_without_replacing_the_collator():
    datasets = pytest.importorskip("datasets")
    from unsloth_zoo.dataset_utils import sft_prepare_dataset

    collator = object()
    trainer = SimpleNamespace(data_collator = collator)
    dataset = datasets.Dataset.from_dict(
        {
            "input_ids": [[1, 2], [3, 4]],
            "labels": [[-100, 2], [-100, 4]],
        }
    )
    config = SimpleNamespace(max_length = 4, dataset_num_proc = 1, packing_strategy = "bfd")
    result = sft_prepare_dataset(trainer, dataset, SimpleNamespace(), config, True, None, "train")
    assert list(result["input_ids"]) == [[1, 2, 3, 4]]
    assert list(result["labels"]) == [[-100, 2, -100, 4]]
    assert trainer.data_collator is collator


def test_vendored_helper_formats_individual_examples_not_column_batches():
    datasets = pytest.importorskip("datasets")
    from unsloth_zoo.dataset_utils import sft_prepare_dataset

    class Tokenizer:
        def __call__(self, texts, **kwargs):
            assert all(isinstance(text, str) for text in texts)
            return {"input_ids": [[len(text)] for text in texts]}

    dataset = datasets.Dataset.from_dict({"value": ["a", "abcd"]})
    config = SimpleNamespace(max_length = 8, dataset_num_proc = 1)
    result = sft_prepare_dataset(
        SimpleNamespace(data_collator = object()),
        dataset,
        Tokenizer(),
        config,
        False,
        lambda example: example["value"] + "!",
        "train",
    )
    assert list(result["input_ids"]) == [[2], [5]]
