const {test} = require("node:test");
const assert = require("node:assert/strict");
const programme = require("../src/trading_radar/dashboard_assets/programme.js");

test("programme filters distinguish stage formats and missing facts", () => {
  const offCycle = {kind: "internship", formats: ["off_cycle", "long"], year: 2027, year_status: "confirmed"};
  for (const filter of ["", "internship", "off_cycle", "long"]) assert.equal(programme.matches(offCycle, filter), true);
  for (const filter of ["summer", "graduate", "unspecified_internship"]) assert.equal(programme.matches(offCycle, filter), false);
  assert.equal(programme.matches({kind: "internship", formats: []}, "unspecified_internship"), true);
  assert.equal(programme.matches({kind: "graduate", formats: ["long"]}, "long"), false);
  assert.equal(programme.matches(null, "internship"), false);
});

test("unknown and conflicting dates are explicit", () => {
  assert.equal(programme.label({kind: "internship", formats: ["off_cycle"], year: 2027, year_status: "confirmed"}), "Off-cycle · 2027");
  assert.equal(programme.label({kind: "internship", formats: []}), "Stage · Année non précisée");
  assert.equal(programme.label({kind: "internship", formats: ["long"], year: 2027, year_status: "conflict"}), "Stage long · À vérifier");
  assert.equal(programme.label({kind: "graduate"}), "Graduate");
});

test("programme year works without a start month and keeps missing or conflicting facts separate", () => {
  const confirmed = {kind:"internship",year:2027,year_status:"confirmed"};
  assert.equal(programme.yearMatches(confirmed,"2027"),true);
  assert.equal(programme.yearMatches(confirmed,"2026"),false);
  assert.equal(programme.yearMatches(confirmed,"unknown"),false);
  assert.equal(programme.yearMatches({...confirmed,year_status:"conflict"},"2027"),false);
  assert.equal(programme.yearMatches({...confirmed,year_status:"conflict"},"conflict"),true);
  assert.equal(programme.yearMatches({kind:"internship",year:null,year_status:"unknown"},"unknown"),true);
  assert.equal(programme.yearMatches({kind:"graduate",year:2027,year_status:"confirmed"},"2027"),false);
  assert.equal(programme.yearMatches(null,""),true);
  for (const invalid of ["NaN","2027foo"," 2027","-2027","2027.0"]) assert.equal(programme.yearMatches(confirmed,invalid),false);
});
