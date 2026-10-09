const radarCalendar = (() => {
  "use strict";
  const encoder = new TextEncoder();
  function day(value) {
    return typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value) && Number(value.slice(0,4)) > 0 &&
      Number.isFinite(Date.parse(value)) && new Date(value).toISOString().slice(0,10) === value;
  }
  function utc(value) {
    if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?(?:Z|[+-]\d{2}:\d{2})$/.test(value) ||
        !day(value.slice(0,10)) || Number(value.slice(11,13)) > 23 || !Number.isFinite(Date.parse(value))) return null;
    const iso = new Date(value).toISOString();
    return /^\d{4}-/.test(iso) ? iso.replace(/[-:]/g,"").replace(/\.\d{3}Z$/,"Z") : null;
  }
  function escape(value) {
    return String(value ?? "").replace(/\r\n?/g,"\n").replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/g,"")
      .replace(/\\/g,"\\\\").replace(/\n/g,"\\n").replace(/;/g,"\\;").replace(/,/g,"\\,");
  }
  function fold(value) {
    const lines = [];let current = "",length = 0;
    for (const character of value) {
      const bytes = encoder.encode(character).length;
      if (length + bytes > 75) {lines.push(current);current = " ";length = 1;}
      current += character;length += bytes;
    }
    lines.push(current);return lines.join("\r\n");
  }
  function build(entries, now) {
    const stamp = utc(now);if (!stamp) throw new Error("Invalid calendar time");
    const lines = ["BEGIN:VCALENDAR","VERSION:2.0","PRODID:-//Trading Job Radar//Echeances//FR","CALSCALE:GREGORIAN","METHOD:PUBLISH"];
    const seen = new Set();let count = 0;
    for (const entry of entries) {
      const job = entry.job || {};
      if (!["action","deadline"].includes(entry.kind) || typeof job.id !== "string" || !/^[A-Za-z0-9_-]{1,128}$/.test(job.id) || !day(entry.day)) continue;
      const uid = "radar-" + encodeURIComponent(job.id) + "-" + entry.kind + "@trading-radar.local";
      if (seen.has(uid)) continue;
      let dates;
      if (entry.kind === "deadline" && job.deadline?.precision === "instant") {
        const instant = utc(job.deadline.instant);if (!instant) continue;
        dates = ["DTSTART:" + instant];
      } else {
        if (entry.kind === "deadline" && job.deadline?.precision !== "date") continue;
        const end = new Date(entry.day + "T12:00:00Z");end.setUTCDate(end.getUTCDate() + 1);
        const until = end.toISOString().slice(0,10);if (!day(until)) continue;
        dates = ["DTSTART;VALUE=DATE:" + entry.day.replace(/-/g,""),"DTEND;VALUE=DATE:" + until.replace(/-/g,"")];
      }
      const label = entry.kind === "action" ? "Action : " + entry.text : "Date limite de candidature";
      lines.push("BEGIN:VEVENT","UID:" + uid,"DTSTAMP:" + stamp,...dates,
        "SUMMARY:" + escape(label + " · " + (job.company || "") + " · " + (job.title || "")),
        "DESCRIPTION:" + escape((entry.kind === "action" ? entry.text + "\n" : "Date limite annoncée par l’employeur.\n") + (job.company || "") + "\n" + (job.title || "")),
        "CLASS:PRIVATE","TRANSP:TRANSPARENT","END:VEVENT");
      seen.add(uid);count += 1;
    }
    lines.push("END:VCALENDAR");return {text:lines.map(fold).join("\r\n") + "\r\n",count};
  }
  return {build};
})();
if (typeof module !== "undefined" && module.exports) module.exports = radarCalendar;
