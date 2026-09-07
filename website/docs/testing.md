---
title: Testing & validation
description: Run targeted repository checks and distinguish static policy tests, real framework tests, application lifespans, browser smoke tests, and GPU qualification.
---

The repository has different test lanes for different questions. Run the smallest existing tests that cover your change, then escalate if those results require it. Do not infer production readiness from a broad test count.

## Validation levels

| Level | What it can establish | What it cannot establish |
| --- | --- | --- |
| Manifest/policy tests | Version, interpreter, pin, and artifact contracts | A working GPU |
| Framework integration | Real datasets/TRL preparation and runtime compatibility | Every training model |
| Backend unit/API tests | Validation, orchestration, auth, lifecycle behavior | Native desktop installation by themselves |
| Frontend typecheck/tests/build | UI logic and production asset generation | Real server/model interaction |
| Browser smoke | A rendered UI and exercised user flow | All hardware profiles |
| Real GPU smoke | Actual tensor/kernel/training behavior on the selected device | Other devices, DDP, or full production coverage |
| Packaged installation test | Behavior of the actual release artifact | Every OS or enterprise security policy |

## Targeted Python checks

Run with the intended supported interpreter and prepared dependencies:

```powershell
python -m pytest tests\test_python314_dependency_policy.py tests\test_python314_runtime_compat.py tests\test_trl112_dataset_integration.py -q
```

The TRL integration file tests the actual TRL 1.12/datasets 5 preparation pipeline rather than only stubs.

To exercise the existing offline tiny-Llama GPU fixture on one physical device:

```powershell
$env:CUDA_VISIBLE_DEVICES = '0'
python -m pytest tests\test_python314_gpu_smoke.py -q
```

Repeat with the intended device index in a **new Python process**. The training fixture selects the primary visible GPU; this avoids mistaking a multi-device machine for a distributed-training test.

These checks can skip when required packages or devices are absent. A skipped test is not qualification. Preserve the real test result and environment identity.

### Verify installed artifacts, not an accidental checkout import

For release qualification, run from outside the checkout with the intended installed interpreter and verify import provenance before and after the workload. Check Core, Zoo, and the tested submodules—not only the top-level distribution version strings. A passing test that imported working-tree modules does not establish that the wheel contains working code.

The recorded installed-Windows run used isolated interpreter execution and passed four GPU cases on each of two separately selected T1000 8 GB devices, eight total with no skips. The cases cover underlying PEFT execution plus FP32, TensorBoard-enabled FP32, and genuinely packed 4-bit Unsloth QLoRA training with adapter reload/inference parity. See the [qualification matrix](support.md#measured-windows-paths) for the exact scope.

Keep raw provenance paths and logs private when they expose machine layout or user information. Publish a sanitized result and precise platform/workload boundary instead.

The root pytest configuration defaults discovery to `tests/security` and excludes `gpu`/`slow` markers unless explicitly selected. Broader marked workloads may download real checkpoints; review the relevant test before enabling `-m gpu` or slow suites.

## Application and frontend checks

```text
unsloth studio verify-install --json
```

This checks completed installation and file health. Separately exercise real application startup, authenticated API access, model load/unload, and any changed worker lifecycle. Normal warmup and controlled Torch-absence startup are different tests.

For Studio frontend changes:

```powershell
npm run typecheck --prefix studio\frontend
npm test --prefix studio\frontend
npm run build --prefix studio\frontend
```

For this wiki:

```powershell
npm ci --prefix website
npm test --prefix website
npm run typecheck --prefix website
npm run build --prefix website
```

The documentation build fails on broken internal links and anchors. Release-data tests prevent publication/version/filename drift; they do not verify remote release uploads.

**Sources:** [pytest configuration](https://github.com/darbotlabs/darbot-unsloth/blob/main/pyproject.toml), [tiny-Llama test](https://github.com/darbotlabs/darbot-unsloth/blob/main/tests/test_python314_gpu_smoke.py), [backend CI](https://github.com/darbotlabs/darbot-unsloth/blob/main/.github/workflows/studio-backend-ci.yml), [frontend CI](https://github.com/darbotlabs/darbot-unsloth/blob/main/.github/workflows/studio-frontend-ci.yml).
