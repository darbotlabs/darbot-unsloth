---
title: Troubleshooting
description: Diagnose interpreter, source, artifact, compiler, environment, dataset, API, GPU-memory, and export failures without destructive workaround commands.
---

Start with the first failing layer. Do not repeatedly reinstall unrelated packages or delete the data root when the actual problem is a driver, source path, or incompatible artifact.

## Fast triage

```text
unsloth studio verify-install --json
```

Then confirm the actual interpreter path/version and selected backend family. A shell's `python` and a desktop-managed backend can point to different environments.

| Symptom | Check | Safe next step |
| --- | --- | --- |
| Python rejected | Final standard CPython `>=3.14.7,<3.15`; not free-threaded | Use a compliant interpreter through the installer |
| Occupied environment refused | Exact path, ownership marker, recorded data-root association | Preserve it; choose a new location if ownership is not established |
| Source checkout not found | Complete, buildable fork source and matching companion identity; `--local`, explicit `STUDIO_LOCAL_REPO` if needed | Point at a real checkout; environment containers and unrelated `pyproject.toml` files are rejected |
| Missing maintained Zoo | Full ML profile and complete vendored source | Re-run the fork's paired install path, not upstream Zoo |
| Completion manifest missing/stale | Interrupted install or changed requirements | Finish the intended dependency pass and re-verify |
| Protobuf metaclass exception | Native abi3 wheel installed instead of the pure artifact | Repair to the checksum-qualified official pure 4.25.9 wheel through the managed installer |
| Resolver asks to downgrade Torch | Incompatible optional extension/export stack | Keep the canonical profile; investigate the blocked capability |
| Wrong Triton import | Mixed provider distributions | Restore the selected profile's provider; do not layer CUDA/XPU/ROCm compilers |
| CUDA unavailable or kernel failure | Driver, wheel family, device capability, extension ABI | Validate actual device/runtime; do not silently switch cu130 to cu126 |
| GPU out of memory | Context, batch, activations/KV, other loaded work | Reduce workload and unload unused models; two devices do not pool memory |
| Launcher missing/blocked | Exact owned path, installation logs, antivirus/application control | Follow managed recovery; do not disable security globally |
| API unauthorized | Correct server/port and current bearer credential | Re-authenticate or rotate/recreate the client key securely |

## Browser cannot connect

Confirm the backend is running and inspect the address it printed. `127.0.0.1` and an IPv6-only `localhost` resolution can differ. The default production port is 8888; the frontend development server is a different process.

If a port is occupied, identify the exact owning process or choose another port. Do not terminate every Python, Node, or Studio process by name. A listening socket does not prove application readiness.

## An installed package is mistaken for source

Older installed helpers can encounter unrelated project metadata inside `site-packages`, including uroman's `pyproject.toml`. The updated resolver now validates [buildable Core and companion identity](updates.md#source-identity-is-checked-before-reuse) and rejects environment containers before accepting a source candidate.

Use the actual retained fork checkout and updated installer/helper for recovery. Do not remove uroman, add a fake README, or copy project metadata into `site-packages` to make it look like source. Keep the selected environment and data root unchanged, then run installation verification and a real startup check. A source-level fix and its regression tests do not by themselves verify a rebuilt desktop/Python release.

## Dataset/training errors

Check row format and the intended tokenizer/chat template. TRL 1.12 expects the modern `SFTConfig`/`processing_class` contract. Pre-tokenized labels and masks must survive packing; custom `with_transform` inputs are not silently supported.

For streaming, use valid plain split names rather than unsupported slice syntax. On Windows/spawn, more map workers are not automatically safer or faster. Read [dataset semantics](datasets.md).

## Export and audio errors

FP8/FP4 compressed export through the current LLMCompressor is intentionally unavailable on this Torch 2.14 stack. Do not downgrade the environment to hide that fact. GGUF, uncompressed output, and 4-bit QLoRA are separate.

For audio, distinguish a codec dependency error from invalid input, a missing checkpoint, or unsupported device placement. Preserve the AudioTools/protobuf/TensorBoard artifact combination. See [audio](audio.md).

## When to stop repairing

If repeated attempts change source provenance, lose the intended environment, or touch unrelated packages, stop. Retain the old data and recovery copies, collect a sanitized minimal report, and follow [support](support.md).

Production installation qualification is ongoing until the [release status](/downloads) says otherwise. A fixed source-selection bug does not establish successful installation, UI startup, or publication of every release artifact.

**Sources:** [install verification](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/install_manifest.py), [repair helper](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/install_python_stack.py), [launcher and update logic](https://github.com/darbotlabs/darbot-unsloth/blob/main/unsloth_cli/commands/studio.py).
