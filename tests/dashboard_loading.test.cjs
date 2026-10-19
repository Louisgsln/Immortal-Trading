const test = require('node:test');
const assert = require('node:assert/strict');
const loading = require('../src/trading_radar/dashboard_assets/loading.js');

const prefix = '/' + 'A'.repeat(43) + '/';
const place = {protocol: 'https:', origin: 'https://dashboard.example.com', pathname: prefix};
function shell() {
  return {format_version: 1, status: 'loading', live: true, jobs: [], editing: {
    enabled: true, mode: 'private', origin: place.origin,
    token: 'c'.repeat(64), api_base: prefix + 'api/applications'
  }};
}
function response(snapshot, overrides = {}) {
  return {ok: true, redirected: false, headers: new Headers({'content-type': 'application/json; charset=utf-8'}),
    json: async () => snapshot, ...overrides};
}

test('loads one complete snapshot with the existing private session', async () => {
  const initial = shell();
  let requests = 0;
  const snapshot = {format_version: 1, status: 'ok', jobs: [{id: 'one'}, {id: 'two'}],
    summary: {total: 2}, editing: {token: 'response-must-not-replace-session'}};
  const result = await loading.load(initial, place, async (url, options) => {
    requests++;
    assert.equal(url, prefix + 'api/snapshot');
    assert.equal(options.credentials, 'same-origin');
    assert.equal(options.headers['X-Radar-Token'], initial.editing.token);
    assert.equal(options.cache, 'no-store');
    assert.equal(options.redirect, 'error');
    assert.equal(options.referrerPolicy, 'no-referrer');
    assert.ok(options.signal instanceof AbortSignal);
    return response(snapshot);
  });
  assert.equal(requests, 1);
  assert.deepEqual(result.jobs, snapshot.jobs);
  assert.deepEqual(result.summary, {total: 2});
  assert.equal(result.editing, initial.editing);
  assert.equal(result.live, true);
});

for (const [label, mutation, location] of [
  ['another origin', value => {value.editing.origin = 'https://other.example';}, place],
  ['an external API', value => {value.editing.api_base = 'https://other.example/api/applications';}, place],
  ['another capability', value => {value.editing.api_base = '/' + 'B'.repeat(43) + '/api/applications';}, place],
  ['a forged token', value => {value.editing.token = 'wrong';}, place],
  ['disabled editing', value => {value.editing.enabled = false;}, place],
  ['an offline export', value => {value.status = 'ok';}, {...place, protocol: 'file:'}],
  ['plain HTTP', () => {}, {...place, protocol: 'http:'}],
  ['a different page', () => {}, {...place, pathname: '/another-page/'}]
]) {
  test('rejects ' + label + ' before any network request', async () => {
    const initial = shell(); mutation(initial);
    await assert.rejects(loading.load(initial, location, () => assert.fail('Unexpected request')),
      /invalid_private_snapshot/);
  });
}

for (const [label, value] of [
  ['failed', response({}, {ok: false})],
  ['redirected', response({}, {redirected: true})],
  ['HTML', response({}, {headers: new Headers({'content-type': 'text/html'})})],
  ['partial', response({format_version: 1, status: 'loading', jobs: []})],
  ['unsupported', response({format_version: 2, status: 'ok', jobs: []})],
  ['duplicate jobs', response({format_version: 1, status: 'ok', jobs: [{id: 'same'}, {id: 'same'}]})],
  ['invalid jobs', response({format_version: 1, status: 'ok', jobs: [null]})],
  ['too many jobs', response({format_version: 1, status: 'ok', jobs: Array.from({length: 5001}, (_, i) => ({id: String(i)}))})]
]) {
  test('does not display a ' + label + ' snapshot as complete', async () => {
    await assert.rejects(loading.load(shell(), place, async () => value), /snapshot_unavailable/);
  });
}

test('abort ends an interrupted load without a write or automatic replay', async () => {
  let requests = 0;
  await assert.rejects(loading.load(shell(), place, (_, options) => {
    requests++;
    return new Promise((resolve, reject) => {
      options.signal.addEventListener('abort', () => reject(new Error('aborted')), {once: true});
    });
  }, 5), /aborted/);
  assert.equal(requests, 1);
});

test('index.html and an empty but complete radar remain supported', async () => {
  const result = await loading.load(shell(), {...place, pathname: prefix + 'index.html'},
    async () => response({format_version: 1, status: 'ok', jobs: [], summary: {total: 0}}));
  assert.deepEqual(result.jobs, []);
  assert.equal(result.summary.total, 0);
});
