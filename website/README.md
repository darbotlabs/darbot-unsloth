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

## Local-only validation and publication status

**Repository GitHub Actions are disabled at the user's request.** Run installation,
tests, typecheck, production build, and browser verification locally using the
commands above. Do not dispatch or re-enable workflows, or use a branch push or
`npm run deploy` as a workaround for that instruction.

`.github/workflows/deploy-pages.yml`, named **Deploy documentation to GitHub
Pages**, is retained as an **inactive workflow definition**, not the current
execution path. It describes locked installation, validation, build, and the
previous Pages deployment arrangement. No change to that file enables repository
Actions or authorizes spending runner credits.

The already-published 25-page Pages site remains the live deployment.
`website/build/` is local output; a successful build or an API-schema import does
not publish it. New publication is pending an explicitly authorized path that
respects the disabled-Actions requirement. Do not assume a static branch push
bypasses GitHub Pages deployment workflows.

GitHub Releases asset uploads are a separate maintainer operation, not an Actions
run or a Pages deployment. The production URL/base path remain explicit in
`docusaurus.config.ts`; no organization-root repository or custom domain is changed.

## Installed-app OpenAPI reference

The API catalog is `/api-reference/`. It filters methods, paths, summaries,
descriptions, operation IDs, and tags locally; operation and model lists are
paginated. Request/response schemas, inherited parameters, declared security,
model properties, and complete JSON definitions are available without an external
API-docs framework or live request runner.

The complete public artifact belongs at `static/api/openapi.json`.
`src/data/api-reference.json` records its exact SHA-256, byte count, schema/API
versions, path/operation/model counts, generation timestamp, installed source
revision, omitted private-default count, and AGPL provenance. The page verifies
the fetched bytes before rendering. This schema is **not Apache-relicensed**.
The schema's `-text` Git attribute preserves these bytes on Windows checkouts
instead of converting line endings and invalidating the recorded digest.

### Refresh procedure

1. Finish rebuilding and installing the intended package. Obtain the actual
   application OpenAPI document from that installed version through the
   repository's verified capture process or its enabled `/openapi.json` endpoint.
   This website does not invent a backend extraction command or capture a
   developer checkout and call it an installed release.
2. Review privacy before import. Remove only the approved environment-local
   directory query defaults and record their count. Do not publish machine paths,
   credentials, user data, raw private logs, or unreviewed request examples.
   Do not remove operations/models or rewrite duplicate operation IDs; fix the
   source, rebuild/reinstall, and regenerate instead.
3. Record the actual installed source commit (full 40-character SHA), actual
   capture timestamp, and count of approved private-default omissions. From
   `website`, run the implemented import tool with those values:

   ```text
   node scripts/import-openapi.mjs <reviewed-sanitized-schema.json> --source-revision <installed-source-commit> --generated-at <capture-ISO-timestamp> --omitted-private-defaults <count>
   ```

   The angle-bracket values are required provenance inputs, not literal commands
   or invented defaults. The importer validates the schema against
   `release.json`'s Python version before writing anything, preserves the reviewed
   input bytes exactly, and updates the artifact plus metadata as a pair. Add
   `--capture-metadata <reviewed-capture-metadata.json>` when the capture includes
   a provenance sidecar: the importer cross-checks its identity, timestamp, hash,
   size, and counts, then retains the wheel checksum and exact reviewed omission
   locations. UTC timestamps ending in either `Z` or `+00:00` are retained
   verbatim, including fractional-second precision.
4. Run `npm test`, `npm run typecheck`, and `npm run build`. Prebuild checks reject
   duplicate/missing operation IDs, unresolved/external references, version drift,
   missing provenance, changed bytes, or incomplete operation/model counts.
   Verify filters, pagination, deep-linked selection, schema links, mobile layout,
   and the actual complete download in a browser. With the local production
   preview running and an isolated Chromium/Edge CDP page available, the checked-in
   browser regression can run without adding dependencies:

   ```text
   node scripts/check-api-browser.mjs --base-url http://127.0.0.1:3407/darbot-unsloth/ --debug-url http://127.0.0.1:9227
   ```

   The browser check only accepts loopback hosts. It exercises the real captured
   schema, filters, pagination, operation/model links, byte-for-byte download
   hash, 1920×1080 light mode, and 390×844 dark mode. Close the owned preview and
   isolated browser after validation; do not attach it to a personal browser
   profile or a production Studio instance.
5. Review the schema and metadata together and retain the validated local
   `build/` output for handoff. Repository Actions remain disabled; do not dispatch
   a Pages workflow or claim that the new catalog is live. Publication requires
   an explicitly authorized path consistent with that restriction. Schema capture
   is independent of `release.json` publication status and must not automatically
   enable desktop downloads.

Until a valid regenerated document is available, metadata remains
`awaiting-schema`, the static artifact must be absent, and no schema download is
offered. The previous duplicate-GET/HEAD-ID document must never be copied into
`static/` even temporarily.

## Attribution

New wiki/site content follows the repository's root Apache-2.0 license.
Upstream Unsloth authorship, Studio's AGPL-3.0 license, and vendored third-party
licenses remain intact. Generated Studio OpenAPI is AGPL-3.0-only and retains
upstream/fork provenance, independently of the website package's Apache label.
See `docs/licenses.md` for the public component map.
