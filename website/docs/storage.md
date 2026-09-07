---
title: Environments, data roots & backups
description: Understand exact virtual-environment selection, persistent Studio paths, ownership records, model caches, and safe backup boundaries.
---

## Keep these four locations distinct

| Location | Contents | Safe assumption |
| --- | --- | --- |
| Source checkout | Core/Studio source, vendored companion, manifests | May contain local uncommitted work |
| Python environment | Interpreter, installed distributions, launcher, completion/ownership records | Runtime replacement must respect ownership and active processes |
| Studio data root | Auth, application state, datasets, outputs, exports | User data must be retained |
| Model/helper/cache locations | Downloaded weights, native executables, cached artifacts | May be outside the data root or shared; inspect before deleting |

`UNSLOTH_ENV_DIR` selects an **absolute exact virtual environment**. `UNSLOTH_STUDIO_HOME` independently selects persistent Studio data; `STUDIO_HOME` is the lower-priority alias.

The default Studio root is the user's `.unsloth/studio` directory. The default environment lives beneath it as `unsloth_studio`, but that nesting is a default layout—not a rule for explicit paths.

## Persistent paths inside the Studio root

| Relative path | Purpose |
| --- | --- |
| `auth/auth.db` | Authentication database |
| `studio.db` | Application persistence |
| `assets/datasets/uploads` | Uploaded datasets |
| `assets/datasets/recipes` | Recipe-produced datasets |
| `outputs` | Training outputs |
| `exports` | Exported models/artifacts |
| `rag/rag.db`, `rag/uploads` | Retrieval indexes and source documents |
| `cache` | Managed application caches |
| `bin` | Managed launchers and downloaded helpers where applicable |

The backend path utilities also resolve TensorBoard directories, external model inventories, Hub caches, documents, and project workspaces. Hugging Face, Ollama, or LM Studio locations are not necessarily children of the Studio root.

## Ownership records

Managed environments use `.unsloth-studio-owned`; an explicitly located environment records its associated data root in `.unsloth-studio-home`. That association allows launch/update logic to find the same user state in a later shell.

An occupied explicit environment requires the appropriate ownership and home records before replacement. Do not fabricate them to adopt an unrelated environment. The completion manifest, `unsloth_install_manifest.json`, records completed dependency installation, interpreter identity, and requirement fingerprints. A missing/stale manifest indicates work to verify, not permission to manufacture a success marker.

## Backup and restore practice

1. Stop generation, training, recipe, and export work, then close Studio normally.
2. Record source revision, profile, interpreter/environment path, and data root.
3. Back up persistent data consistently, especially SQLite databases and related files, while the application is stopped.
4. Preserve model/adaptor provenance and any caches you cannot easily download again.
5. Protect backups as sensitive data: auth material, conversations, provider configuration, and uploaded documents may be present.
6. Restore to the intended root and verify the application before deleting prior copies.

Do not assume copying a live virtual environment makes it portable to another OS/path. Keep the original rollback material and use the source-aware [update and recovery flow](updates.md).

**Sources:** [storage roots](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/backend/utils/paths/storage_roots.py), [environment resolver](https://github.com/darbotlabs/darbot-unsloth/blob/main/unsloth_cli/_environment.py), [manifest](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/install_manifest.py).
