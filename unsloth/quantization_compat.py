# SPDX-License-Identifier: Apache-2.0
"""Fail before mutating a stack outside the published quantizer's requirements."""

from importlib.metadata import PackageNotFoundError, version

from packaging.version import InvalidVersion, Version


LLM_COMPRESSOR_MAX_VERSIONS = {
    "torch": "2.13.0",
    "transformers": "5.14.1",
    "numpy": "2.4.6",
}


def llm_compressor_compatibility_error(versions = None):
    problems = []
    for package, ceiling in LLM_COMPRESSOR_MAX_VERSIONS.items():
        try:
            active = version(package) if versions is None else versions[package]
            parsed = Version(str(active))
            if Version(parsed.public) > Version(ceiling):
                problems.append(f"{package} {active} exceeds <= {ceiling}")
        except PackageNotFoundError, KeyError, InvalidVersion, TypeError:
            problems.append(f"{package} compatibility cannot be verified")
    if not problems:
        return None
    return (
        "Unsloth: llmcompressor 0.13.0 FP8/FP4 compressed export is unsupported on this stack: "
        + "; ".join(problems)
        + ". Do not downgrade the active stack or install an older Transformers shadow. "
        "Use merged_16bit or GGUF export instead; other quantizers require their own qualification."
    )


def require_llm_compressor_compatibility():
    error = llm_compressor_compatibility_error()
    if error is not None:
        raise RuntimeError(error)
