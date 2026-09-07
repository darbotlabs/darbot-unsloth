---
title: Attribution & licenses
description: Preserve Unsloth AI's authorship, the repository's Core/Studio license boundaries, vendored companion notices, and third-party obligations.
---

## Upstream authorship

Darbot Unsloth is an independent fork of **Unsloth**, created by the **Unsloth AI team**. The original project's authorship, copyright notices, and licenses remain applicable. This wiki does not imply endorsement by Unsloth AI or rebrand an upstream release as a fork-built artifact.

- [Upstream source](https://github.com/unslothai/unsloth)
- [Upstream documentation](https://unsloth.ai/docs)
- [Darbot fork source](https://github.com/darbotlabs/darbot-unsloth)

Upstream documentation is valuable for model-specific concepts, but it may use a different runtime policy. Upstream downloads, Docker images, and notebooks must not be represented as containing this fork's changes.

## License boundaries

| Material | Where to read the applicable terms |
| --- | --- |
| Core/root Apache-licensed material | [Root LICENSE](https://github.com/darbotlabs/darbot-unsloth/blob/main/LICENSE) |
| Studio and AGPL-marked components | [Studio AGPL-3.0 license](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/LICENSE.AGPL-3.0) and [COPYING](https://github.com/darbotlabs/darbot-unsloth/blob/main/COPYING) |
| Maintained vendored Zoo | [Companion license](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/backend/vendor/unsloth_zoo_compat/LICENSE) and retained per-file notices |
| Vendored truststore | [Vendor documentation](https://github.com/darbotlabs/darbot-unsloth/blob/main/studio/backend/vendor/README.md) and adjacent MIT license |
| Models, datasets, native helpers, and package dependencies | Their own upstream licenses and distribution notices |

Read individual file headers and component licenses; do not assume that one repository-level label relicenses every bundled dependency. The maintained Zoo modifications do not remove its original attribution.

The newly authored wiki/site code follows the root Apache-2.0 license. Links and explanatory summaries do not change the licensing of Studio or third-party material.

## Distribution and network use

If distributing modified components or providing network access to AGPL-covered software, review the license's corresponding-source and notice obligations. Keep the applicable source available and preserve required notices. This page is an orientation, not legal advice.

Release archives must not include credentials or user data. Model weights and training datasets can impose independent use/redistribution conditions even when the application code is open source.

## Website technology and assets

The site is built with [Docusaurus](https://docusaurus.io/) and React, using their upstream packages and licenses. Search uses the local Docusaurus search plugin; no third-party search service is required.

The website's simple geometric mark and social card are original documentation assets, not copied application screenshots or an official Unsloth logo. No upstream performance graphics or benchmark claims are republished as this fork's results.

For actual platform evidence, see [qualification scope](support.md). For current artifacts, see [Downloads](/downloads).
