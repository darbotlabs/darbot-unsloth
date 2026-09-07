# SPDX-License-Identifier: Apache-2.0
"""Interpreter policy and per-device hardware eligibility, not execution vetoes."""

from __future__ import annotations

import sys
import sysconfig


def require_supported_python() -> None:
    if (
        sys.implementation.name != "cpython"
        or not ((3, 14, 7) <= sys.version_info[:3] < (3, 15, 0))
        or sys.version_info[3] != "final"
        or sysconfig.get_config_var("Py_GIL_DISABLED")
    ):
        raise RuntimeError(
            "Darbot Unsloth requires standard (GIL-enabled) CPython >=3.14.7,<3.15. "
            "Prereleases, older interpreters and free-threaded builds are unsupported."
        )


def get_cuda_feature_support(device: int | None = None) -> dict:
    """Report hardware eligibility, not a claim that kernels have been tested.

    In particular, Turing's working CUDA tensor operations do not imply support
    for every Triton 3.8 kernel or Inductor graph. Conversely, an upstream
    support policy is not proof that a particular kernel fails. Runtime
    compilation fields remain None until separately qualified; BF16 and
    FlashAttention fields describe native hardware eligibility only.
    """
    import torch

    available = bool(torch.cuda.is_available()) and not bool(torch.version.hip)
    result = {
        "cuda_available": available,
        "device": device,
        "name": None,
        "compute_capability": None,
        "triton_policy_supported": False,
        "triton_kernels": False,
        "torch_compile_cuda": False,
        "bf16": False,
        "flash_attention_2": False,
        "reason": "NVIDIA CUDA is unavailable.",
    }
    if not available:
        return result
    if device is None:
        device = torch.cuda.current_device()
    capability = tuple(torch.cuda.get_device_capability(device))
    supported = capability >= (8, 0)
    result.update(
        device = device,
        name = torch.cuda.get_device_name(device),
        compute_capability = capability,
        triton_policy_supported = supported,
        triton_kernels = None,
        torch_compile_cuda = None,
        bf16 = supported,
        flash_attention_2 = supported,
        reason = (
            "Within upstream Triton hardware policy; individual kernels still require qualification."
            if supported
            else f"This sm_{capability[0]}{capability[1]} device is outside Triton 3.8's upstream "
            "support policy (compute capability >=8.0). Runtime kernels are unqualified, not "
            "automatically disabled; CUDA eager and per-feature kernel probes remain available."
        ),
    )
    return result
