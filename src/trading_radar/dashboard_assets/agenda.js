const radarAgenda = (() => {
  "use strict";
  function parisDay(instant) {
    const parts = new Intl.DateTimeFormat("en-GB", {timeZone:"Europe/Paris",year:"numeric",month:"2-digit",day:"2-digit"}).formatToParts(new Date(instant));
    const values = Object.fromEntries(parts.map((part) => [part.type,part.value]));
    return values.year + "-" + values.month + "-" + values.day;
  }
  function entries(jobs, now) {
    const today = parisDay(now); const items = [];
    for (const job of jobs) {
      const application = job.application || {};
      if (["Rejected","Withdrawn","Closed"].includes(application.status)) continue;
      if (application.next_action && /^\d{4}-\d{2}-\d{2}$/.test(application.next_action_date || "")) {
        items.push({job,day:application.next_action_date,kind:"action",text:application.next_action,overdue:application.next_action_date < today});
      }
      const deadline = job.deadline || {};
      if (job.is_active && ["New","Reviewing","To Apply"].includes(application.status || "New") &&
          ["date","instant"].includes(deadline.precision) && /^\d{4}-\d{2}-\d{2}$/.test(deadline.day || "")) {
        const expired = deadline.precision === "instant" && deadline.instant ? Date.parse(deadline.instant) < Date.parse(now) : deadline.day < today;
        items.push({job,day:deadline.day,kind:"deadline",text:expired ? "Date limite dépassée" : "Date limite de candidature",overdue:expired});
      }
    }
    return items.sort((a,b) => a.day.localeCompare(b.day) || a.kind.localeCompare(b.kind) || a.job.id.localeCompare(b.job.id));
  }
  return {parisDay,entries};
})();
if (typeof module !== "undefined" && module.exports) module.exports = radarAgenda;
