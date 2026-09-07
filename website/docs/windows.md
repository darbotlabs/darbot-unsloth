---
title: Windows installation & environment reuse
description: Install the fork on Windows, select exact environment and data paths, and safely reuse a managed CPython 3.14 environment.
---

## What the installer manages

Run `install.ps1` from a complete fork checkout with `--local`. A non-local Windows installation instead obtains a commit-qualified archive of this fork; Git is not required for that archive-based bootstrap. It must include the installation helpers and maintained Zoo source. There is no supported fallback to upstream PyPI when those files are missing.

Use a normal PowerShell terminal. Review execution-policy errors and your organization's application-control policy rather than disabling system-wide protections. Native extensions may require appropriate compiler/toolchain support; successful wheel resolution alone does not prove compiled GPU kernels work.

## Choose paths deliberately

This example uses **illustrative paths**, not a required drive layout:

```powershell
$env:UNSLOTH_ENV_DIR = 'C:\AI\unsloth-env'
$env:UNSLOTH_STUDIO_HOME = 'C:\AI\unsloth-data'
.\install.ps1 --local --skip-autostart
```

- `UNSLOTH_ENV_DIR` is the **absolute, exact virtual-environment directory**. It is not a parent under which another environment is silently created.
- `UNSLOTH_STUDIO_HOME` selects persistent application data. `STUDIO_HOME` is its lower-priority alias.
- Without overrides, Studio uses the home-directory `.unsloth\studio` layout, with its default `unsloth_studio` environment.
- Keep source, Python packages, model caches, and persistent user data conceptually separate. See [storage](storage.md).

## Reuse does not authorize replacement

An existing environment must satisfy the standard CPython `>=3.14.7,<3.15` policy. To replace an **occupied explicitly selected environment**, the installer requires its ownership marker and recorded `.unsloth-studio-home` relationship. A directory containing Python is not automatically installer-owned.

Do not forge markers, erase user directories, or overwrite a foreign environment to pass this check. Choose a new empty location when ownership cannot be established. Preserve the old data root and any retained rollback environment until the replacement has been verified.

## Verify the exact interpreter

```powershell
& "$env:UNSLOTH_ENV_DIR\Scripts\python.exe" -c "import sys, sysconfig; print(sys.executable); print(sys.version); print(sys.implementation.name); print(sysconfig.get_config_var('Py_GIL_DISABLED'))"
& "$env:UNSLOTH_ENV_DIR\Scripts\unsloth.exe" studio verify-install --json
& "$env:UNSLOTH_ENV_DIR\Scripts\unsloth.exe" studio --host 127.0.0.1 --port 8888
```

These commands inspect or start your chosen environment; they do not activate an unrelated shell environment. For NVIDIA, confirm a CUDA-13-compatible driver and the [cu130 profile](devices.md). TorchAudio is **2.11.0+cu130**, not a nonexistent 2.14 audio package.

## If setup is interrupted

Do not start parallel repair/install processes. Close Studio and active workers normally, keep the failure log, and use [source-aware recovery](updates.md). A missing completion manifest must not be bypassed by merely importing the CLI. Antivirus quarantine of a launcher, a missing wheel, and source-discovery failures are different problems.

**Implementation:** [install.ps1](https://github.com/darbotlabs/darbot-unsloth/blob/main/install.ps1), [setup.ps1](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/setup.ps1), [environment resolver](https://github.com/darbotlabs/darbot-unsloth/blob/main/unsloth_cli/_environment.py), [Python policy](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/python_policy.py).
