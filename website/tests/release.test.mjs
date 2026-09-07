import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {validateRelease} from '../scripts/validate-release.mjs';

const data = JSON.parse(readFileSync(new URL('../src/data/release.json', import.meta.url), 'utf8'));
const preparing = () => ({...structuredClone(data), status: 'preparing', publishedAt: null});

test('checked-in release data is valid', () => validateRelease(data));
test('preparing release does not claim a publication date', () => {
  assert.throws(() => validateRelease({...preparing(), publishedAt: '2026-09-07'}));
});
test('published release requires a real date', () => {
  assert.throws(() => validateRelease({...preparing(), status: 'published'}));
  assert.throws(() => validateRelease({...preparing(), status: 'published', publishedAt: '2026-02-31'}));
  validateRelease({...preparing(), status: 'published', publishedAt: '2026-09-07'});
});
test('release tag cannot drift from the desktop version', () => {
  assert.throws(() => validateRelease({...preparing(), tag: 'v9.0.0'}));
});
test('artifact versions and checksum manifest cannot drift', () => {
  const changed = preparing();
  changed.assets[0].name = 'Unsloth_0.1.0_x64-setup.exe';
  assert.throws(() => validateRelease(changed));
  assert.throws(() => validateRelease({...preparing(), assets: data.assets.slice(0, -1)}));
});
test('publication status cannot be invented', () => {
  assert.throws(() => validateRelease({...preparing(), status: 'ready'}));
});
