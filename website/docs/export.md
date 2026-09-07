---
title: Saving, quantization & export
description: Distinguish adapters, merged models, GGUF, and compressed FP8/FP4 export, including the current LLMCompressor compatibility block.
---

A successful training run does not automatically produce every deployment format. Saving adapters, merging base weights, converting to GGUF, and compressing a Hugging Face checkpoint are separate operations with separate requirements.

## Choose the artifact you need

| Artifact | Meaning | Important dependency |
| --- | --- | --- |
| LoRA adapter | Trainable changes plus adapter configuration | Original compatible base model still required |
| Merged/uncompressed model | Base and trained changes in a supported full-model representation | Enough RAM/VRAM/disk for loading and merging |
| GGUF | Native-inference representation with a selected quantization/conversion path | Model architecture and native converter support |
| HF FP8/FP4 compressed-tensors | Specialized compressed export, not GGUF and not 4-bit QLoRA training | Compatible LLMCompressor, compressed-tensors, framework, and hardware stack |

Save the tokenizer/processor alongside the adapter or model when required. Record the base model identity, revision, training configuration, and format. For an adapter, test reload against the intended base and compare representative logits or outputs.

## Studio flow

Load the desired checkpoint in the export workflow, choose an actually supported output format, set a safe output destination, and monitor status/logs. Export runs through its own orchestrator/worker and may allocate substantial resources.

The HTTP registration uses `/api/export`; operation paths include `/load-checkpoint`, `/status`, and `/export/gguf` under that prefix. Use the [live API schema](api.md) instead of guessing shorter route names.

Do not overwrite your only trained checkpoint. Keep sufficient disk headroom for intermediate files and validate the result with its target inference runtime before publishing it.

## Incremental Hub uploads

The maintained Zoo companion preserves repository IDs and revisions as literal
values when generating incremental-save code. A revision such as `main`,
`refs/heads/topic`, or a commit SHA is passed to the Hub uploader as a string,
not interpreted as a Python expression. Quoting and whitespace are preserved;
the Hub still validates whether those values name an acceptable repository or
revision.

## Current compressed-export block

Stable **LLMCompressor 0.13.0** and **compressed-tensors 0.18** do not satisfy this fork's Torch 2.14 stack. Their relevant published ceilings include:

- Torch **2.13.0**;
- Transformers **5.14.1**;
- NumPy **2.4.6**.

The fork deliberately blocks that incompatible FP8/FP4 compressed-export path rather than silently downgrading Torch, replacing framework packages, or falsifying metadata. A visible format label or NVIDIA GPU is not proof that the current compressor is usable.

**This does not block GGUF, uncompressed saving, or 4-bit QLoRA training.** Those are different capabilities. TorchAO-specific formats also need their own model/device validation; do not treat them as equivalent compressor qualification.

## Sharing responsibly

Check the base model license, adapter redistribution terms, and dataset provenance. Exports can retain sensitive learned behavior or metadata. Keep access credentials and private source data out of output archives and public model cards.

**Sources:** [export routes](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/backend/routes/export.py), [export implementation](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/backend/core/export/export.py), [compressor compatibility gate](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/backend/utils/transformers_version.py), [capability tests](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/backend/tests/test_export_capability.py).
