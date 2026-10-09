const radarProgramme = (() => {
  "use strict";
  const formats = {off_cycle: "Off-cycle", long: "Stage long", summer: "Summer Internship"};
  const kinds = {internship: "Stage", apprenticeship: "Alternance", discovery: "Discovery / Insight", graduate: "Graduate", vie: "VIE", unspecified: "Programme non précisé"};
  function label(observed) {
    const value = observed || {};
    const names = (value.formats || []).filter((format) => Object.hasOwn(formats, format)).map((format) => formats[format]);
    const text = names.length ? names.join(" / ") : kinds[value.kind] || kinds.unspecified;
    return text + (value.kind === "internship" ? " · " + (value.year_status === "conflict" ? "À vérifier" : value.year || "Année non précisée") : "");
  }
  function matches(observed, selected) {
    const value = observed || {};
    if (!selected) return true;
    if (selected === "off_cycle" || selected === "long" || selected === "summer") return value.kind === "internship" && (value.formats || []).includes(selected);
    if (selected === "unspecified_internship") return value.kind === "internship" && !(value.formats || []).length;
    return value.kind === selected;
  }
  function yearMatches(observed, selected) {
    if (!selected) return true;
    const value = observed || {};
    if (value.kind !== "internship") return false;
    if (selected === "unknown") return value.year_status === "unknown" && value.year == null;
    if (selected === "conflict") return value.year_status === "conflict";
    return /^20\d{2}$/.test(selected) && value.year_status === "confirmed" && value.year === Number(selected);
  }
  return {label, matches, yearMatches};
})();
if (typeof module !== "undefined" && module.exports) module.exports = radarProgramme;
