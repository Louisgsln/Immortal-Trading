const radarOpportunity = (() => {
  "use strict";
  function country(facts, selected) {
    if (!selected) return true;
    if (selected === "unknown") return !(facts?.countries || []).length;
    return (facts?.countries || []).some((item) => item.code === selected);
  }
  function duration(facts, selected) {
    if (!selected) return true;
    if (selected === "unknown") return !facts || facts.precision !== "months";
    if (facts?.precision !== "months") return false;
    const bands = {short: [1, 5], six: [6, 6], long: [6, 12], over_twelve: [13, 24]};
    const range = bands[selected];
    return !!range && facts.min_months <= range[1] && facts.max_months >= range[0];
  }
  function start(facts, from, to) {
    if (!from && !to) return true;
    if (!facts || !["day", "months", "year"].includes(facts.precision)) return false;
    return (facts.windows || []).some((window) => (!from || window.to >= from) && (!to || window.from <= to));
  }
  function durationLabel(facts) {
    if (facts?.precision === "conflict") return "Durée à vérifier";
    if (facts?.precision !== "months") return "Durée non précisée";
    return (facts.min_months === facts.max_months ? String(facts.min_months) : facts.min_months + "–" + facts.max_months) + " mois";
  }
  function startLabel(facts) {
    if (!facts || facts.precision === "unknown") return "Début non précisé";
    if (facts.precision === "conflict") return "Début à vérifier";
    if (facts.precision === "day") return facts.windows[0].from;
    if (facts.precision === "year") return facts.year + " · mois non précisé";
    const names = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"];
    return (facts.months || []).map((month) => names[month - 1]).join(", ") + " " + facts.year;
  }
  return {country, duration, start, durationLabel, startLabel};
})();
if (typeof module !== "undefined" && module.exports) module.exports = radarOpportunity;
