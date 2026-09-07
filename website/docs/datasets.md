---
title: Datasets & TRL 1.12 semantics
description: Prepare datasets 5 inputs while preserving completion masks, assistant masks, labels, packing boundaries, and multiprocessing behavior in TRL 1.12.
---

This stack uses **datasets 5.0.1** and **TRL 1.12.0**. Compatibility requires real preparation and trainer API changes; widening a version cap cannot preserve training semantics by itself.

## Choose a stable input

For an initial text run, use a small dataset with a `text` column and inspect the actual formatted strings. Conversational data needs the intended model chat template; raw text, prompt/completion pairs, and multimodal rows are not interchangeable.

Studio's training schema supports Hub dataset selection, local datasets, evaluation datasets, split/config selection, optional streaming, and bounded row slices. A local path must be a valid readable dataset source; a Hub name must be a valid identifier. Model and dataset authentication are separate from rights to train on the content.

Avoid relying on a huge preprocessing pass to discover a formatting mistake. Preview rows and token boundaries first.

## Masking is part of correctness

Modern preparation must preserve:

- `input_ids` and their alignment with `labels`;
- `completion_mask` for completion-only loss;
- `assistant_masks` when assistant-only supervision is involved;
- masked label values of **`-100`**, which exclude tokens from loss;
- per-sequence boundaries such as `seq_lengths` when packing.

For example, token IDs `[1, 2, 3, 4]` with completion mask `[0, 0, 1, 1]` and assistant mask `[0, 0, 1, 0]` must retain labels `[-100, -100, 3, -100]` in the exercised preparation path. Replacing a collator or rebuilding labels indiscriminately can silently train on the wrong tokens.

The integration tests run the real TRL preparation pipeline, including packed and unpacked cases. The maintained Zoo helper packs existing labels without replacing the caller's collator.

## Current trainer API

Use `SFTConfig` for training/preparation configuration and pass the tokenizer or appropriate processor through `processing_class`. `max_length` belongs to the TRL config; Studio maps its user-facing `max_seq_length` into that contract.

Packing and padding-free execution are separate decisions. Do not enable either simply to silence an error. Pre-tokenized rows, truncation limits, a model's attention implementation, and the collator must agree. The fork also handles TRL's chunked-loss interaction with model forward paths.

## Multiprocessing and streaming

Spawn-based dataset map calls are normalized safely rather than blindly forcing a requested worker count. The integration test checks that the caller's `dataset_num_proc` configuration is not mutated. Formatting functions operate on the expected **individual examples**, not accidentally on column batches.

Custom `with_transform` datasets retain the modern TRL rejection rather than being silently accepted with altered semantics. Streaming uses plain split names; do not combine it with unsupported Hub slice syntax.

For step-bounded Studio runs, the row-bound helper limits unnecessary preprocessing while recording resume context. `max_steps` alone does not make the TRL constructor tokenize only the rows training will consume.

**Sources:** [real TRL integration tests](https://github.com/darbotlabs/darbot-unsloth/blob/main/tests/test_trl112_dataset_integration.py), [preparation rewrites](https://github.com/darbotlabs/darbot-unsloth/blob/main/unsloth/models/rl_replacements.py), [dataset bounds](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/backend/core/training/dataset_bounds.py), [training schema](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/backend/models/training.py).
