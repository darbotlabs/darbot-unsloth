"""Offline, tiny-model GPU qualification; no CUDA spoofing or model downloads."""

from importlib.metadata import PackageNotFoundError, version
import math

import pytest


torch = pytest.importorskip("torch")


def _real_cuda_devices():
    if not torch.version.cuda or not torch.cuda.is_available():
        return []
    try:
        probe = torch.empty(0, device = "cuda:0")
    except RuntimeError, AssertionError:
        return []
    # Other CPU orchestration modules may have installed a CUDA spoof during
    # collection. Such a process cannot qualify a GPU kernel.
    return list(range(torch.cuda.device_count())) if probe.device.type == "cuda" else []


DEVICES = _real_cuda_devices()


@pytest.fixture(autouse = True)
def offline(monkeypatch):
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "1")
    monkeypatch.setenv("HF_DATASETS_OFFLINE", "1")


def tiny_llama():
    from transformers import LlamaConfig, LlamaForCausalLM, PreTrainedTokenizerFast
    from tokenizers import Tokenizer
    from tokenizers.models import WordLevel
    from tokenizers.pre_tokenizers import Whitespace

    vocab = {
        "<pad>": 0,
        "<unk>": 1,
        "<s>": 2,
        "</s>": 3,
        "tiny": 4,
        "offline": 5,
        "training": 6,
        "example": 7,
    }
    backend = Tokenizer(WordLevel(vocab, unk_token = "<unk>"))
    backend.pre_tokenizer = Whitespace()
    tokenizer = PreTrainedTokenizerFast(
        tokenizer_object = backend,
        pad_token = "<pad>",
        unk_token = "<unk>",
        bos_token = "<s>",
        eos_token = "</s>",
    )
    config = LlamaConfig(
        vocab_size = len(vocab),
        hidden_size = 32,
        intermediate_size = 64,
        num_hidden_layers = 1,
        num_attention_heads = 4,
        num_key_value_heads = 2,
        max_position_embeddings = 64,
        pad_token_id = 0,
        bos_token_id = 2,
        eos_token_id = 3,
    )
    config._attn_implementation = "eager"
    return LlamaForCausalLM(config), tokenizer


def assert_adapter_roundtrip(model, tokenizer, directory, device, load_kwargs):
    from peft import get_peft_model_state_dict
    from unsloth import FastLanguageModel

    expected = {
        name: value.detach().cpu().clone()
        for name, value in get_peft_model_state_dict(model).items()
    }
    model.save_pretrained(directory)
    tokenizer.save_pretrained(directory)
    assert (directory / "adapter_config.json").is_file()
    assert (directory / "adapter_model.safetensors").is_file()
    tokens = torch.tensor([[2, 4, 5, 6, 7, 3]], device = device)
    FastLanguageModel.for_inference(model)
    with torch.no_grad():
        expected_logits = model(input_ids = tokens, use_cache = False).logits.float().cpu()
    restored, _ = FastLanguageModel.from_pretrained(
        model_name = str(directory),
        max_seq_length = 64,
        device_map = {"": str(device)},
        local_files_only = True,
        **load_kwargs,
    )
    assert restored.active_adapters == model.active_adapters
    actual = get_peft_model_state_dict(restored)
    assert actual.keys() == expected.keys()
    for name, value in expected.items():
        torch.testing.assert_close(actual[name].detach().cpu(), value, rtol = 0, atol = 0)
    FastLanguageModel.for_inference(restored)
    with torch.no_grad():
        restored_logits = restored(input_ids = tokens, use_cache = False).logits.float().cpu()
    assert torch.isfinite(restored_logits).all()
    rtol, atol = (1e-5, 1e-6) if load_kwargs.get("load_in_4bit") is False else (1e-3, 1e-4)
    torch.testing.assert_close(restored_logits, expected_logits, rtol = rtol, atol = atol)


@pytest.mark.parametrize("device_index", DEVICES)
def test_tiny_llama_peft_forward_backward_on_each_real_gpu(device_index):
    """Establish the underlying Torch/Transformers/PEFT path independently."""
    from peft import LoraConfig, get_peft_model

    device = torch.device("cuda", device_index)
    with torch.cuda.device(device):
        model, _ = tiny_llama()
        model = get_peft_model(
            model.to(device),
            LoraConfig(
                r = 2,
                lora_alpha = 4,
                target_modules = ["q_proj", "v_proj"],
                task_type = "CAUSAL_LM",
            ),
        )
        model.train()
        tokens = torch.tensor([[2, 4, 5, 6, 7, 3]], device = device)
        output = model(input_ids = tokens, labels = tokens)
        assert torch.isfinite(output.loss)
        output.loss.backward()
        gradients = [parameter.grad for parameter in model.parameters() if parameter.requires_grad]
        assert gradients and all(
            gradient is not None and torch.isfinite(gradient).all() for gradient in gradients
        )
        assert any(torch.count_nonzero(gradient).item() for gradient in gradients)
        torch.cuda.synchronize(device)


@pytest.mark.parametrize("device_index", DEVICES[:1])
@pytest.mark.parametrize(
    ("report_to", "load_in_4bit"),
    [("none", False), ("tensorboard", False), ("none", True)],
    ids = ["fp32", "fp32-tensorboard", "qlora-4bit"],
)
def test_offline_unsloth_lora_sft_step_on_primary_real_gpu(
    device_index, report_to, load_in_4bit, tmp_path
):
    """Qualify Unsloth's actual fast model/trainer path, not just HF orchestration."""
    try:
        companion = version("unsloth_zoo")
    except PackageNotFoundError:
        pytest.skip("Install the maintained Zoo companion before Unsloth GPU qualification")
    assert companion == "2026.9.1+darbot.1"
    if report_to == "tensorboard":
        try:
            version("tensorboard")
        except PackageNotFoundError:
            pytest.skip("TensorBoard is an optional training integration")

    from unsloth import FastLanguageModel
    from datasets import Dataset
    from trl import SFTConfig, SFTTrainer

    checkpoint = tmp_path / "tiny-llama"
    model, tokenizer = tiny_llama()
    model.save_pretrained(checkpoint)
    tokenizer.save_pretrained(checkpoint)
    del model

    device = torch.device("cuda", device_index)
    with torch.cuda.device(device):
        # Omit both options for QLoRA to exercise the loader's actual defaults.
        load_kwargs = {} if load_in_4bit else {"dtype": torch.float32, "load_in_4bit": False}
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name = str(checkpoint),
            max_seq_length = 64,
            device_map = {"": str(device)},
            local_files_only = True,
            **load_kwargs,
        )
        if load_in_4bit:
            import bitsandbytes as bnb

            assert model.is_loaded_in_4bit
            quantized = [
                module for module in model.modules() if isinstance(module, bnb.nn.Linear4bit)
            ]
            assert len(quantized) == 7
            assert all(
                module.weight.dtype == torch.uint8
                and module.weight.device == device
                and module.weight.quant_state is not None
                for module in quantized
            )
        model = FastLanguageModel.get_peft_model(
            model,
            r = 2,
            lora_alpha = 4,
            target_modules = [
                "q_proj",
                "k_proj",
                "v_proj",
                "o_proj",
                "gate_proj",
                "up_proj",
                "down_proj",
            ],
            use_gradient_checkpointing = False,
        )
        layer = model.get_base_model().model.layers[0]
        assert layer.self_attn.apply_qkv.__name__ == "apply_lora_qkv"
        assert layer.self_attn.apply_o.__name__ == "apply_lora_o"
        assert layer.mlp.forward.__name__ == "apply_lora_mlp_swiglu"
        before = {
            name: parameter.detach().clone()
            for name, parameter in model.named_parameters()
            if parameter.requires_grad
        }
        args = SFTConfig(
            output_dir = str(tmp_path / "training"),
            max_steps = 1,
            per_device_train_batch_size = 1,
            gradient_accumulation_steps = 1,
            learning_rate = 1e-3,
            warmup_steps = 0,
            lr_scheduler_type = "constant",
            bf16 = False,
            fp16 = load_in_4bit,
            packing = False,
            padding_free = False,
            gradient_checkpointing = False,
            dataloader_num_workers = 0,
            save_strategy = "no",
            report_to = report_to,
            logging_steps = 1,
            optim = "adamw_torch",
        )
        # Qualify one actual GPU, not Trainer's implicit multi-GPU DataParallel.
        # CUDA_VISIBLE_DEVICES can select a different physical GPU before pytest.
        args._n_gpu = 1
        assert before and all(value.device == device for value in before.values())
        trainer = SFTTrainer(
            model = model,
            processing_class = tokenizer,
            train_dataset = Dataset.from_dict({"text": ["tiny offline training example"] * 2}),
            args = args,
        )
        log_dir = tmp_path / "tensorboard"
        if report_to == "tensorboard":
            from transformers.integrations import TensorBoardCallback
            callback = next(
                callback
                for callback in trainer.callback_handler.callbacks
                if isinstance(callback, TensorBoardCallback)
            )
            callback.logging_dir = str(log_dir)
        result = trainer.train()
        assert result.global_step == 1
        assert math.isfinite(result.training_loss)
        after = dict(model.named_parameters())
        assert any(not torch.equal(value, after[name]) for name, value in before.items())
        assert all(torch.isfinite(after[name]).all() for name in before)
        torch.cuda.synchronize(device)
        if report_to == "tensorboard":
            from tensorboard.backend.event_processing.event_accumulator import EventAccumulator

            events = EventAccumulator(str(log_dir)).Reload()
            losses = events.Scalars("train/loss")
            assert any(event.step == 1 and math.isfinite(event.value) for event in losses)
        assert_adapter_roundtrip(model, tokenizer, tmp_path / "adapter", device, load_kwargs)
