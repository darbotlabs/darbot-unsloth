import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {existsSync, readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {resolve} from 'node:path';
import {validateOpenApi} from '../src/lib/openapi.mjs';

export function validateSnapshot(metadata, bytes, expectedVersion) {
  assert.equal(metadata.status, 'ready', 'API snapshot must be ready');
  assert.equal(metadata.version, expectedVersion, 'snapshot version must match the Python release');
  assert.equal(metadata.schemaPath, 'api/openapi.json', 'schema must stay in the fixed local artifact path');
  assert.equal(metadata.sourceRepository, 'https://github.com/darbotlabs/darbot-unsloth');
  assert.equal(metadata.license, 'AGPL-3.0-only', 'generated Studio schema retains its AGPL attribution');
  assert.match(metadata.sourceRevision ?? '', /^[a-f0-9]{40}$/, 'record the actual installed source revision');
  assert.equal(metadata.generationContext, 'installed-package');
  assert.match(metadata.generatedAt ?? '', /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)$/, 'generation timestamp must be an ISO UTC timestamp');
  assert.ok(Number.isFinite(Date.parse(metadata.generatedAt)), 'generation timestamp must be valid');
  assert.equal(new Date(metadata.generatedAt).toISOString().slice(0, 10), metadata.generatedAt.slice(0, 10), 'generation date must be valid');
  assert.ok(Number.isInteger(metadata.omittedPrivateDefaults) && metadata.omittedPrivateDefaults >= 0, 'disclose the count of omitted environment-local defaults');
  assert.equal(createHash('sha256').update(bytes).digest('hex'), metadata.sha256, 'snapshot bytes must match their recorded SHA-256');
  assert.equal(bytes.byteLength, metadata.bytes, 'snapshot byte count must match');
  const document = JSON.parse(bytes.toString('utf8'));
  const counts = validateOpenApi(document, expectedVersion);
  if (metadata.wheelSha256 !== undefined) assert.match(metadata.wheelSha256, /^[a-f0-9]{64}$/, 'wheel provenance must be a SHA-256');
  if (metadata.omissions !== undefined) {
    assert.ok(Array.isArray(metadata.omissions), 'omission locations must be an array');
    assert.equal(metadata.omissions.length, metadata.omittedPrivateDefaults, 'omission locations must match the disclosed count');
    const locations = new Set();
    for (const omission of metadata.omissions) {
      const key = `${omission.method}:${omission.path}:${omission.parameter}`;
      assert.ok(!locations.has(key), 'omission locations must be unique');
      locations.add(key);
      const operation = document.paths[omission.path]?.[omission.method];
      assert.ok(operation, `omitted default operation must still exist: ${key}`);
      const parameter = operation.parameters?.find((entry) => entry.name === omission.parameter && entry.in === 'query');
      assert.ok(parameter, `omitted default parameter must still exist: ${key}`);
      assert.notEqual(parameter.required, true, 'only reviewed optional query defaults may be omitted');
      assert.ok(!Object.hasOwn(parameter.schema ?? {}, 'default'), `private default is still present: ${key}`);
    }
  }
  assert.equal(metadata.title, document.info.title, 'API title must match the captured schema');
  assert.equal(metadata.openapi, document.openapi, 'OpenAPI format version must match the captured schema');
  assert.deepEqual(metadata.counts, counts, 'snapshot counts must match the complete document');
  return {document, counts};
}

export function validateCheckedInSnapshot() {
  const metadata = JSON.parse(readFileSync(new URL('../src/data/api-reference.json', import.meta.url), 'utf8'));
  const release = JSON.parse(readFileSync(new URL('../src/data/release.json', import.meta.url), 'utf8'));
  const artifact = new URL('../static/api/openapi.json', import.meta.url);
  if (metadata.status === 'awaiting-schema') {
    assert.equal(metadata.version, release.pythonVersion);
    assert.ok(!existsSync(artifact), 'an unvalidated artifact must not be present while the snapshot is awaiting regeneration');
    console.log('API reference is awaiting a valid regenerated schema; no schema is published.');
    return;
  }
  const {counts} = validateSnapshot(metadata, readFileSync(artifact), release.pythonVersion);
  console.log(`OpenAPI snapshot validated: ${counts.paths} paths, ${counts.operations} operations, ${counts.schemas} schemas.`);
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) validateCheckedInSnapshot();
