(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const make = (tag, text, className) => {
    const element = document.createElement(tag);
    if (text !== undefined && text !== null) element.textContent = String(text);
    if (className) element.className = className;
    return element;
  };
  const number = (value) => Number(value || 0).toLocaleString("fr-FR");
  const date = (value, full = false) => {
    if (!value) return "Non renseigné";
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return "Date indisponible";
    return parsed.toLocaleString("fr-FR", full
      ? {day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit", timeZoneName: "short"}
      : {day: "2-digit", month: "short", year: "numeric"});
  };
  const statusLabels = {
    "New": "À découvrir", "Reviewing": "En revue", "To Apply": "À candidater",
    "Applied": "Postulé", "Online Assessment": "Test en ligne",
    "Video Interview": "Entretien vidéo", "Interview": "Entretien",
    "Final Round": "Dernier tour", "Offer": "Offre reçue", "Rejected": "Refus",
    "Withdrawn": "Retirée", "Closed": "Clôturée"
  };
  const healthLabels = {
    fresh: "À jour", recent_failure: "Échec récent", stale: "À actualiser",
    never_scanned: "Jamais collectée", invalid_timestamp: "Date invalide",
    healthy: "Sain", degraded: "À surveiller", critical: "À vérifier"
  };
  const statusLabel = (status) => statusLabels[status] || status || "Non renseigné";
  const healthBadge = (status) => make("span", healthLabels[status] || status || "Indisponible",
    "badge " + (["fresh", "healthy"].includes(status) ? "good" : ["recent_failure", "degraded"].includes(status) ? "warning" : "bad"));
  const safeURL = (value) => {
    if (typeof value !== "string") return null;
    try {
      const url = new URL(value);
      return ["https:", "http:"].includes(url.protocol) && !url.username && !url.password ? url.href : null;
    } catch (_) { return null; }
  };
  const fail = (message) => {
    $("fatal-error").hidden = false;
    $("fatal-error").textContent = message;
    $("metrics").hidden = true;
    $("jobs-view").hidden = true;
    $("health-view").hidden = true;
    $("trends-view").hidden = true;
    document.querySelectorAll(".nav-item").forEach((button) => { button.disabled = true; });
  };
  let data;
  try { data = JSON.parse($("radar-data").textContent); }
  catch (_) { fail("Cet instantané est illisible. Générez un nouvel export depuis Trading Job Radar."); return; }
  if (!data || data.status !== "ok" || !Array.isArray(data.jobs)) {
    fail(data && data.error && data.error.message || "Les données du radar sont indisponibles."); return;
  }
  const jobs = data.jobs;
  const editingEnabled = Boolean(data.editing && data.editing.enabled === true &&
    typeof data.editing.token === "string" && data.editing.token &&
    ["http:", "https:"].includes(location.protocol) && ["localhost", "127.0.0.1", "[::1]"].includes(location.hostname));
  if (editingEnabled) {
    $("workspace-mode").textContent = "Suivi local modifiable";
    $("tracking-mode").textContent = "SUIVI LOCAL MODIFIABLE";
    $("snapshot-refresh-help").textContent = "Suivi des candidatures synchronisé toutes les 10 secondes. Rechargez pour actualiser les offres et les sources.";
  }
  const summary = data.summary || {};
  const health = data.health || {};
  const state = {view: "jobs", page: 1};
  const pageSize = 25;
  const collator = new Intl.Collator("fr", {sensitivity: "base", numeric: true});
  const normalize = (value) => String(value || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  const searchText = new Map(jobs.map((job) => [job.id, normalize([job.title, job.company, job.location, job.country, job.source].join(" "))]));
  $("generated-at").textContent = date(data.generated_at, true);
  $("generated-at").dateTime = data.generated_at;
  $("nav-jobs").textContent = number(summary.total ?? jobs.length);
  const cards = [
    ["Offres actives", summary.active, "sur " + number(summary.total) + " offres repérées", "↗", "primary"],
    ["Offres prioritaires", summary.high_priority, "Actives · score ≥ 70 / 100", "◎", ""],
    ["Candidatures en cours", summary.applications_in_progress ?? jobs.filter((j) => !["New", "Rejected", "Withdrawn", "Closed"].includes((j.application || {}).status)).length, "Votre suivi de candidatures", "◫", ""],
    ["Sources à jour", (summary.fresh_sources ?? (health.source_summary || {}).fresh ?? 0) + " / " + (summary.enabled_sources ?? (health.sources || []).length), "Seuil : " + (health.max_age_hours || 24) + " h", "⌁", ""]
  ];
  cards.forEach(([label, value, note, symbol, style]) => {
    const card = make("article", null, "metric " + style);
    const icon = make("span", symbol, "metric-symbol"); icon.setAttribute("aria-hidden", "true");
    card.append(make("span", label, "metric-label"), make("strong", typeof value === "number" ? number(value) : value, "metric-value"), make("span", note, "metric-note"), icon);
    $("metrics").append(card);
  });
  if (Array.isArray(data.warnings) && data.warnings.length) {
    $("warnings").hidden = false;
    data.warnings.forEach((warning) => $("warnings").append(make("p", warning.message || warning.code || warning)));
  }
  const addOptions = (id, options, label = (value) => value) => {
    options.forEach((value) => { const option = make("option", label(value)); option.value = value; $(id).append(option); });
  };
  addOptions("company", [...new Set(jobs.map((job) => job.company))].sort(collator.compare));
  addOptions("application-status", [...new Set(jobs.map((job) => (job.application || {}).status || "New"))].sort(collator.compare), statusLabel);
  const scorePill = (score) => {
    const pill = make("span", number(score), "score-pill " + (score >= 70 ? "high" : score >= 55 ? "medium" : ""));
    pill.setAttribute("aria-label", "Score " + number(score) + " sur 100");
    const bar = make("span", null, "score-bar"); bar.setAttribute("aria-hidden", "true"); pill.append(bar);
    return pill;
  };
  const experience = (job) => {
    const value = job.experience;
    const years = value?.minimum_years;
    if (Number.isSafeInteger(years) && years >= 0 &&
        value.category === (years <= 2 ? "up_to_2" : "over_2")) return value;
    return {minimum_years: null, category: "unspecified"};
  };
  const evidenceMethods = {
    jump_coding_track_record: {origin: "description", kinds: ["professional", "industry_or_academia", "unspecified"], label: "Pratique du codage", source: "Déduit de la description"},
    ca_cib_experience_level: {origin: "employer_field", kinds: ["professional"], label: "Expérience indiquée", source: "Publié dans le champ d’expérience de l’employeur"},
    macquarie_sales_trading_experience: {origin: "description", kinds: ["professional"], label: "Expérience en sales trading", source: "Déduit de la description"},
    nomura_position_specifications: {origin: "description", kinds: ["professional"], label: "Expérience indiquée par Nomura", source: "Description employeur · Position Specifications → Experience"}
  };
  const experienceEvidence = (job) => {
    const evidence = job.experience?.evidence;
    if (!Array.isArray(evidence)) return [];
    return evidence.filter((item) => item && typeof item === "object" &&
      Number.isSafeInteger(item.minimum_years) && item.minimum_years >= 0 && item.minimum_years <= 99 &&
      typeof item.method === "string" && Object.hasOwn(evidenceMethods, item.method) &&
      evidenceMethods[item.method].kinds.includes(item.kind) &&
      item.origin === evidenceMethods[item.method].origin &&
      typeof item.excerpt === "string" && item.excerpt.trim().length > 0);
  };
  const evidenceLabel = (item) => {
    const context = {professional: "cadre professionnel", industry_or_academia: "industrie ou académie", unspecified: "cadre non précisé"};
    return evidenceMethods[item.method].label + " : au moins " + number(item.minimum_years) +
      (item.minimum_years === 1 ? " an" : " ans") + " (" + context[item.kind] + ")";
  };
  const experienceLabel = (job) => {
    const years = experience(job).minimum_years;
    if (years === null && experienceEvidence(job).some((item) => item.kind === "industry_or_academia")) {
      return "Minimum professionnel non reconnu";
    }
    return years === null ? "Minimum non reconnu" : "Minimum reconnu : " + number(years) + (years === 1 ? " an" : " ans");
  };
  const detailSection = (heading) => {
    const section = make("section", null, "detail-section"); section.append(make("h3", heading)); return section;
  };
  const applicationFields = [
    ["status", "Statut", "select"], ["application_date", "Date de candidature", "date"],
    ["recruiter", "Contact", "text", 500], ["next_action", "Prochaine action", "text", 2000],
    ["next_action_date", "Date de prochaine action", "date"], ["notes", "Notes", "textarea", 20000]
  ];
  let detailSession = null;
  let applicationEpoch = 0;
  const currentSession = (session) => detailSession === session && $("job-dialog").open;
  const actionButton = (label, action, primary = false) => {
    const button = make("button", label, primary ? "primary-button" : "secondary-button");
    button.type = "button"; button.addEventListener("click", action); return button;
  };
  function applicationValues(session) {
    return Object.fromEntries(applicationFields.map(([field]) => {
      const value = session.editor.elements.namedItem(field).value.trim();
      return [field, field === "status" ? value : value || null];
    }));
  }
  function dirtyEditor(session) {
    return Boolean(session.editor && JSON.stringify(applicationValues(session)) !== session.baseline);
  }
  function syncApplication(job, application) {
    applicationEpoch += 1;
    job.application = {...application};
    const selected = $("application-status").value;
    $("application-status").replaceChildren(make("option", "Tous les statuts"));
    $("application-status").firstElementChild.value = "";
    addOptions("application-status", [...new Set([...jobs.map((item) => (item.application || {}).status || "New"), ...(selected ? [selected] : [])])].sort(collator.compare), statusLabel);
    $("application-status").value = selected;
    const count = jobs.filter((item) => !["New", "Rejected", "Withdrawn", "Closed"].includes((item.application || {}).status || "New")).length;
    $("metrics").children[2].querySelector(".metric-value").textContent = number(count);
    if (detailSession && detailSession.job === job) detailSession.statusBadge.textContent = statusLabel(application.status);
    renderJobs();
  }
  let refreshingApplications = false;
  async function refreshApplications() {
    if (!editingEnabled || document.hidden || refreshingApplications || detailSession?.pending) return;
    refreshingApplications = true;
    const epoch = applicationEpoch;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 8000);
    try {
      const response = await fetch("/api/applications", {headers: {"X-Radar-Token": data.editing.token},
        signal: controller.signal, credentials: "omit", cache: "no-store", redirect: "error", referrerPolicy: "no-referrer"});
      const result = await response.json();
      if (!response.ok || result.status !== "ok" || !Array.isArray(result.applications)) throw new Error("Tracking unavailable");
      if (epoch !== applicationEpoch || detailSession?.pending) return;
      const byId = new Map(result.applications.map((application) => [application.job_id, application]));
      jobs.forEach((job) => {
        const application = byId.get(job.id);
        if (!application || !Object.hasOwn(statusLabels, application.status) ||
            applicationFields.every(([field]) => (job.application?.[field] ?? null) === (application[field] ?? null))) return;
        syncApplication(job, application);
        if (detailSession?.job === job && currentSession(detailSession)) {
          if (detailSession.editor) {
            detailSession.message.textContent = "Le suivi a changé depuis Telegram ou une autre fenêtre. Votre brouillon est conservé ; rechargez le suivi avant d’enregistrer.";
            detailSession.mustReload = true;
            detailSession.saveButton.disabled = true;
            if (!detailSession.reloadButton) {
              detailSession.reloadButton = actionButton("Recharger le suivi", () => confirmDiscard(detailSession, () => {
                detailSession.editor = null; detailSession.mustReload = false; renderTracking(detailSession); requestApplication(detailSession);
              }));
              detailSession.message.after(detailSession.reloadButton);
            }
          } else {
            detailSession.latest = null;
            renderTracking(detailSession, "Suivi actualisé automatiquement.");
          }
        }
      });
      $("snapshot-refresh-help").textContent = "Suivi synchronisé · " + new Date().toLocaleTimeString("fr-FR") + ". Rechargez pour actualiser les offres et les sources.";
    } catch (_) {
      $("snapshot-refresh-help").textContent = "Synchronisation du suivi indisponible. Nouvelle tentative automatique ; rechargez la page si le radar a redémarré.";
    } finally { clearTimeout(timer); refreshingApplications = false; }
  }
  function setPending(session, pending) {
    session.pending = pending;
    $("close-detail").disabled = pending;
    session.tracking.querySelectorAll("button, input, select, textarea").forEach((control) => { control.disabled = pending; });
    if (!pending && session.mustReload && session.saveButton) session.saveButton.disabled = true;
  }
  function confirmDiscard(session, action, close = false) {
    if (session.pending) return;
    if (!dirtyEditor(session) && !session.mustReload) { action(); return; }
    if (session.confirmation) { session.confirmation.querySelector("button").focus(); return; }
    const panel = make("div", null, "editor-confirmation");
    panel.setAttribute("role", "group"); panel.setAttribute("aria-label", "Confirmer l’abandon du brouillon");
    panel.append(make("p", session.mustReload ? "Le suivi doit être relu avant toute autre modification. Abandonner ce brouillon ?" : "Vous avez des modifications non enregistrées. Abandonner ce brouillon ?"));
    const keep = actionButton("Garder le brouillon", () => { panel.remove(); session.confirmation = null; session.editor?.querySelector("select").focus(); });
    panel.append(keep, actionButton(close ? "Abandonner et fermer" : "Abandonner le brouillon", () => { panel.remove(); session.confirmation = null; action(); }));
    session.confirmation = panel; session.tracking.prepend(panel); panel.scrollIntoView({block: "nearest"}); keep.focus();
  }
  function closeDetail() {
    const session = detailSession;
    if (!session) { $("job-dialog").close(); return; }
    confirmDiscard(session, () => {
      session.controller?.abort(); detailSession = null; $("job-dialog").close(); $("close-detail").disabled = false;
    }, true);
  }
  async function requestApplication(session, changes) {
    if (!editingEnabled || !currentSession(session) || session.pending) return;
    setPending(session, true);
    session.message.textContent = changes ? "Enregistrement du suivi local…" : "Lecture du suivi actuel…";
    session.message.className = "editor-message";
    const controller = new AbortController(); session.controller = controller;
    const timer = setTimeout(() => controller.abort(), 15000);
    try {
      const options = {method: changes ? "POST" : "GET", headers: {"X-Radar-Token": data.editing.token},
        signal: controller.signal, credentials: "omit", cache: "no-store", redirect: "error", referrerPolicy: "no-referrer"};
      if (changes) { options.headers["Content-Type"] = "application/json"; options.body = JSON.stringify({revision: session.revision, changes}); }
      const response = await fetch("/api/applications/" + encodeURIComponent(session.job.id), options);
      const result = await response.json();
      if (!currentSession(session)) return;
      if (!response.ok || result.status !== "ok") {
        const error = new Error(result.error?.message || "Le suivi n’a pas pu être consulté ou enregistré.");
        error.stale = response.status === 409;
        error.definitive = response.status >= 400 && response.status < 500;
        throw error;
      }
      if (!result.application || result.application.job_id !== session.job.id || typeof result.revision !== "string" ||
          !Object.hasOwn(statusLabels, result.application.status) || !Array.isArray(result.history)) throw new Error("Réponse du suivi indisponible.");
      session.revision = result.revision; session.latest = result; session.mustReload = false;
      session.editor = null; session.saveButton = null;
      syncApplication(session.job, result.application);
      setPending(session, false);
      renderTracking(session, changes ? "Suivi local enregistré. Aucune candidature n’a été envoyée." : "");
      if (!changes) renderApplicationEditor(session);
      else session.editButton.focus();
    } catch (error) {
      if (!currentSession(session)) return;
      if (changes && error.definitive && !error.stale) {
        session.message.textContent = error.message + " Votre brouillon est conservé.";
      } else if (changes) {
        // A transport failure cannot establish whether the server committed the save.
        session.mustReload = true;
        session.message.textContent = error.stale ? "Ce suivi a changé ailleurs. Votre brouillon est conservé ; rechargez le suivi avant de modifier à nouveau." :
          "L’enregistrement n’a pas pu être confirmé. Votre brouillon est conservé. Relisez le suivi avant toute nouvelle tentative.";
        if (!session.reloadButton) {
          session.reloadButton = actionButton("Recharger le suivi", () => confirmDiscard(session, () => {
            session.editor = null; session.mustReload = false; renderTracking(session); requestApplication(session);
          }));
          session.message.after(session.reloadButton);
        }
      } else session.message.textContent = "Le suivi actuel est indisponible. Réessayez avec « Modifier le suivi ».";
      session.message.className = "editor-message editor-error";
    } finally {
      clearTimeout(timer);
      if (currentSession(session)) setPending(session, false);
    }
  }
  function renderApplicationHistory(session) {
    if (!session.latest) return;
    const history = make("details", null, "application-history");
    const total = session.latest.history_total ?? session.latest.history.length;
    history.append(make("summary", "Historique du suivi · " + number(total) + (total === 1 ? " modification" : " modifications")));
    if (session.latest.history_truncated) history.append(make("p", "Les 50 modifications les plus récentes sont affichées."));
    if (!session.latest.history.length) history.append(make("p", "Aucune modification enregistrée."));
    session.latest.history.forEach((entry) => {
      const article = make("article", null, "application-history-entry"); article.append(make("strong", date(entry.changed_at, true)));
      const list = make("dl", null, "application-diff");
      applicationFields.forEach(([field, label]) => {
        const before = (entry.before || {})[field] ?? null; const after = (entry.after || {})[field] ?? null;
        if (before === after) return;
        const value = (item) => field === "status" ? statusLabel(item) : item || "Non renseigné";
        list.append(make("dt", label), make("dd", "Avant : " + value(before) + "\nAprès : " + value(after)));
      });
      article.append(list); history.append(article);
    });
    session.tracking.append(history);
  }
  function renderTracking(session, message = "") {
    const tracking = session.tracking; tracking.replaceChildren(); session.reloadButton = null; session.confirmation = null;
    tracking.append(make("h3", editingEnabled ? "Suivi de candidature · local" : "Suivi de candidature · lecture seule"));
    const trackingGrid = make("dl", null, "detail-grid"); const application = session.job.application || {};
    applicationFields.forEach(([field, label]) => {
      const value = field === "status" ? statusLabel(application[field]) : application[field];
      const wrap = make("div"); wrap.append(make("dt", label), make("dd", value || "Non renseigné")); trackingGrid.append(wrap);
    });
    tracking.append(trackingGrid);
    if (editingEnabled) {
      tracking.append(make("p", "Ce suivi reste dans votre radar local. Enregistrer un statut n’envoie aucune candidature.", "editor-help"));
      session.message = make("p", message, "editor-message"); session.message.setAttribute("role", "status"); session.message.setAttribute("aria-live", "polite");
      session.editButton = actionButton("Modifier le suivi", () => requestApplication(session), true);
      tracking.append(session.editButton, session.message); renderApplicationHistory(session);
    }
  }
  function renderApplicationEditor(session) {
    const form = make("form", null, "application-editor"); form.setAttribute("aria-label", "Modifier le suivi local");
    applicationFields.forEach(([field, label, type, limit]) => {
      const wrap = make("label", null, "application-field" + (type === "textarea" ? " wide" : "")); wrap.append(make("span", label));
      const input = make(type === "select" ? "select" : type === "textarea" ? "textarea" : "input");
      input.name = field; input.id = "edit-" + field;
      if (type === "select") Object.entries(statusLabels).forEach(([value, text]) => { const option = make("option", text); option.value = value; input.append(option); });
      else if (type !== "textarea") input.type = type;
      else input.rows = 5;
      if (type === "date") { input.min = "0001-01-01"; input.max = "9999-12-31"; }
      if (limit) input.maxLength = limit;
      input.value = session.latest.application[field] || (field === "status" ? "New" : "");
      input.autocomplete = "off"; wrap.append(input); form.append(wrap);
    });
    const buttons = make("div", null, "editor-actions");
    const save = make("button", "Enregistrer le suivi", "primary-button"); save.type = "submit"; session.saveButton = save;
    buttons.append(save, actionButton("Annuler", () => confirmDiscard(session, () => { session.editor = null; renderTracking(session); })));
    form.append(buttons); session.editor = form; session.baseline = JSON.stringify(applicationValues(session));
    form.addEventListener("submit", (event) => {
      event.preventDefault(); if (session.pending || session.mustReload || !currentSession(session)) return;
      const values = applicationValues(session); const nextAction = form.elements.namedItem("next_action");
      nextAction.setCustomValidity(values.next_action_date && !values.next_action ? "Renseignez la prochaine action ou effacez sa date." : "");
      if (!form.reportValidity()) return;
      const original = JSON.parse(session.baseline);
      const changes = Object.fromEntries(Object.entries(values).filter(([field, value]) => value !== original[field]));
      if (!Object.keys(changes).length) { session.message.textContent = "Aucune modification à enregistrer."; return; }
      requestApplication(session, changes);
    });
    form.addEventListener("input", () => form.elements.namedItem("next_action").setCustomValidity(""));
    session.editButton.hidden = true; session.message.before(form); form.querySelector("select").focus();
    form.scrollIntoView({block: "nearest"});
  }
  const educationLabels = {bachelor: "Bachelor / Licence", master: "Master", doctorate: "Doctorat", unspecified_level: "Diplôme sans niveau précis"};
  function educationLevels(job) {
    return ((job.education || {}).levels || []).filter((level) => Object.hasOwn(educationLabels, level));
  }
  function showDetail(job) {
    const content = $("job-detail"); content.replaceChildren();
    const title = make("h2", job.title); title.id = "detail-title";
    const top = make("div", null, "detail-top");
    const statusBadge = make("span", statusLabel((job.application || {}).status), "badge");
    top.append(scorePill(job.score), make("span", job.is_active ? "Offre active" : "Offre inactive", "badge"), statusBadge);
    content.append(title, make("p", [job.company, job.location].filter(Boolean).join(" · "), "detail-company"), top);
    const url = safeURL(job.apply_url);
    if (url) {
      const link = make("a", "Consulter l’offre officielle ↗", "official-link");
      link.href = url; link.target = "_blank"; link.rel = "noopener noreferrer";
      link.setAttribute("aria-label", "Consulter l’offre officielle (nouvel onglet)"); content.append(link);
    } else content.append(make("p", "Lien officiel indisponible.", "detail-company"));
    if (job.missions && job.missions.excerpts.length) {
      const missions = detailSection("Missions · extraits");
      missions.append(make("p", "Rubrique de l’annonce · " + job.missions.heading, "detail-company"));
      const excerpts = make("ul");
      job.missions.excerpts.forEach((excerpt) => excerpts.append(make("li", excerpt, "description")));
      missions.append(excerpts, make("p", "Jusqu’à trois extraits dans la langue de l’annonce. Consultez l’offre officielle pour l’ensemble des missions.", "detail-company"));
      content.append(missions);
    }
    const experienceSection = detailSection("Expérience");
    experienceSection.append(make("p", experienceLabel(job), "experience-minimum"));
    experienceEvidence(job).forEach((item) => {
      const evidence = make("div", null, "experience-evidence");
      evidence.append(make("p", evidenceLabel(item), "experience-practice"),
        make("p", evidenceMethods[item.method].source, "detail-company"),
        make("blockquote", item.excerpt, "description experience-excerpt"));
      if (item.kind === "industry_or_academia") {
        evidence.append(make("p", "Cette pratique peut inclure des travaux académiques ; elle n’établit pas un minimum d’expérience professionnelle."));
      }
      experienceSection.append(evidence);
    });
    experienceSection.append(make("p", "La détection d’un minimum dans l’annonce ne garantit pas votre éligibilité. Un minimum non reconnu ne signifie ni zéro année d’expérience ni l’absence d’exigence. Vérifiez les qualifications et les alternatives dans la description officielle."));
    content.append(experienceSection);
    const educationSection = detailSection("Diplômes mentionnés");
    const educationEvidence = ((job.education || {}).evidence || []);
    if (!educationEvidence.length) educationSection.append(make("p", "Aucune mention reconnue dans les critères pris en charge (DRW et IMC)."));
    educationEvidence.forEach((item) => {
      educationSection.append(make("p", "Critères de l’annonce · " + item.heading, "detail-company"),
        make("blockquote", item.excerpt, "description experience-excerpt"));
    });
    educationSection.append(make("p", "Ces mentions ne définissent pas un diplôme minimum. L’extrait conserve les alternatives, préférences et conditions de fin d’études. Vérifiez l’annonce officielle pour apprécier votre éligibilité."));
    content.append(educationSection);
    const timing = detailSection("Repères"); const grid = make("dl", null, "detail-grid");
    const deadline = job.deadline || {};
    const timingValues = [
      ["Première détection", date(job.first_seen, true)], ["Dernière observation", date(job.last_seen, true)],
      ["Échéance", deadline.precision === "instant" ? date(deadline.instant, true) : deadline.precision === "date" ? (deadline.day || "Non renseignée") + " · heure non précisée" : "Non confirmée"],
      ["Source", job.source || "Non renseignée"]
    ];
    timingValues.forEach(([label, value]) => { const wrap = make("div"); wrap.append(make("dt", label), make("dd", value)); grid.append(wrap); });
    timing.append(grid); content.append(timing);
    const scoring = detailSection("Pourquoi ce score ?"); const components = make("div", null, "score-components");
    const breakdown = job.score_breakdown || {};
    [["Trading", "trading", 30], ["Profil junior", "junior", 20], ["Démarrage", "start", 15], ["Front office", "front_office", 15], ["Classe d’actifs", "asset", 10], ["Adéquation profil", "profile_fit", 10]].forEach(([label, key, max]) => {
      const component = make("div", label, "component"); component.append(make("strong", (breakdown[key] || 0) + " / " + max)); components.append(component);
    });
    scoring.append(components);
    if (breakdown.reasons && breakdown.reasons.length) {
      const reasons = make("ul"); breakdown.reasons.forEach((reason) => reasons.append(make("li", reason))); scoring.append(reasons);
    }
    if (breakdown.exclusions && breakdown.exclusions.length) {
      scoring.append(make("p", "Critères d’exclusion (score ramené à zéro) :"));
      const excluded = make("ul"); breakdown.exclusions.forEach((reason) => excluded.append(make("li", reason))); scoring.append(excluded);
    }
    content.append(scoring);
    const tracking = detailSection("");
    detailSession = {job, tracking, statusBadge, pending: false}; renderTracking(detailSession); content.append(tracking);
    const description = detailSection("Description de l’offre"); description.append(make("p", job.description_text || "Aucune description disponible dans cet instantané.", "description")); content.append(description);
    content.append(make("p", "Identifiant · " + job.id, "detail-id"));
    $("job-dialog").showModal(); $("job-dialog").scrollTop = 0; $("close-detail").focus();
  }
  function renderJobs() {
    const query = normalize($("search").value.trim());
    const company = $("company").value; const score = Number($("score").value);
    const active = $("active").value; const application = $("application-status").value;
    const experienceCategory = $("experience").value;
    const education = $("education").value;
    let results = jobs.filter((job) =>
      (!query || searchText.get(job.id).includes(query)) && (!company || job.company === company) &&
      job.score >= score && (active === "all" || Boolean(job.is_active) === (active === "active")) &&
      (!application || (job.application || {}).status === application) &&
      (!experienceCategory || experience(job).category === experienceCategory) &&
      (!education || (education === "unrecognized" ? !educationLevels(job).length : educationLevels(job).includes(education))) &&
      (state.view !== "applications" || (job.application || {}).status !== "New")
    );
    const sorting = $("sort").value;
    const timestamp = (value) => { const stamp = Date.parse(value); return Number.isFinite(stamp) ? stamp : 0; };
    const deadlineTime = (job) => timestamp((job.deadline || {}).instant || (job.deadline || {}).day) || Number.MAX_SAFE_INTEGER;
    results.sort((a, b) => (sorting === "company" ? collator.compare(a.company, b.company) : sorting === "recent" ? timestamp(b.first_seen) - timestamp(a.first_seen) : sorting === "deadline" ? deadlineTime(a) - deadlineTime(b) : b.score - a.score) || collator.compare(a.title, b.title) || collator.compare(a.id, b.id));
    const pages = Math.max(1, Math.ceil(results.length / pageSize)); state.page = Math.min(state.page, pages);
    const start = (state.page - 1) * pageSize;
    $("job-rows").replaceChildren();
    results.slice(start, start + pageSize).forEach((job) => {
      const row = make("tr"); const jobCell = make("td");
      const button = make("button", job.title, "job-title"); button.type = "button"; button.addEventListener("click", () => showDetail(job));
      const companyLine = make("div", null, "company-line"); const initial = make("span", job.company.slice(0, 2).toUpperCase(), "company-initial"); initial.setAttribute("aria-hidden", "true");
      companyLine.append(initial, make("span", job.company)); if (!job.is_active) companyLine.append(make("span", "Inactive", "badge"));
      jobCell.append(button, companyLine, make("span", experienceLabel(job), "experience-indicator"));
      experienceEvidence(job).filter((item) => item.kind === "industry_or_academia").forEach((item) => {
        jobCell.append(make("span", evidenceLabel(item), "experience-indicator experience-practice"));
      });
      const degrees = educationLevels(job);
      if (degrees.length) jobCell.append(make("span", "Diplômes cités · " + degrees.map((level) => educationLabels[level]).join(" · "), "experience-indicator"));
      const scoreCell = make("td"); scoreCell.append(scorePill(job.score));
      const statusCell = make("td"); statusCell.append(make("span", statusLabel((job.application || {}).status), "badge"));
      const detailCell = make("td"); const detailButton = make("button", "↗", "arrow-button"); detailButton.type = "button"; detailButton.setAttribute("aria-label", "Détail : " + job.title + " chez " + job.company); detailButton.addEventListener("click", () => showDetail(job)); detailCell.append(detailButton);
      row.append(jobCell, make("td", job.location || "Non précisée", "location-cell"), scoreCell, statusCell, make("td", date(job.first_seen), "date-cell"), detailCell);
      $("job-rows").append(row);
    });
    $("empty-state").hidden = results.length > 0;
    const emptyText = $("empty-state").querySelector("p");
    emptyText.textContent = state.view === "applications" ? "Cette vue affiche les offres dont le suivi a quitté le statut « À découvrir ». Vous pouvez aussi élargir les filtres." : "Élargissez vos filtres ou recherchez un autre mot-clé.";
    $("result-count").textContent = number(results.length) + (results.length === 1 ? " offre" : " offres") + (state.view === "applications" ? (results.length === 1 ? " suivie" : " suivies") : " dans votre sélection");
    $("page-info").textContent = results.length ? (start + 1) + "–" + Math.min(start + pageSize, results.length) + " sur " + number(results.length) + " · Page " + state.page + " / " + pages : "0 offre";
    $("previous").disabled = state.page <= 1; $("next").disabled = state.page >= pages;
  }
  function renderHealth() {
    const badge = healthBadge(health.status); $("health-status").className = badge.className; $("health-status").textContent = badge.textContent;
    $("health-explanation").textContent = (editingEnabled ? "État calculé au chargement de la page. " : "État calculé lors de l’export. ") + "Une source est à jour si sa dernière collecte réussie date de moins de " + (health.max_age_hours || 24) + " heures, sans échec ultérieur. " + (editingEnabled ? "Rechargez la page pour actualiser toutes les données depuis votre radar local. Aucune collecte automatique." : "Les données ne s’actualisent pas automatiquement.");
    (health.sources || []).forEach((source) => {
      const row = make("tr"); const name = make("td"); name.append(make("span", source.company, "source-name"), make("span", source.source, "source-key"));
      const status = make("td"); status.append(healthBadge(source.status));
      if ((source.collection_conflicts || []).length) {
        const details = make("details", undefined, "collection-conflicts");
        details.append(make("summary", "Collecte dégradée · " + number(source.collection_conflicts.length) + " référence(s) exclue(s)"));
        const fieldLabels = { title: "Intitulé", description: "Description", location: "Lieu", date_posted: "Date de publication", employment_type: "Type de contrat" };
        source.collection_conflicts.forEach((conflict) => {
          details.append(make("p", "Référence " + conflict.external_id + " · Informations divergentes : " + conflict.fields.map((field) => fieldLabels[field] || field).join(", ")));
          conflict.urls.forEach((url) => details.append(make("p", url, "source-key")));
        });
        status.append(details);
      }
      const success = make("td", date(source.last_success, true));
      if (source.age_hours !== null && source.age_hours !== undefined) success.append(make("span", "Il y a " + number(Math.round(source.age_hours * 10) / 10) + " h", "source-key"));
      row.append(name, status, success, make("td", number(source.last_snapshot_jobs ?? source.last_count)), make("td", number(source.consecutive_failures))); $("source-rows").append(row);
    });
    const monitoring = data.monitoring || {};
    const snapshots = monitoring.snapshots || [];
    if (monitoring.status === "unavailable") $("health-history").append(make("p", "L’historique local est indisponible. " + ((monitoring.error || {}).message || ""), "history-empty"));
    else if (!snapshots.length) $("health-history").append(make("p", "Aucun rapport de santé enregistré. Cette vue affiche les rapports déjà présents dans le projet.", "history-empty"));
    snapshots.forEach((snapshot) => {
      const row = make("article", null, "history-row"); const description = make("div");
      description.append(make("strong", date(snapshot.recorded_at, true)), make("div", number((snapshot.source_summary || {}).fresh || 0) + " sources à jour · " + number((snapshot.issues || []).length) + " points à examiner", "history-meta"));
      row.append(description, healthBadge(snapshot.status)); $("health-history").append(row);
    });
  }
  const trendFields = ["new_jobs", "updates", "rescored", "closed", "reopened", "scans", "failed_sources"];
  const trendDate = (value) => new Date(value + "T00:00:00Z").toLocaleDateString("fr-FR", {day: "2-digit", month: "short", year: "numeric", timeZone: "UTC"});
  function renderTrends() {
    const trends = data.trends;
    const available = trends && trends.status === "ok" && Array.isArray(trends.daily) && trends.daily.every((day) => day &&
      /^\d{4}-\d{2}-\d{2}$/.test(day.date) && !Number.isNaN(Date.parse(day.date + "T00:00:00Z")) &&
      trendFields.every((field) => Number.isSafeInteger(day[field]) && day[field] >= 0));
    $("trend-unavailable").hidden = Boolean(available);
    $("trend-content").hidden = !available;
    $("trend-days").disabled = !available;
    if (!available) {
      $("trend-window").textContent = "L’historique des tendances n’est pas disponible dans cet instantané.";
      $("trend-unavailable").textContent = (trends && trends.error && trends.error.message) || "Générez un nouvel export pour inclure les tendances disponibles. Les autres vues restent consultables.";
      return;
    }
    const days = Number($("trend-days").value);
    const daily = trends.daily.slice(-days);
    const totals = Object.fromEntries(trendFields.map((field) => [field, daily.reduce((sum, day) => sum + day[field], 0)]));
    const activeDays = daily.filter((day) => trendFields.some((field) => day[field] > 0));
    $("trend-window").textContent = daily.length ? "Du " + trendDate(daily[0].date) + " au " + trendDate(daily[daily.length - 1].date) + " · " + daily.length + " jours calendaires en UTC · journée en cours incluse." : "Aucun jour d’historique disponible · UTC.";
    $("trend-metrics").replaceChildren();
    [
      ["Premières détections", totals.new_jobs, "Offres repérées pour la première fois", "primary"],
      ["Mises à jour de fiches", totals.updates, number(totals.rescored) + " recalculs de score séparés", ""],
      ["Scans enregistrés", totals.scans, "Exécutions de collecte sur la période", ""],
      ["Échecs de sources", totals.failed_sources, "Occurrences par scan · sources non uniques", ""]
    ].forEach(([label, value, note, style]) => {
      const card = make("article", null, "metric " + style);
      card.append(make("span", label, "metric-label"), make("strong", number(value), "metric-value"), make("span", note, "metric-note"));
      $("trend-metrics").append(card);
    });
    $("trend-empty").hidden = activeDays.length > 0;
    const detections = daily.filter((day) => day.new_jobs > 0);
    const chartDays = detections.slice(-14).reverse();
    const max = Math.max(1, ...detections.map((day) => day.new_jobs));
    $("trend-chart-description").textContent = detections.length ? "Les " + chartDays.length + " derniers jours avec détection sur cette période, du plus récent au plus ancien. Même échelle : " + number(max) + " offres. Les valeurs exactes sont indiquées à droite." : "Aucune première détection sur cette période.";
    $("trend-chart").replaceChildren();
    chartDays.forEach((day) => {
      const row = make("div", null, "trend-bar-row");
      const label = make("span", trendDate(day.date), "trend-bar-date");
      const bar = make("meter", null, "trend-meter");
      bar.min = 0; bar.max = max; bar.value = day.new_jobs;
      bar.setAttribute("aria-label", "Premières détections le " + trendDate(day.date) + " UTC");
      bar.setAttribute("aria-valuetext", number(day.new_jobs) + " offres");
      row.append(label, bar, make("strong", number(day.new_jobs), "trend-bar-value"));
      $("trend-chart").append(row);
    });
    $("trend-table-description").textContent = number(activeDays.length) + " jours avec activité sur " + daily.length + ". Tous sont affichés ci-dessous, du plus récent au plus ancien. Les jours sans activité sont omis.";
    $("trend-rows").replaceChildren();
    activeDays.slice().reverse().forEach((day) => {
      const row = make("tr");
      const label = make("th", trendDate(day.date)); label.scope = "row";
      row.append(label, ...trendFields.map((field) => make("td", number(day[field]))));
      $("trend-rows").append(row);
    });
  }
  function setView(view) {
    if (view !== state.view && view === "applications") $("active").value = "all";
    state.view = view; state.page = 1;
    document.querySelectorAll(".nav-item").forEach((button) => {
      const selected = button.dataset.view === view; button.classList.toggle("selected", selected);
      if (selected) button.setAttribute("aria-current", "page"); else button.removeAttribute("aria-current");
    });
    $("jobs-view").hidden = !["jobs", "applications"].includes(view); $("health-view").hidden = view !== "health"; $("trends-view").hidden = view !== "trends";
    $("metrics").hidden = view === "trends";
    const headings = {
      jobs: ["OFFRES", "Le marché, à votre portée.", "Repérez les offres pertinentes. Gardez le cap sur votre recherche."],
      applications: ["CANDIDATURES", "Chaque candidature compte.", "Consultez votre suivi, vos contacts et vos prochaines actions."],
      health: ["SANTÉ DES SOURCES", "La santé de votre veille.", "Vérifiez la fraîcheur des collectes et les derniers rapports locaux."],
      trends: ["TENDANCES", "Le rythme de votre veille.", "Suivez les détections, les changements et la fiabilité des collectes."]
    };
    ["breadcrumb-view", "page-title", "page-subtitle"].forEach((id, index) => { $(id).textContent = headings[view][index]; });
    $("results-heading").textContent = view === "applications" ? "Votre suivi de candidatures" : "Toutes les offres";
    if (["jobs", "applications"].includes(view)) renderJobs();
  }
  document.querySelectorAll(".nav-item").forEach((button) => button.addEventListener("click", () => setView(button.dataset.view)));
  $("filters").addEventListener("submit", (event) => event.preventDefault());
  $("trend-days").addEventListener("change", renderTrends);
  ["search", "company", "score", "active", "application-status", "experience", "education", "sort"].forEach((id) => $(id).addEventListener(id === "search" ? "input" : "change", () => { state.page = 1; renderJobs(); }));
  $("reset").addEventListener("click", () => { HTMLFormElement.prototype.reset.call($("filters")); if (state.view === "applications") $("active").value = "all"; $("sort").value = "score"; state.page = 1; renderJobs(); });
  $("previous").addEventListener("click", () => { state.page -= 1; renderJobs(); });
  $("next").addEventListener("click", () => { state.page += 1; renderJobs(); });
  $("close-detail").addEventListener("click", closeDetail);
  $("job-dialog").addEventListener("cancel", (event) => { event.preventDefault(); closeDetail(); });
  $("job-dialog").addEventListener("click", (event) => {
    if (event.target === $("job-dialog")) { const bounds = $("job-dialog").getBoundingClientRect(); if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) closeDetail(); }
  });
  renderJobs(); renderHealth(); renderTrends();
  if (editingEnabled) {
    setInterval(refreshApplications, 10000);
    document.addEventListener("visibilitychange", () => { if (!document.hidden) refreshApplications(); });
    refreshApplications();
  }
})();
