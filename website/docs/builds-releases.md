---
title: Production builds & releases
description: Understand frontend, Python, Tauri, release qualification, artifact checksums, and the GitHub Pages publication interface.
---

## Different artifacts, different version schemes

| Product | Current version scheme | Meaning |
| --- | --- | --- |
| Python package | **2026.9.3** | Core/Studio package version |
| Desktop application | **0.2.0**, tag **v0.2.0** | SemVer desktop/display release |
| Private npm holders | `0.0.0` | Dependency lockfile holders, not public product versions |
| Documentation | Source-controlled static site | Publication status is data, not a hard-coded download promise |

Always use [Downloads](/downloads) for current asset availability. An executable or wheel built on a maintainer's machine is not yet a qualified, uploaded release.

:::important Local execution policy
Repository GitHub Actions are currently disabled at the user's request. Run build, test, and browser-verification steps locally. Retained workflow files are inactive definitions, not permission to dispatch or re-enable Actions.
:::

## Build layers

1. **Studio frontend:** install its committed npm lockfile and run its production build.
2. **Python distribution:** include the built frontend and package data; stamp and verify the display-only desktop release metadata.
3. **Tauri desktop:** use the pinned CLI/Rust dependencies and target-specific native packaging prerequisites.
4. **Installation qualification:** install the actual built artifacts, not only a source checkout.
5. **Publication:** upload verified binaries plus checksums to the fork's GitHub Release, then update the website's release status.

Frontend commands, from the repository root:

```powershell
npm ci --prefix studio\frontend
npm run typecheck --prefix studio\frontend
npm run build --prefix studio\frontend
```

For Python packaging, the repository's `build.sh` implements frontend build, metadata stamping, distribution build, and validation. Read its publishing branch before invoking it; build automation can clean output directories and publication is not a harmless local test.

A release's explicit stamp is supplied with `UNSLOTH_STUDIO_RELEASE_VERSION`. After packaging, validate the shipped stamp with the existing tool:

```powershell
python scripts\stamp_studio_release.py --verify-dist dist --expected v0.2.0
```

Use the supported Python interpreter for build tooling. Do not upload distributions whose packaged metadata or version scheme disagrees with the intended release.

## Desktop and updater policy

The intended Windows installer is an **unsigned NSIS x64** build. Its desktop executable is not a complete offline Python/model bundle. Native tooling, WebView2, the selected environment, network acquisition, and actual first-run behavior must be tested.

Automatic signed desktop updating remains disabled. `createUpdaterArtifacts` is false in the Tauri bundle configuration. The retained release workflow definitions also contain an `UNSLOTH_DESKTOP_PUBLISH=true` gate, but repository-wide Actions are disabled and must not be re-enabled or dispatched. A repository variable alone neither authorizes an Actions run nor creates signing keys, signatures, or a configured updater.

Do not invent signing material or ask users to disable platform security controls.

## Website publication interface

`website/src/data/release.json` is the single release-status interface. While `status` is `preparing`, asset names are shown as planned files, with **no direct download links**.

After all assets are qualified and uploaded:

1. Confirm the tag/version pairing and every listed filename.
2. Set `status` to `published`.
3. Set `publishedAt` to the actual `YYYY-MM-DD` date.
4. Update `summary` with truthful qualification/known-issue information and keep `desktopSigned` accurate.
5. Keep the JSON update together, run the site checks/build locally, and retain the output for an explicitly authorized publication path. Do not treat this metadata edit as a Pages deployment.

The website constructs direct links only to this fork's GitHub Releases. The validator checks tag/version agreement, required filenames, a valid publication date, and the checksum manifest. It does not independently certify binaries or replace the maintainer's upload checks.

## GitHub Pages and local output

The existing published wiki remains at `https://darbotlabs.github.io/darbot-unsloth/`. Repository Actions are now disabled. **Deploy documentation to GitHub Pages** in `.github/workflows/deploy-pages.yml` is retained but inactive; its former push/PR/manual-dispatch triggers are not the current execution path.

Run the corresponding website checks locally:

```powershell
npm ci --prefix website
npm test --prefix website
npm run typecheck --prefix website
npm run build --prefix website
npm run serve --prefix website
```

Preview the generated project path locally. The built `website/build/` directory, a schema capture, or a Git commit does **not** establish that a new API catalog or download page is live. No new Pages publication is claimed until an explicitly authorized path that respects disabled Actions has been completed. A static branch push must not be assumed to bypass Pages deployment workflows.

GitHub Releases uploads are separate from both Actions execution and Pages publication. Maintainers can manage release assets without treating that as authorization to run workflows. No organization-root repository, custom domain, analytics service, or committed release binaries are needed.

**Sources:** [build script](https://github.com/darbotlabs/darbot-unsloth/blob/main/build.sh), [stamp tool](https://github.com/darbotlabs/darbot-unsloth/blob/main/scripts/stamp_studio_release.py), [Tauri bundle policy](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/src-tauri/tauri.conf.json), [desktop workflow](https://github.com/darbotlabs/darbot-unsloth/blob/main/.github/workflows/release-desktop.yml).
