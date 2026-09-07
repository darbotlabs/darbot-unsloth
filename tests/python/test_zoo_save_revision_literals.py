# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2026-present the Unsloth AI Inc. team. All rights reserved.
"""Exercise bundled Zoo's source generator without models, files or Hub access."""

import ast
from pathlib import Path
import re
from types import SimpleNamespace

import pytest


SOURCE = (
    Path(__file__).resolve().parents[2]
    / "studio" / "backend" / "vendor" / "unsloth_zoo_compat"
    / "unsloth_zoo" / "saving_utils.py"
)
SAVE_METHOD = """\
def save_pretrained(self, save_directory, filename_to_tensors, token=None):
    os.makedirs(save_directory, exist_ok=True)
    for shard_file, tensors in filename_to_tensors:
        shard = {tensor: tensor for tensor in tensors}
        saved.append(shard)
    return save_directory
"""
HUB_VALUES = [
    ("org/model", None),
    ("org/model", ""),
    ("org/model", "main"),
    ("org/model", "refs/heads/topic"),
    ("org/model", "a" * 40),
    ("org/model's", "branch's\nname"),
    ("org/with        spaces", r"refs\heads\with        spaces"),
]


@pytest.fixture(scope = "module")
def generate():
    tree = ast.parse(SOURCE.read_text(encoding = "utf-8"))
    template = next(
        node for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "_PUSHING_CODE" for target in node.targets)
    )
    function = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "incremental_save_pretrained"
    )
    namespace = {"re": re, "_PUSHING_CODE": ast.literal_eval(template.value)}
    exec(compile(ast.Module(body = [function], type_ignores = []), str(SOURCE), "exec"), namespace)
    return namespace["incremental_save_pretrained"]


@pytest.mark.parametrize(("repo_id", "revision"), HUB_VALUES)
@pytest.mark.parametrize("use_temp_file", [False, True])
def test_generated_save_preserves_hub_literals(generate, repo_id, revision, use_temp_file):
    generated = generate(
        SAVE_METHOD, repo_id = repo_id, revision = revision, use_temp_file = use_temp_file
    )
    tree = ast.parse(generated)
    upload = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        and node.func.attr == "_upload_modified_files"
    )
    keywords = {keyword.arg: ast.literal_eval(keyword.value) for keyword in upload.keywords
                if keyword.arg in ("repo_id", "revision")}
    assert keywords == {"repo_id": repo_id, "revision": revision}
    assignment = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "repo_id" for target in node.targets)
    )
    assert ast.literal_eval(assignment.value) == repo_id


@pytest.mark.parametrize(("repo_id", "revision"), HUB_VALUES)
@pytest.mark.parametrize("use_temp_file", [False, True])
def test_generated_save_passes_exact_values_to_uploader(generate, repo_id, revision, use_temp_file):
    calls = []
    hub = SimpleNamespace(
        _get_files_timestamps = lambda *args: {},
        _upload_modified_files = lambda *args, **kwargs: calls.append(kwargs),
    )
    namespace = {
        "os": SimpleNamespace(makedirs = lambda *args, **kwargs: None),
        "shutil": SimpleNamespace(rmtree = lambda *args: None),
        "tempfile": SimpleNamespace(
            TemporaryDirectory = lambda **kwargs: SimpleNamespace(
                name = "synthetic-temp", cleanup = lambda: None
            ),
        ),
        "PushToHubMixin": hub,
        "saved": [],
        "DEQUANTIZED_KEYS": [],
    }
    generated = generate(
        SAVE_METHOD, repo_id = repo_id, revision = revision, use_temp_file = use_temp_file
    )
    exec(compile(generated, "<generated-save>", "exec"), namespace)
    namespace["save_pretrained"](hub, "synthetic-output", [("shard", ["weight"])], token = "test")
    assert len(calls) == 1
    assert calls[0]["repo_id"] == repo_id
    assert calls[0]["revision"] == revision
    assert calls[0]["token"] == "test"


@pytest.mark.parametrize("use_temp_file", [False, True])
def test_non_incremental_save_does_not_add_uploads(generate, use_temp_file):
    generated = generate(
        SAVE_METHOD, low_disk_space_usage = False, use_temp_file = use_temp_file,
        repo_id = "org/model", revision = "refs/heads/topic",
    )
    tree = ast.parse(generated)
    assert not any(
        isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        and node.func.attr == "_upload_modified_files"
        for node in ast.walk(tree)
    )
    assert "ProgressBar(filename_to_tensors" in generated
