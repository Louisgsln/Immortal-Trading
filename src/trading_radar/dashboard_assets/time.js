/* Explicit Paris time, independent of the device's timezone. */
const radarTime = (() => {
  "use strict";
  const date = (value, full = false) => {
    if (!value) return "Non renseigné";
    // Calendar-only values are not instants: preserve their written day.
    if (typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value)) return radarPublication.label(value);
    if (typeof value !== "string" || !/T.*(?:Z|[+-]\d{2}:\d{2})$/.test(value)) return "Date indisponible";
    const parsed = new Date(value);
    if (!Number.isFinite(parsed.getTime())) return "Date indisponible";
    const options = {day: "2-digit", month: "short", year: "numeric", timeZone: "Europe/Paris"};
    if (full) Object.assign(options, {hour: "2-digit", minute: "2-digit"});
    return parsed.toLocaleString("fr-FR", options);
  };
  return {date};
})();
if (typeof module !== "undefined" && module.exports) module.exports = radarTime;
