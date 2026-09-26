const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const context = vm.createContext({});
for (const name of ['publication.js', 'time.js']) {
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../src/trading_radar/dashboard_assets', name), 'utf8'), context);
}
const format = vm.runInContext('radarTime.date', context);

test('Paris midnight and seasonal offsets are independent of the computer timezone', () => {
  const original = process.env.TZ;
  try {
    for (const zone of ['UTC', 'Pacific/Honolulu', 'Europe/Paris', 'Pacific/Kiritimati']) {
      process.env.TZ = zone;
      for (const [value, day, clock, offset] of [
        ['2026-09-26T23:30:00Z', '27 sept. 2026', '01:30', 'UTC+2'],
        ['2026-12-26T23:30:00Z', '27 déc. 2026', '00:30', 'UTC+1'],
        ['2026-03-29T00:30:00Z', '29 mars 2026', '01:30', 'UTC+1'],
        ['2026-03-29T01:30:00Z', '29 mars 2026', '03:30', 'UTC+2'],
        ['2026-10-25T00:30:00Z', '25 oct. 2026', '02:30', 'UTC+2'],
        ['2026-10-25T01:30:00Z', '25 oct. 2026', '02:30', 'UTC+1'],
      ]) {
        assert.equal(format(value), day);
        const text = format(value, true);
        assert.ok(text.includes(clock) && text.includes(`Paris (${offset})`), text);
      }
      assert.equal(format('2026-09-26', true), '26 sept. 2026');
      assert.equal(format('2026-09-26T12:00:00', true), 'Date indisponible');
      assert.equal(format('broken', true), 'Date indisponible');
      assert.equal(format(null, true), 'Non renseigné');
    }
  } finally {
    if (original === undefined) delete process.env.TZ; else process.env.TZ = original;
  }
});
