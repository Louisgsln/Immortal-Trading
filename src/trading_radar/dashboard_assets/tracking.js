const radarTracking = (() => {
  "use strict";
  function addDays(day, count) {
    const instant = new Date(day + "T12:00:00Z");
    instant.setUTCDate(instant.getUTCDate() + count);
    return instant.toISOString().slice(0, 10);
  }
  function shortcuts(job, application, now) {
    const today = radarAgenda.parisDay(now);
    const actions = [];
    if (job.is_active && !job.is_expired && ["New", "Reviewing", "To Apply"].includes(application.status)) {
      actions.push({id:"prepare", label:"Préparer la candidature", changes:{status:"To Apply", next_action:"Préparer et envoyer la candidature", next_action_date:today}});
    }
    if (application.status === "Applied") {
      actions.push({id:"followup", label:"Relance dans 7 jours", changes:{next_action:"Relancer le recrutement", next_action_date:addDays(today, 7)}});
    }
    if (application.next_action) {
      actions.push({id:"complete", label:"Action terminée", changes:{next_action:null, next_action_date:null}});
    }
    return actions;
  }
  return {shortcuts};
})();
if (typeof module !== "undefined" && module.exports) module.exports = radarTracking;
