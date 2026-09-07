---
title: LoRA & QLoRA training
description: Configure a small adapter-training run, distinguish LoRA from packed 4-bit QLoRA, and validate changed weights plus save/reload behavior.
---

**LoRA** trains low-rank adapter weights attached to a base model. **QLoRA** combines adapter training with a quantized base; here, genuine 4-bit qualification checks packed CUDA `Linear4bit` weights, not merely a configuration flag.

## Before a run

- Install a full compatible ML profile, including the matching Zoo companion.
- Choose a model whose architecture, license, precision, and memory needs fit the actual GPU.
- Select and preview a dataset; check its text/template and loss masking.
- Keep one device visible for an initial smoke test. A second GPU does not automatically pool VRAM.
- Close unnecessary loaded inference models and retain enough disk for the base, checkpoints, adapters, and logs.

In Studio, the training request includes model selection, `load_in_4bit`, sequence length, dataset source, learning rate, adapter rank, and other validated fields. Start with a small bounded run, inspect metrics, and only then expand the dataset or training duration.

## Minimal Python shape

This example expects a **previously downloaded, compatible local Llama-style checkpoint** in `model-checkpoint`. It illustrates a one-step FP32 adapter smoke run, not recommended hyperparameters for a production model. Use one visible CUDA GPU and an appropriately small checkpoint.

```python
from unsloth import FastLanguageModel
import torch
from datasets import Dataset
from trl import SFTConfig, SFTTrainer

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="model-checkpoint",
    max_seq_length=64,
    dtype=torch.float32,
    load_in_4bit=False,
    device_map={"": "cuda:0"},
    local_files_only=True,
)
model = FastLanguageModel.get_peft_model(
    model,
    r=2,
    lora_alpha=4,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                    "gate_proj", "up_proj", "down_proj"],
    use_gradient_checkpointing=False,
)
trainer = SFTTrainer(
    model=model,
    processing_class=tokenizer,
    train_dataset=Dataset.from_dict(
        {"text": ["tiny offline training example"] * 2}
    ),
    args=SFTConfig(
        output_dir="adapter-smoke",
        max_steps=1,
        max_length=64,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=1,
        learning_rate=1e-3,
        bf16=False,
        fp16=False,
        packing=False,
        padding_free=False,
        gradient_checkpointing=False,
        dataloader_num_workers=0,
        optim="adamw_torch",
        report_to="none",
        save_strategy="no",
    ),
)
trainer.train()
model.save_pretrained("adapter-smoke/saved")
tokenizer.save_pretrained("adapter-smoke/saved")
```

For a genuinely offline, self-contained qualification fixture, use the existing [tiny-Llama GPU test](https://github.com/darbotlabs/darbot-unsloth/blob/main/tests/test_python314_gpu_smoke.py). It constructs a tiny model locally rather than downloading a benchmark.

## Validate more than the loss display

A meaningful smoke run checks finite forward loss and gradients, a completed optimizer step, changed trainable adapter weights, and successful adapter save/reload. Reload should preserve weights and logits within the relevant precision tolerances. TensorBoard verification should read back actual events, not just check that a logging directory exists.

The fork's T1000 qualification covers FP32 LoRA and default 4-bit QLoRA separately on each of two 8 GB devices. It does not certify BF16, arbitrary larger models, DDP, or every kernel.

Read [datasets and TRL 1.12](datasets.md) before enabling packing or response-only loss. Read [export](export.md) before assuming a trained adapter implies FP8/FP4 export support.

**Implementation:** [training schema](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/backend/models/training.py), [Studio trainer](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/backend/core/training/trainer.py), [Core trainer adaptation](https://github.com/darbotlabs/darbot-unsloth/blob/main/unsloth/trainer.py).
