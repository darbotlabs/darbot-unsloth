---
title: Data recipes & local plugins
description: Use the Studio Data Designer integration to validate, generate, inspect, and retain datasets with clear source, provider, and worker boundaries.
---

Data recipes are Studio's dataset-construction workflow. They use **Data Designer 0.9.2**, its matching config and engine packages, and local plugins. Recipe jobs are distinct from GPU training jobs.

## A deliberate recipe workflow

1. Choose source material you are authorized to process: a supported dataset, document upload, or repository seed.
2. Configure fields, transformations, generation/provider settings, and validation.
3. Validate the recipe before launching a large generation job.
4. Run a small sample and inspect actual rows, missing values, document extraction, and model-generated content.
5. Save or locate the resulting dataset and preview its training format.
6. Only then start a [training run](training.md), with an explicit evaluation plan.

A structurally valid recipe does not guarantee correct, representative, or non-sensitive output. Generated examples still need quality checks.

## Dependency boundaries

The direct requirements union is installed with normal dependency resolution under shared constraints. The three Data Designer packages and local plugins are installed through the controlled installer phases; that is not permission to install an incomplete graph using arbitrary `--no-deps` commands.

Data Designer's genuine requirements explain several [compatibility exceptions](dependency-matrix.md): pandas 2.3.3, Arrow 24, Rich 14.3.4, Click 8.4.2, and the MCP 1.x-compatible FastMCP 3.4.7 line.

The runtime is available to the true GGUF-only application profile without adding Zoo, Torch, or compiler providers. "Torch-free" does not mean that external generation providers are automatically offline.

## Local plugins and validation

The repository contains **GitHub repository seed** and **unstructured seed** plugins. The latter's name does not imply installing the unrelated PyPI `unstructured` distribution. Document extraction dependencies and their platform markers are listed in the maintained direct-runtime requirements.

Local callable validation includes an OXC-based JavaScript validator with its own package manifest. Keep that Node helper distinct from the main frontend and from the documentation website.

## Jobs, artifacts, and privacy

Recipe work runs through dedicated job-manager/worker code and exposes status/output APIs under `/api/data-recipe`. Outputs live under Studio's recipe-dataset storage, not in the Git checkout by default. See [data roots](storage.md).

Repository seeds, uploaded PDFs/DOCX/CSV data, prompt templates, provider responses, and validation logs may contain confidential information. A local recipe UI does not guarantee its configured provider or source fetch remains local. Review network destinations and retain only the data needed for the task.

**Sources:** [recipe routes](https://github.com/darbotlabs/darbot-unsloth/tree/main/studio/backend/routes/data_recipe), [service](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/backend/core/data_recipe/service.py), [job manager](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/backend/core/data_recipe/jobs/manager.py), [plugins](https://github.com/darbotlabs/darbot-unsloth/tree/main/studio/backend/plugins), [direct runtime union](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/backend/requirements/single-env/data-designer-deps.txt).
