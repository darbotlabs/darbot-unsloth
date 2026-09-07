# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2026-present the Unsloth AI Inc. team. All rights reserved. See /studio/LICENSE.AGPL-3.0

from core.data_recipe.jobs.constants import STAGE_SAMPLING
from core.data_recipe.jobs.parse import apply_update, parse_log_message
from core.data_recipe.jobs.types import Job
import pytest


def test_current_sampling_log_sets_stage_and_rows():
    # data-designer's current phrasing (seen in issue #5848 logs). Without this
    # the sampling stage never fires and the row total used for overall progress
    # is lost. The legacy "Preparing samplers ..." line is covered below.
    update = parse_log_message("🌱 Sampling 25 records from seed dataset")

    assert update is not None
    assert update.stage == STAGE_SAMPLING
    assert update.rows == 25

    job = Job(job_id = "job-1")
    apply_update(job, update)
    assert job.stage == STAGE_SAMPLING
    assert job.rows == 25


def test_legacy_sampling_log_still_parsed():
    update = parse_log_message("Preparing samplers to generate 50 records across 3 columns")

    assert update is not None
    assert update.stage == STAGE_SAMPLING
    assert update.rows == 50
    assert update.cols == 3


@pytest.mark.parametrize("label", ["response", "LLM_TEXT column 'response'"])
def test_data_designer_async_column_progress(label):
    update = parse_log_message(f"    |-- ⏳ {label}: 5/10 (50%) 2.5 rec/s, 1 skipped")
    assert update.current_column == "response"
    assert update.rows == 10
    assert update.progress.done == 5
    assert update.progress.eta_sec == 2.0
    assert update.progress.ok is None
    assert update.progress.failed is None


def test_async_progress_uses_all_scheduled_columns_not_only_llm_columns():
    job = Job(job_id = "async", progress_columns_total = 1)
    update = parse_log_message("⚡ Async generation: 2 column(s) (seed, response), 20 tasks across 1 row group(s)")
    apply_update(job, update)
    assert job.progress_columns_total == 2
    apply_update(job, parse_log_message("    |-- ✅ seed: 10/10 (100%) 2.5 rec/s"))
    assert job.progress.percent == 50.0
    apply_update(job, parse_log_message("    |-- ✅ response: 10/10 (100%) 2.5 rec/s"))
    assert job.progress.percent == 100.0
    assert job.completed_columns == ["seed", "response"]


def test_legacy_progress_with_skipped_rows_and_unknown_eta():
    update = parse_log_message(
        "response progress: 0/10 (0%) complete, 0 ok, 0 failed, 1 skipped, 0.00 rec/s, eta unknown"
    )
    assert update.progress.done == 0
    assert update.progress.eta_sec is None
