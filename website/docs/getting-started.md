---
title: Getting started
description: Choose the correct Darbot Unsloth installation profile, prepare a source checkout, and verify a first local Studio launch.
---

## Decide before installing

1. **Need Python fine-tuning or Torch-backed inference?** Choose a full ML profile matching your hardware.
2. **Only need native GGUF chat and the Torch-free Studio/data runtime?** Choose [true GGUF-only mode](gguf-only.md).
3. **Need desktop packaging?** Check [Downloads](/downloads). Do not substitute an upstream installer and expect this fork's changes.

Use [device profiles](devices.md) to check the driver, wheel family, compiler provider, and qualification boundaries. Two GPUs do not automatically combine their memory.

## Prepare a source checkout

Windows PowerShell:

```powershell
git clone https://github.com/darbotlabs/darbot-unsloth unsloth
Set-Location unsloth
.\install.ps1 --local --skip-autostart
```

Linux, macOS, or a separate WSL environment:

```bash
git clone https://github.com/darbotlabs/darbot-unsloth unsloth
cd unsloth
UNSLOTH_SKIP_AUTOSTART=1 bash install.sh --local
```

`--local` selects the current checkout, including uncommitted changes. It does not mean "download the latest PyPI package." Use the fork installers to select the runtime, install the matching Zoo before Core where required, resolve shared dependencies, and prepare native helpers.

:::warning Interpreter policy
Python 3.12/3.13, early 3.14, 3.15, PyPy, prereleases, and free-threaded Python are outside policy. A free-threaded binary with the GIL turned back on is still unsupported. See [Windows reuse](windows.md) before pointing an installer at an occupied environment.
:::

## Verify, then launch

In a new terminal using the installed launcher:

```text
unsloth studio verify-install --json
unsloth studio --host 127.0.0.1 --port 8888
```

If the launcher is not on `PATH`, use its absolute path inside your selected environment. `verify-install` checks completion and installed-file health; it does **not** train a model or certify a GPU. Open the loopback address printed by Studio and complete the actual first-run authentication flow. No default password is published here.

For the first model, choose a small model appropriate to your backend and available memory, review its license, and finish downloading it before assuming offline operation works.

## Keep a useful baseline

Record the source revision, Python interpreter path, environment/data roots, backend family, GPU and driver, and the verification result. Store credentials separately; never paste tokens or personal datasets into public issues.

Continue with [Studio](studio.md), [training](training.md), or [troubleshooting](troubleshooting.md).

**Implementation:** [Windows installer](https://github.com/darbotlabs/darbot-unsloth/blob/main/install.ps1), [POSIX installer](https://github.com/darbotlabs/darbot-unsloth/blob/main/install.sh), [Studio CLI](https://github.com/darbotlabs/darbot-unsloth/blob/main/unsloth_cli/commands/studio.py).
