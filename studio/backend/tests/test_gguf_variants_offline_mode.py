# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2026-present the Unsloth AI Inc. team. All rights reserved. See /studio/LICENSE.AGPL-3.0

"""Environment offline mode must use the same cache-only contract as the query flag."""

import asyncio

import pytest
from fastapi import HTTPException

from hub.services.models import gguf_variants
from hub.utils.gguf import GgufVariantInfo


@pytest.fixture
def isolated_variant_cache(monkeypatch, tmp_path):
    for name in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE"):
        monkeypatch.delenv(name, raising = False)
    root = tmp_path / "hub" / "models--qa--offline-GGUF"
    monkeypatch.setattr(
        gguf_variants, "_repo_cache_dir_for_request", lambda *args: root
    )
    monkeypatch.setattr(gguf_variants, "_snapshot_scope_for_request", lambda *args: None)
    monkeypatch.setattr(gguf_variants, "_quants_from_state", lambda *args: None)
    monkeypatch.setattr(
        gguf_variants, "_mark_empty_dir_cleanables", lambda repo, response, root: response
    )
    return root


@pytest.mark.parametrize(
    ("source", "value"),
    [
        ("query", None),
        ("HF_HUB_OFFLINE", "1"),
        ("HF_HUB_OFFLINE", " yes "),
        ("TRANSFORMERS_OFFLINE", "on"),
    ],
)
@pytest.mark.parametrize("cache_available", [False, True])
@pytest.mark.parametrize("anonymous", [False, True])
def test_offline_variants_never_probe_the_hub(
    monkeypatch, isolated_variant_cache, source, value, cache_available, anonymous
):
    if value is not None:
        monkeypatch.setenv(source, value)
    snapshot = isolated_variant_cache / "snapshots" / "revision"
    variant = GgufVariantInfo(
        filename = "model-Q4_K_M.gguf", quant = "Q4_K_M", size_bytes = 32
    )
    cached = ([variant], False, {"Q4_K_M"}, snapshot) if cache_available else None
    cache_reads = []
    remote_calls = []

    def read_cache(*args, **kwargs):
        cache_reads.append(True)
        return cached

    def remote(*args, **kwargs):
        remote_calls.append(True)
        raise AssertionError("Offline GGUF requests must never probe the Hub")

    monkeypatch.setattr(gguf_variants, "select_gguf_cache_snapshot", read_cache)
    monkeypatch.setattr(gguf_variants, "list_gguf_variants", remote)
    request = gguf_variants.get_gguf_variants_response(
        "qa/offline-GGUF",
        offline = source == "query",
        hf_token = False if anonymous else None,
    )
    if cache_available and not anonymous:
        response = asyncio.run(request)
        assert len(response.variants) == 1
        assert response.variants[0].quant == "Q4_K_M"
        assert response.variants[0].downloaded is True
    else:
        with pytest.raises(HTTPException) as raised:
            asyncio.run(request)
        assert raised.value.status_code == 404
        assert raised.value.detail == "No cached GGUF variants available while offline."
    assert not remote_calls
    assert bool(cache_reads) is not anonymous


@pytest.mark.parametrize("value", ["0", "false", "off"])
def test_online_variants_keep_runtime_failures_visible(
    monkeypatch, isolated_variant_cache, value
):
    monkeypatch.setenv("HF_HUB_OFFLINE", value)
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", value)
    monkeypatch.setattr(
        gguf_variants, "select_gguf_cache_snapshot", lambda *args, **kwargs: None
    )
    remote_calls = []

    def remote(*args, **kwargs):
        remote_calls.append(True)
        raise RuntimeError("synthetic metadata failure")

    monkeypatch.setattr(gguf_variants, "list_gguf_variants", remote)
    with pytest.raises(HTTPException) as raised:
        asyncio.run(gguf_variants.get_gguf_variants_response("qa/offline-GGUF"))
    assert raised.value.status_code == 500
    assert "synthetic metadata failure" in raised.value.detail
    assert remote_calls == [True]
