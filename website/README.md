# Darbot Unsloth documentation

Docusaurus 3.10.2, scaffolded with the official `create-docusaurus` classic
TypeScript template. This is the fork's public wiki, not the Studio frontend.
Target: <https://darbotlabs.github.io/darbot-unsloth/>.

## Develop and verify

Use Node 26.8.1 (`.nvmrc`) and npm. From this directory:

```text
npm ci
npm start
npm test
npm run typecheck
npm run build
npm run serve
```

The build emits `build/`; preview the `/darbot-unsloth/` project path.
Generated output and dependencies are ignored. Do not commit binaries, local
environment files, user data, model caches, or build/browser artifacts.

`docs/` contains 25 focused wiki pages. `sidebars.ts` defines their navigation.
Internal links and anchors fail the build when broken. Search is indexed from
public content at build time using `@easyops-cn/docusaurus-search-local`; no
Algolia account, API keys, external analytics, or remote search service is used.

## Release metadata

Edit **`src/data/release.json`** atomically only after release qualification
and upload. The renderer never probes GitHub from visitors' browsers.

- `status`: `preparing` hides all direct asset links; `published` enables them.
- `tag`: `v` plus `desktopVersion` (desktop SemVer).
- `pythonVersion`: Python calendar version, independent of desktop SemVer.
- `publishedAt`: `null` while preparing, actual `YYYY-MM-DD` when published.
- `desktopSigned`: truthful Windows signing state; automatic signed updates
  remain disabled and are not toggled by this data.
- `summary`: accurate qualification/known-issue description.
- `assets`: exact filenames, display labels, and descriptions.

The current interface expects the Windows NSIS installer, desktop executable,
Python wheel/sdist, and `SHA256SUMS.txt`. `scripts/validate-release.mjs` runs
before every build and Node's built-in test runner checks invalid transitions.
If the asset contract changes, update the validator, tests, and public docs.
This validator does not replace verification that remote assets really exist.

Binaries belong on the fork's GitHub Releases, not in this project or the
Pages artifact. The download URL is constructed from the fixed fork repository,
validated tag, and validated filename only when status is published.

## Deployment

`.github/workflows/deploy-pages.yml` is named **Deploy documentation to GitHub
Pages**. It runs normal locked installation, metadata tests, typecheck, and
production build on website/workflow changes and manual dispatch. PRs build
without publishing; only `main` can upload/deploy. GitHub Pages must be configured
with GitHub Actions as its source. The deploy job uses the `github-pages`
environment and minimal Pages/OIDC permissions. No organization-root repository
or custom domain is changed.

The production URL/base path are explicit in `docusaurus.config.ts`.

## Attribution

New wiki/site content follows the repository's root Apache-2.0 license.
Upstream Unsloth authorship, Studio's AGPL-3.0 license, and vendored third-party
licenses remain intact. See `docs/licenses.md` for the public component map.
