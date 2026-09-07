---
title: Contributing
description: Make focused contributions to the fork, preserve upstream attribution and source contracts, run targeted tests, and maintain the wiki and release data.
---

Contributions here target **darbotlabs/darbot-unsloth**, not an upstream release. Read the repository's [contribution guide](https://github.com/darbotlabs/darbot-unsloth/blob/main/CONTRIBUTING.md) and [code of conduct](https://github.com/darbotlabs/darbot-unsloth/blob/main/CODE_OF_CONDUCT.md).

## Prepare the right environment

Use a complete source checkout and the [supported installer/profile](getting-started.md). Full ML development requires the maintained Zoo companion before Core; true GGUF-only development deliberately does not install Zoo.

Do not run tests in an unrelated system Python and interpret missing dependencies as a failure of the supported stack. Keep editable work and source pins explicit. Avoid testing destructive install/recovery paths against an occupied environment that contains valuable user data.

## Keep a change reviewable

1. Describe the concrete problem and the layer it belongs to.
2. Reproduce it with a focused test or a small, authorized workload.
3. Change the implementation—not only dependency upper bounds or installed metadata.
4. Add/update the closest existing tests for changed behavior.
5. Run [targeted validation](testing.md), then report results and remaining gaps.
6. Update source-linked documentation when commands, profiles, or behavior change.

Do not rewrite historical fixtures merely to hide incompatibility. Do not add unsupported Python versions to the CI matrix or replace measured qualification with import-only checks.

## Dependency changes require a contract review

Consider the root extras, Studio requirements, shared constraints, Data Designer direct-runtime union, no-Torch negative constraints, platform markers, and paired Zoo source. A new version may be valid in one lane and incompatible in another.

For Node changes, retain committed lockfiles and use the project's current toolchain. Keep Studio's frontend, OXC recipe validator, Tauri CLI holder, and documentation website as separate package scopes.

## Documentation workflow

```powershell
npm ci --prefix website
npm run start --prefix website
```

The development server prints the project-prefixed URL. Documentation lives in `website/docs`; navigation is explicit in `website/sidebars.ts`. Use focused pages, meaningful headings, relative document links, and source links for claims.

Before a docs PR:

```powershell
npm test --prefix website
npm run typecheck --prefix website
npm run build --prefix website
```

Broken links and anchors fail the production build. Search is generated locally from the built public content, with no hosted search credentials.

## Publication discipline

Do not set `release.json` to `published` before the actual assets and checksums have been uploaded and verified. Keep version schemes, filenames, signing state, and qualification notes aligned. The [release interface](builds-releases.md#website-publication-interface) is designed for one atomic metadata update.

Preserve upstream copyright/license notices and third-party attribution. Never include real credentials, model cache contents, private session artifacts, or user datasets in a documentation PR.

**Source areas:** [tests](https://github.com/darbotlabs/darbot-unsloth/tree/main/tests), [Studio backend](https://github.com/darbotlabs/darbot-unsloth/tree/main/studio/backend), [frontend](https://github.com/darbotlabs/darbot-unsloth/tree/main/studio/frontend), [wiki source](https://github.com/darbotlabs/darbot-unsloth/tree/main/website).
