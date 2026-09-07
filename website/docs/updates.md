---
title: Source-aware updates, repair & rollback
description: Distinguish tracked source updates from immutable repair snapshots, preserve local work and exact environments, and validate recovery without silent fallback.
---

An **update** intentionally advances source or dependencies. A **repair** restores a known installation contract. A **rollback** returns to retained prior material. Treating all three as "install latest" can destroy provenance and local work.

## Source mode determines behavior

| Installation source | Update expectation | Repair expectation |
| --- | --- | --- |
| Default remote fork source | Track fork `main` for an intentional update | Use the recorded immutable source snapshot |
| Explicit local checkout / CI overlay | Use the supplied source, including intended local work | Do not silently advance to a remote branch |
| Explicit revision or source pin | Preserve the pin | Restore the recorded source/artifact contract |
| Editable development source | Preserve developer intent and uncommitted work | Do not replace it with a convenient unrelated package |

Core and the matching maintained Zoo must refresh together, even when their package version strings remain unchanged. A version equality check is not proof the source files are identical.

No silent PyPI, upstream, or older-framework fallback is an acceptable recovery strategy for this fork.

## Source identity is checked before reuse

A `pyproject.toml` file by itself does not identify an Unsloth checkout. The source resolver checks the Core project name, setuptools build metadata, `unsloth_cli:app` entry point, version declaration, a valid local README, required source files, and the maintained Zoo companion's project identity.

It rejects environment containers—including interpreter prefixes, `site-packages`/`dist-packages`, and directories containing `pyvenv.cfg`—as candidate source roots. This prevents an unrelated installed package's project metadata, such as uroman's `pyproject.toml`, from masking the intended retained checkout.

These checks protect source selection; they do not authorize replacing an unowned environment, bypass [data-root ownership](storage.md), or prove the next packaged release is qualified. Older installed packages may not yet include the source-identity fix; use the intended complete fork checkout when recovering such an installation.

## Normal maintenance sequence

1. Record the source/profile and make [a data backup](storage.md).
2. Finish or stop active work and close the desktop app/backend normally.
3. Confirm the exact environment and data root, especially when using overrides.
4. Run the intentional update through the managed launcher.
5. Verify the installation, launch the application, and repeat a small representative workload.
6. Keep rollback material until that workload and data access are verified.

For an installation with recorded source provenance:

```text
unsloth studio update
unsloth studio verify-install --json
```

For an explicit checkout when invoking an installed CLI, supply that checkout deliberately:

```powershell
$env:STUDIO_LOCAL_REPO = 'C:\src\darbot-unsloth'
unsloth studio update --local
```

Alternatively, from the actual fork root rerun `.\install.ps1 --local --skip-autostart` on Windows or `UNSLOTH_SKIP_AUTOSTART=1 bash install.sh --local` on POSIX. Preserve your original environment/data overrides and GGUF-only mode when applicable.

## Interrupted or damaged installs

The completion manifest is dropped before a dependency pass and written only after completion. A package with intact metadata can still have missing/corrupt files; a normal "already satisfied" resolver result does not repair those files automatically.

Capture the first actionable error. Distinguish:

- missing runtime requirements or a stale fingerprint;
- wrong Torch family or compiler provider;
- duplicate distribution metadata;
- native protobuf wheel versus the required pure artifact;
- source-discovery/provenance errors;
- locked or quarantined launchers.

If an older installation still points source discovery at an unrelated package's `pyproject.toml`, stop and record the wrong path. Recover using the intended complete fork checkout and the updated helper; do not delete the unrelated package or fabricate checkout metadata. Verify the actual installed environment afterward. Packaged rebuild/reinstall checks remain part of release qualification.

## Rollback is not an invented command

The repository contains staged-update and launcher-recovery machinery. Retained copies are recovery material, not a documented universal `rollback` CLI command. Use the recovery paths reported by the failed operation, preserve the original data root, and verify process ownership before manual action.

If the exact prior environment cannot be safely reactivated, reconstruct a separate environment from the recorded source and profile while retaining data. Do not erase the only working copy to force an installer fast path.

**Sources:** [update CLI](https://github.com/darbotlabs/darbot-unsloth/blob/main/unsloth_cli/commands/studio.py), [install/repair helper](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/install_python_stack.py), [source-selection regression tests](https://github.com/darbotlabs/darbot-unsloth/blob/main/tests/python/test_install_python_stack.py), [Windows source regression tests](https://github.com/darbotlabs/darbot-unsloth/blob/main/tests/python/test_windows_fork_source.py), [staging](https://github.com/darbotlabs/darbot-unsloth/blob/main/unsloth_cli/_studio_stage.py), [desktop staged update](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/src-tauri/src/staged_update.rs).
