const test = require('node:test');
const assert = require('node:assert/strict');
const facts = require('../src/trading_radar/dashboard_assets/opportunity.js');
test('country facets include any advertised location and distinguish unknowns', () => {
  const countries = {countries:[{code:'GB'},{code:'FR'}]};
  assert.equal(facts.country(countries,'FR'),true);
  assert.equal(facts.country(countries,'US'),false);
  assert.equal(facts.country({countries:[]},'unknown'),true);
});
test('duration overlap excludes unknowns and conflicting evidence', () => {
  assert.equal(facts.duration({precision:'months',min_months:6,max_months:9},'six'),true);
  assert.equal(facts.duration({precision:'months',min_months:3,max_months:5},'long'),false);
  assert.equal(facts.duration({precision:'conflict'},'six'),false);
});
test('start windows are inclusive, preserve gaps, and exclude unknowns', () => {
  const start = {precision:'months',windows:[{from:'2027-01-01',to:'2027-01-31'},{from:'2027-04-01',to:'2027-04-30'}]};
  assert.equal(facts.start(start,'2027-01-31','2027-01-31'),true);
  assert.equal(facts.start(start,'2027-02-01','2027-03-31'),false);
  assert.equal(facts.start({precision:'unknown'},'2027-01-01',''),false);
  assert.equal(facts.start({precision:'conflict'},'2027-01-01',''),false);
  assert.equal(facts.start({precision:'unknown'},'',''),true);
});
