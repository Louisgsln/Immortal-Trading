const {test} = require("node:test");
const assert = require("node:assert/strict");
const {execFileSync} = require("node:child_process");
const modulePath = require.resolve("../src/trading_radar/dashboard_assets/publication.js");
const publication = require(modulePath);

test("newest and oldest order across months and years, with unknown dates always last", () => {
  const dates = [null, "2025-12-31", "2026-09-01", undefined, "2026-01-01", "invalid"];
  // Job objects keep undefined dates inside the comparator, as in the dashboard.
  const jobs = dates.map((value) => ({publication_day: value}));
  for (const oldest of [false, true]) {
    const sorted = jobs.toSorted((a, b) => publication.compare(a.publication_day, b.publication_day, oldest));
    assert.deepEqual(sorted.slice(0, 3).map((job) => job.publication_day), oldest
      ? ["2025-12-31", "2026-01-01", "2026-09-01"]
      : ["2026-09-01", "2026-01-01", "2025-12-31"]);
    assert.ok(sorted.slice(3).every((job) => !publication.day(job.publication_day)));
  }
});

test("same-day and unknown dates leave tie-breaking to title and ID", () => {
  for (const oldest of [false, true]) {
    assert.equal(publication.compare("2026-09-01", "2026-09-01", oldest), 0);
    assert.equal(publication.compare(null, undefined, oldest), 0);
  }
});

test("inclusive period and single-day bounds exclude undated offers", () => {
  for (const value of ["2026-09-01", "2026-09-15", "2026-09-30"]) {
    assert.equal(publication.within(value, "2026-09-01", "2026-09-30"), true);
  }
  for (const value of ["2026-08-31", "2026-10-01", null, undefined]) {
    assert.equal(publication.within(value, "2026-09-01", "2026-09-30"), false);
  }
  assert.equal(publication.within("2026-09-01", "2026-09-01", "2026-09-01"), true);
});

test("one-sided bounds and reset retain their own semantics", () => {
  assert.equal(publication.within("2026-09-01", "2026-09-01", ""), true);
  assert.equal(publication.within("2026-09-02", "", "2026-09-01"), false);
  assert.equal(publication.within("2026-09-01", "", "2026-09-01"), true);
  assert.equal(publication.within(null, "2026-09-01", ""), false);
  assert.equal(publication.within(null, "", "2026-09-01"), false);
  assert.equal(publication.within(null, "", ""), true);
  assert.equal(publication.within("2026-09-01", "", ""), true);
});

test("invalid and reversed periods are rejected", () => {
  assert.equal(publication.validRange("", ""), true);
  assert.equal(publication.validRange("2026-09-01", "2026-09-01"), true);
  for (const bounds of [["2026-09-02", "2026-09-01"], ["bad", ""], ["", "2026-02-30"]]) {
    assert.equal(publication.validRange(...bounds), false);
    assert.equal(publication.within("2026-09-01", ...bounds), false);
  }
});

test("impossible calendar dates, instants and unsupported values stay unknown", () => {
  for (const value of ["2026-02-29", "2026-04-31", "0000-01-01", "2026-13-01", "2026-9-1", "2026-09-01T12:00:00Z", null, undefined, 0, {}]) {
    assert.equal(publication.day(value), null);
    assert.equal(publication.label(value), "Non précisée");
  }
  assert.equal(publication.day("2024-02-29"), "2024-02-29");
});

for (const zone of ["UTC", "Pacific/Honolulu", "Europe/Paris", "Pacific/Kiritimati"]) {
  test(`labels and period boundaries keep the same calendar day in ${zone}`, () => {
    const result = execFileSync(process.execPath, ["-e", `
      const p = require(process.argv[1]);
      console.log(JSON.stringify([p.label("2026-09-01"), p.within("2026-09-01", "2026-09-01", "2026-09-01")]));
    `, modulePath], {env: {...process.env, TZ: zone}, encoding: "utf8"});
    assert.deepEqual(JSON.parse(result), ["01 sept. 2026", true]);
  });
}
