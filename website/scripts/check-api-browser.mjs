import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {parseArgs} from 'node:util';

const {values} = parseArgs({options: {
  'base-url': {type: 'string', default: 'http://127.0.0.1:3407/darbot-unsloth/'},
  'debug-url': {type: 'string', default: 'http://127.0.0.1:9227'},
}});
const baseUrl = new URL(values['base-url']);
const debugUrl = new URL(values['debug-url']);
for (const url of [baseUrl, debugUrl]) {
  assert.ok(['127.0.0.1', 'localhost', '[::1]'].includes(url.hostname), 'Browser checks are restricted to local servers');
}
const snapshot = JSON.parse(readFileSync(new URL('../src/data/api-reference.json', import.meta.url), 'utf8'));
const schema = JSON.parse(readFileSync(new URL('../static/api/openapi.json', import.meta.url), 'utf8'));
const operationId = schema.paths['/api/train/start'].post.operationId;
const target = (await (await fetch(new URL('/json/list', debugUrl))).json()).find((entry) => entry.type === 'page');
assert.ok(target, 'Open an isolated local browser with a CDP page first');
const socket = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((resolve, reject) => {
  socket.addEventListener('open', resolve, {once: true});
  socket.addEventListener('error', reject, {once: true});
});
let nextId = 0;
const pending = new Map();
const runtimeErrors = [];
const httpErrors = [];
socket.addEventListener('message', ({data}) => {
  const message = JSON.parse(data);
  if (message.id) {
    const request = pending.get(message.id);
    if (!request) return;
    clearTimeout(request.timer);
    pending.delete(message.id);
    message.error ? request.reject(new Error(JSON.stringify(message.error))) : request.resolve(message.result);
  }
  if (message.method === 'Runtime.exceptionThrown') runtimeErrors.push(message.params.exceptionDetails.text);
  if (message.method === 'Network.responseReceived' && message.params.response.status >= 400) {
    httpErrors.push(`${message.params.response.status} ${message.params.response.url}`);
  }
});
function call(method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = ++nextId;
    const timer = setTimeout(() => {pending.delete(id); reject(new Error(`CDP timeout: ${method}`));}, 15000);
    pending.set(id, {resolve, reject, timer});
    socket.send(JSON.stringify({id, method, params}));
  });
}
async function evaluate(expression) {
  const response = await call('Runtime.evaluate', {expression, returnByValue: true, awaitPromise: true});
  if (response.exceptionDetails) throw new Error(JSON.stringify(response.exceptionDetails));
  return response.result.value;
}
async function until(expression, label) {
  const deadline = Date.now() + 15000;
  while (Date.now() < deadline) {
    if (await evaluate(expression)) return;
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error(`Browser condition timed out: ${label}`);
}
async function navigate(query = '') {
  await call('Page.navigate', {url: new URL(`api-reference/${query}`, baseUrl).href});
  await until(`document.querySelector('main [aria-label="Operation catalog"]') !== null || document.querySelector('main [aria-label="Model catalog"]') !== null`, 'catalog loaded and verified');
}
async function search(text) {
  await evaluate(`(() => {const input = document.querySelector('main input[type="search"]'); input.focus(); input.select();})()`);
  await call('Input.insertText', {text});
}
async function clickText(text) {
  await evaluate(`[...document.querySelectorAll('main button')].find(button => button.textContent === ${JSON.stringify(text)}).click()`);
}
async function noOverflow() {
  assert.equal(await evaluate('document.documentElement.scrollWidth <= window.innerWidth'), true, 'page must not overflow the viewport');
}

try {
  await call('Page.enable');
  await call('Runtime.enable');
  await call('Network.enable');
  await call('Emulation.setDeviceMetricsOverride', {width: 1920, height: 1080, deviceScaleFactor: 1, mobile: false});
  await navigate();
  await evaluate(`localStorage.setItem('theme', 'light')`);
  await call('Page.reload');
  await until(`document.querySelector('main [aria-label="Operation catalog"]') && document.documentElement.dataset.theme === 'light'`, 'light mode');
  await noOverflow();
  assert.equal(await evaluate(`document.querySelectorAll('main button[aria-expanded]').length`), 25, 'operations are paginated');
  await evaluate(`document.querySelector('nav[aria-label="Operations pagination"] button:last-child').click()`);
  await until(`document.querySelector('nav[aria-label="Operations pagination"]').textContent.includes('Page 2')`, 'next page');

  await search('/api/train/status');
  await evaluate(`const controls = document.querySelectorAll('main select'); controls[0].value = 'GET'; controls[0].dispatchEvent(new Event('change', {bubbles: true}));`);
  await evaluate(`const control = document.querySelectorAll('main select')[1]; control.value = 'training'; control.dispatchEvent(new Event('change', {bubbles: true}));`);
  await until(`document.querySelector('main p[role="status"]').textContent.startsWith('1 of ')`, 'combined method/path/tag filters');
  assert.equal(await evaluate(`document.querySelector('main button[aria-expanded] code').textContent`), '/api/train/status');
  await search('no-such-operation-catalog-check');
  await until(`document.querySelector('main p[role="status"]').textContent.startsWith('0 of ')`, 'empty search');
  await clickText('Clear filters');
  await until(`document.querySelector('main p[role="status"]').textContent.startsWith('${snapshot.counts.operations} of ')`, 'clear filters');

  await navigate(`?operation=${encodeURIComponent(operationId)}`);
  await until(`document.querySelector('main button[aria-expanded="true"]')?.textContent === '/api/train/start'`, 'operation deep link');
  assert.match(await evaluate(`document.querySelector('main').textContent`), /Operation ID:/);
  await clickText('TrainingStartRequest');
  await until(`document.querySelector('section[aria-label="Schema TrainingStartRequest"]') !== null`, 'request-body model reference');
  await noOverflow();
  await search('TrainingStartRequest');
  const matchingModels = Object.keys(schema.components.schemas).filter((name) => name.toLowerCase().includes('trainingstartrequest')).length;
  await until(`document.querySelector('main p[role="status"]').textContent.startsWith('${matchingModels} of ')`, 'model name filter');
  await navigate('?schema=TrainingStartRequest');
  await until(`document.querySelector('section[aria-label="Schema TrainingStartRequest"]') !== null`, 'model deep link');
  assert.match(await evaluate(`document.querySelector('section[aria-label="Schema TrainingStartRequest"]').textContent`), /model_name/);

  const download = await evaluate(`(async () => {
    const link = document.querySelector('main a[download]');
    const response = await fetch(link.href, {credentials: 'omit'});
    const bytes = await response.arrayBuffer();
    const digest = await crypto.subtle.digest('SHA-256', bytes);
    return {path: new URL(link.href).pathname, bytes: bytes.byteLength,
      hash: [...new Uint8Array(digest)].map(byte => byte.toString(16).padStart(2, '0')).join('')};
  })()`);
  assert.equal(download.path, `${baseUrl.pathname}api/openapi.json`);
  assert.equal(download.bytes, snapshot.bytes);
  assert.equal(download.hash, snapshot.sha256);

  await call('Emulation.setDeviceMetricsOverride', {width: 390, height: 844, deviceScaleFactor: 1, mobile: true});
  await navigate();
  await evaluate(`localStorage.setItem('theme', 'dark')`);
  await call('Page.reload');
  await until(`document.querySelector('main [aria-label="Operation catalog"]') && document.documentElement.dataset.theme === 'dark'`, 'mobile dark mode');
  await noOverflow();
  await navigate(`?operation=${encodeURIComponent(operationId)}`);
  await until(`document.querySelector('main button[aria-expanded="true"]')?.textContent === '/api/train/start'`, 'mobile operation details');
  await noOverflow();
  await clickText('TrainingStartRequest');
  await until(`document.querySelector('section[aria-label="Schema TrainingStartRequest"]') !== null`, 'mobile model details');
  await noOverflow();
  assert.deepEqual(runtimeErrors, [], 'no browser runtime exceptions');
  assert.deepEqual(httpErrors, [], 'no failed HTTP responses');
  console.log(`PASS: ${snapshot.counts.operations} operations/${snapshot.counts.schemas} models; filters, pagination, deep links, reference navigation, full download hash; 1920x1080 light and 390x844 dark; no viewport overflow, runtime exceptions, or HTTP errors.`);
} finally {
  for (const request of pending.values()) clearTimeout(request.timer);
  socket.close();
}
