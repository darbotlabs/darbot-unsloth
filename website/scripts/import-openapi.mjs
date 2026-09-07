import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import {mkdirSync, readFileSync, renameSync, writeFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {resolve} from 'node:path';
import {parseArgs} from 'node:util';
import {validateOpenApi} from '../src/lib/openapi.mjs';
import {validateSnapshot} from './validate-openapi.mjs';

const {values, positionals} = parseArgs({
  allowPositionals: true,
  options: {
    'source-revision': {type: 'string'},
    'generated-at': {type: 'string'},
    'omitted-private-defaults': {type: 'string'},
    'capture-metadata': {type: 'string'},
  },
});
if (positionals.length !== 1 || !values['source-revision'] || !values['generated-at'] || !/^\d+$/.test(values['omitted-private-defaults'] ?? '')) {
  throw new Error('Usage: node scripts/import-openapi.mjs <sanitized-schema.json> --source-revision <40-character-installed-commit> --generated-at <ISO-timestamp> --omitted-private-defaults <count>');
}
const input = resolve(positionals[0]);
const bytes = readFileSync(input);
const release = JSON.parse(readFileSync(new URL('../src/data/release.json', import.meta.url), 'utf8'));
const document = JSON.parse(bytes.toString('utf8'));
const counts = validateOpenApi(document, release.pythonVersion);
const metadata = {
  status: 'ready',
  version: release.pythonVersion,
  title: document.info.title,
  openapi: document.openapi,
  schemaPath: 'api/openapi.json',
  sourceRepository: 'https://github.com/darbotlabs/darbot-unsloth',
  sourceRevision: values['source-revision'],
  generationContext: 'installed-package',
  generatedAt: values['generated-at'],
  license: 'AGPL-3.0-only',
  attribution: 'Generated from Unsloth Studio, originally by Unsloth AI; this fork is maintained by Darbot Labs.',
  omittedPrivateDefaults: Number(values['omitted-private-defaults']),
  sha256: createHash('sha256').update(bytes).digest('hex'),
  bytes: bytes.byteLength,
  counts,
};
if (values['capture-metadata']) {
  const capture = JSON.parse(readFileSync(resolve(values['capture-metadata']), 'utf8'));
  for (const key of ['sourceRevision', 'generatedAt', 'omittedPrivateDefaults', 'version', 'openapi', 'sha256', 'bytes']) {
    assert.equal(capture[key], metadata[key], `capture metadata does not match the schema/import inputs: ${key}`);
  }
  for (const key of ['paths', 'operations', 'schemas']) assert.equal(capture[key], counts[key], `capture count mismatch: ${key}`);
  metadata.wheelSha256 = capture.wheelSha256;
  metadata.omissions = capture.omissions;
  metadata.capture = capture.capture;
}
validateSnapshot(metadata, bytes, release.pythonVersion);
const destination = fileURLToPath(new URL('../static/api/openapi.json', import.meta.url));
const metadataPath = fileURLToPath(new URL('../src/data/api-reference.json', import.meta.url));
mkdirSync(fileURLToPath(new URL('../static/api/', import.meta.url)), {recursive: true});
// Preserve the reviewed artifact byte-for-byte; validation never repairs IDs or drops routes.
writeFileSync(`${destination}.pending`, bytes);
writeFileSync(`${metadataPath}.pending`, `${JSON.stringify(metadata, null, 2)}\n`);
renameSync(`${destination}.pending`, destination);
renameSync(`${metadataPath}.pending`, metadataPath);
console.log(`Imported complete OpenAPI snapshot: ${counts.operations} operations; SHA-256 ${metadata.sha256}.`);
