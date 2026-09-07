import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {catalogOperations, describeSchema, filterOperations, resolveReference, schemaNameFromReference, validateOpenApi} from '../src/lib/openapi.mjs';
import {validateCheckedInSnapshot, validateSnapshot} from '../scripts/validate-openapi.mjs';

function fixture() {
  return {
    openapi: '3.1.0',
    info: {title: 'Synthetic fixture, not an application endpoint', version: '2026.9.3'},
    paths: {
      '/fixture/items': {
        parameters: [{name: 'limit', in: 'query', schema: {type: 'integer'}}],
        get: {operationId: 'fixture_list', summary: 'List fixture entries', tags: ['fixture'], responses: {'200': {description: 'Fixture', content: {'application/json': {schema: {$ref: '#/components/schemas/Fixture'}}}}}},
        head: {operationId: 'fixture_head', summary: 'Inspect fixture headers', tags: ['fixture'], responses: {'200': {description: 'Fixture'}}},
      },
    },
    components: {schemas: {Fixture: {type: 'object', properties: {name: {type: 'string'}}}}},
  };
}
function snapshot(document = fixture()) {
  const bytes = Buffer.from(JSON.stringify(document));
  return {
    bytes,
    metadata: {
      status: 'ready', version: '2026.9.3', schemaPath: 'api/openapi.json',
      title: document.info.title, openapi: document.openapi,
      sourceRepository: 'https://github.com/darbotlabs/darbot-unsloth',
      sourceRevision: 'a'.repeat(40), generationContext: 'installed-package',
      generatedAt: '2026-09-07T08:00:00Z', license: 'AGPL-3.0-only',
      omittedPrivateDefaults: 3, bytes: bytes.byteLength,
      sha256: createHash('sha256').update(bytes).digest('hex'),
      counts: {paths: 1, operations: 2, schemas: 1},
    },
  };
}

test('checked-in API snapshot is valid or safely absent', validateCheckedInSnapshot);
test('Git preserves the checksum-pinned schema bytes on every checkout platform', () => {
  const attributes = readFileSync(new URL('../.gitattributes', import.meta.url), 'utf8');
  assert.match(attributes, /^static\/api\/openapi\.json -text$/m);
});
test('all HTTP methods have separate unique operation IDs', () => {
  assert.deepEqual(validateOpenApi(fixture(), '2026.9.3'), {paths: 1, operations: 2, schemas: 1});
  const invalid = fixture();
  invalid.paths['/fixture/items'].head.operationId = 'fixture_list';
  assert.throws(() => validateOpenApi(invalid, '2026.9.3'), /Duplicate operationId/);
});
test('missing operation ID and wrong installed version fail closed', () => {
  const invalid = fixture();
  delete invalid.paths['/fixture/items'].get.operationId;
  assert.throws(() => validateOpenApi(invalid, '2026.9.3'), /Missing operationId/);
  assert.throws(() => validateOpenApi(fixture(), '2026.9.4'), /API version/);
});
test('all local references resolve; external and broken references fail', () => {
  const invalid = fixture();
  invalid.components.schemas.Fixture.properties.name = {$ref: '#/components/schemas/Missing'};
  assert.throws(() => validateOpenApi(invalid, '2026.9.3'), /Unresolved/);
  invalid.components.schemas.Fixture.properties.name.$ref = 'https://example.invalid/schema.json';
  assert.throws(() => validateOpenApi(invalid, '2026.9.3'), /External/);
});
test('JSON pointer escaping is respected without following prototype properties', () => {
  const document = {components: {schemas: {'A/B~C': {type: 'string'}}}};
  assert.equal(resolveReference(document, '#/components/schemas/A~1B~0C').type, 'string');
  assert.equal(schemaNameFromReference('#/components/schemas/A~1B~0C'), 'A/B~C');
  assert.throws(() => resolveReference(document, '#/components/schemas/toString'), /Unresolved/);
});
test('snapshot hash, operation counts, provenance and AGPL identity must agree', () => {
  const {metadata, bytes} = snapshot();
  validateSnapshot(metadata, bytes, '2026.9.3');
  assert.throws(() => validateSnapshot(metadata, Buffer.concat([bytes, Buffer.from(' ')]), '2026.9.3'), /SHA-256/);
  assert.throws(() => validateSnapshot({...metadata, counts: {...metadata.counts, operations: 1}}, bytes, '2026.9.3'), /counts/);
  assert.throws(() => validateSnapshot({...metadata, license: 'Apache-2.0'}, bytes, '2026.9.3'), /AGPL/);
  assert.throws(() => validateSnapshot({...metadata, sourceRevision: 'unknown'}, bytes, '2026.9.3'), /revision/);
  assert.throws(() => validateSnapshot({...metadata, title: 'Wrong application'}, bytes, '2026.9.3'), /title/);
  assert.throws(() => validateSnapshot({...metadata, generatedAt: '2026-02-31T08:00:00Z'}, bytes, '2026.9.3'), /date/);
});
test('catalog filters combine words, method and tag case-insensitively for search', () => {
  const operations = catalogOperations(fixture());
  assert.equal(filterOperations(operations, 'FIXTURE list', 'GET', 'fixture').length, 1);
  assert.equal(filterOperations(operations, 'list', 'HEAD', 'fixture').length, 0);
  assert.equal(filterOperations(operations, '', '', 'missing').length, 0);
  assert.equal(operations[0].parameters[0].name, 'limit');
});
test('schema summaries retain nullable unions and references', () => {
  assert.equal(describeSchema({anyOf: [{type: 'string'}, {type: 'null'}]}), 'string | null');
  assert.equal(describeSchema({type: 'array', items: {$ref: '#/components/schemas/Fixture'}}), 'Array of Fixture');
});
test('capture timestamps retain UTC offsets and microseconds without rewriting provenance', () => {
  const {metadata, bytes} = snapshot();
  validateSnapshot({...metadata, generatedAt: '2026-09-07T09:11:35.643797+00:00'}, bytes, '2026.9.3');
});
test('reviewed private-default omissions preserve optional query parameters', () => {
  const document = fixture();
  document.paths['/fixture/items'].get.parameters = [{name: 'directory', in: 'query', required: false, schema: {type: 'string'}}];
  const {metadata, bytes} = snapshot(document);
  const record = {...metadata, omittedPrivateDefaults: 1, omissions: [{path: '/fixture/items', method: 'get', parameter: 'directory'}]};
  validateSnapshot(record, bytes, '2026.9.3');
  assert.throws(() => validateSnapshot({...record, omittedPrivateDefaults: 2}, bytes, '2026.9.3'), /disclosed count/);
  assert.throws(() => validateSnapshot({...record, omissions: [{path: '/fixture/items', method: 'get', parameter: 'missing'}]}, bytes, '2026.9.3'), /parameter must still exist/);
});
test('hundreds of operations remain complete and can be narrowed without mutating the schema', () => {
  const document = fixture();
  for (let index = 0; index < 500; index++) {
    document.paths[`/fixture/batch/${index}`] = {
      post: {operationId: `fixture_batch_${index}`, summary: `Synthetic batch ${index}`, tags: [index % 2 ? 'odd' : 'even'], responses: {'200': {description: 'Fixture'}}},
    };
  }
  const before = JSON.stringify(document);
  const entries = catalogOperations(document);
  assert.equal(entries.length, 502);
  assert.equal(filterOperations(entries, '', 'POST', 'odd').length, 250);
  assert.equal(filterOperations(entries, 'batch 499', 'POST', 'odd').length, 1);
  assert.equal(JSON.stringify(document), before);
});
