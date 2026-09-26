/* Calendar days shared by rendering, sorting and inclusive date filters. */
const radarPublication = (() => {
  "use strict";
  const day = (value) => {
    if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value) || value.startsWith("0000")) return null;
    const parsed = new Date(value + "T00:00:00Z");
    return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value ? value : null;
  };
  const label = (value) => day(value)
    ? new Date(value + "T00:00:00Z").toLocaleDateString("fr-FR", {day: "2-digit", month: "short", year: "numeric", timeZone: "UTC"})
    : "Non précisée";
  const compare = (left, right, oldestFirst = false) => {
    const a = day(left); const b = day(right);
    // Missing dates stay last in both directions; callers supply stable tie-breaks.
    if (!a || !b) return a ? -1 : b ? 1 : 0;
    if (a === b) return 0;
    return (a < b ? -1 : 1) * (oldestFirst ? 1 : -1);
  };
  const validRange = (from, to) => (!from || Boolean(day(from))) && (!to || Boolean(day(to))) && (!from || !to || from <= to);
  const within = (value, from, to) => {
    if (!validRange(from, to)) return false;
    if (!from && !to) return true;
    const published = day(value);
    return Boolean(published && (!from || published >= from) && (!to || published <= to));
  };
  return {day, label, compare, validRange, within};
})();
// Node is used only for development checks; exports remain self-contained HTML.
if (typeof module !== "undefined" && module.exports) module.exports = radarPublication;
