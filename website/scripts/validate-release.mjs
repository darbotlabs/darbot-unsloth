import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {resolve} from 'node:path';

export function validateRelease(release) {
  assert.ok(['preparing', 'published'].includes(release.status), 'status must be preparing or published');
  assert.match(release.desktopVersion, /^\d+\.\d+\.\d+$/, 'desktopVersion must be SemVer');
  assert.equal(release.tag, `v${release.desktopVersion}`, 'tag must match desktopVersion');
  assert.match(release.pythonVersion, /^\d{4}\.\d+\.\d+$/, 'pythonVersion must use the calendar version scheme');
  assert.equal(typeof release.desktopSigned, 'boolean', 'desktopSigned must be explicit');
  assert.ok(typeof release.summary === 'string' && release.summary.trim(), 'summary is required');
  if (release.status === 'published') {
    assert.match(release.publishedAt ?? '', /^\d{4}-\d{2}-\d{2}$/, 'published releases need a YYYY-MM-DD date');
    assert.equal(new Date(release.publishedAt).toISOString().slice(0, 10), release.publishedAt, 'publication date must be valid');
  } else {
    assert.equal(release.publishedAt, null, 'preparing releases must not have a publication date');
  }
  const expected = [
    `Unsloth_${release.desktopVersion}_x64-setup.exe`,
    'unsloth-studio.exe',
    `unsloth-${release.pythonVersion}-py3-none-any.whl`,
    `unsloth-${release.pythonVersion}.tar.gz`,
    'SHA256SUMS.txt',
  ];
  assert.ok(Array.isArray(release.assets), 'assets must be an array');
  assert.deepEqual(release.assets.map((asset) => asset.name).sort(), expected.sort(), 'asset names must match the release versions and checksum manifest');
  for (const asset of release.assets) {
    assert.ok(typeof asset.label === 'string' && asset.label.trim(), 'asset label is required');
    assert.ok(typeof asset.description === 'string' && asset.description.trim(), 'asset description is required');
  }
  return release;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  validateRelease(JSON.parse(readFileSync(new URL('../src/data/release.json', import.meta.url), 'utf8')));
  console.log('Release metadata is valid.');
}
