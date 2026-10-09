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
  const date = radarTime.date;
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
    partial: "Collecte partielle", collection_degraded: "Références contradictoires", access_restricted: "Accès bloqué · CAPTCHA",
    healthy: "Sain", degraded: "À surveiller", critical: "À vérifier"
  };
  const statusLabel = (status) => statusLabels[status] || status || "Non renseigné";
  const healthBadge = (status) => make("span", healthLabels[status] || status || "Indisponible",
    "badge " + (["fresh", "healthy"].includes(status) ? "good" : ["recent_failure", "degraded", "partial", "collection_degraded", "access_restricted"].includes(status) ? "warning" : "bad"));
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
    $("agenda-view").hidden = true;
    document.querySelectorAll(".nav-item").forEach((button) => { button.disabled = true; });
  };
  let data;
  try { data = JSON.parse($("radar-data").textContent); }
  catch (_) { fail("Cet instantané est illisible. Générez un nouvel export depuis Trading Job Radar."); return; }
  if (!data || data.status !== "ok" || !Array.isArray(data.jobs)) {
    fail(data && data.error && data.error.message || "Les données du radar sont indisponibles."); return;
  }
  const jobs = data.jobs;
  if (data.services) {
    const watcher = data.services.watcher || {};
    const labels = {active:"Radar actif", stale:"Signal du radar ancien", stopped:"Radar arrêté", long_scan:"Collecte prolongée · à vérifier", unknown:"Activité du radar à vérifier"};
    $("service-overview").hidden = false;
    $("watcher-summary").textContent = (labels[watcher.status] || labels.unknown) +
      (watcher.status === "active" ? (watcher.phase === "scanning" ? " · collecte en cours" : " · en veille") : "");
    $("watcher-observed").textContent = "État à l’ouverture : " + date(data.services.observed_at, true) +
      (watcher.at ? " · dernier signal : " + date(watcher.at, true) : "");
    const digest = data.services.digest || {};
    $("digest-summary").textContent = digest.status !== "configured" ? "Réglage indisponible" :
      digest.enabled ? "Programmé chaque jour à " + digest.time + " (Paris)" : "Récapitulatif désactivé";
  }
  const countryOptions = new Map(jobs.flatMap((job) => (job.location_facts?.countries || []).map((item) => [item.code, item.label])));
  [...countryOptions].sort((a, b) => a[1].localeCompare(b[1], "fr")).forEach(([code, label]) => {
    const option = make("option", label); option.value = code; $("country").append(option);
  });
  const programmeYears = new Set(jobs.filter((job) => job.programme?.kind === "internship" && job.programme.year_status === "confirmed" && Number.isInteger(job.programme.year)).map((job) => job.programme.year));
  if (data.internship_scope?.enabled && Number.isInteger(data.internship_scope.target_year)) programmeYears.add(data.internship_scope.target_year);
  [...programmeYears].filter((year) => year >= 2000 && year <= 2099).sort((a,b) => a-b).forEach((year) => {
    const option = make("option", year); option.value = String(year); $("programme-year").append(option);
  });
  if (data.internship_scope?.enabled) $("programme-help").textContent = "Veille stages : off-cycle et stages longs · " + data.internship_scope.target_year + ". Les Summer Internships restent hors des alertes. Format ou année non confirmé : à vérifier dans la fiche officielle.";
  if (data.internship_scope?.enabled && data.internship_summary) {
    const stages = data.internship_summary;
    $("internship-overview").hidden = false;
    $("internship-counts").textContent = number(stages.available) + " stages disponibles · " + number(stages.formats.off_cycle) + " off-cycle · " + number(stages.formats.long) + " stages longs · " + number(stages.criteria_met) + " avec les critères d’alerte remplis.";
    $("internship-policy").textContent = "Alertes stages " + (data.internship_scope.alerts_enabled && data.internship_scope.radar_alerts_enabled ? "activées" : "désactivées") + " · année ciblée : " + data.internship_scope.target_year + ". Les offres sans année ou format confirmé restent consultables.";
  }
  const internshipAlertLabels = {eligible:"Critères d’alerte remplis",blocked:"Critères d’alerte non remplis",unavailable:"Critères d’alerte à vérifier"};
  const liveEnabled = data.live === true;
  const privateEditing = Boolean(data.editing?.mode === "private" && location.protocol === "https:" &&
    data.editing.origin === location.origin && /^\/[A-Za-z0-9_-]{32,128}\/api\/applications$/.test(data.editing.api_base || "") &&
    [data.editing.api_base.replace(/api\/applications$/, ""), data.editing.api_base.replace(/api\/applications$/, "index.html")].includes(location.pathname));
  const editingEnabled = Boolean(data.editing && data.editing.enabled === true &&
    typeof data.editing.token === "string" && data.editing.token &&
    (privateEditing || (["http:", "https:"].includes(location.protocol) && ["localhost", "127.0.0.1", "[::1]"].includes(location.hostname))));
  const applicationsAPI = privateEditing ? data.editing.api_base : "/api/applications";
  const requestCredentials = privateEditing ? "same-origin" : "omit";
  if (editingEnabled) {
    $("workspace-mode").textContent = "Suivi modifiable";
    $("tracking-mode").textContent = "SUIVI MODIFIABLE";
    if (liveEnabled) {
      $("snapshot-kind").textContent = "DASHBOARD PRIVÉ";
      $("generated-caption").textContent = "Données actualisées le";
      $("refresh-dashboard").hidden = false;
      $("refresh-dashboard").addEventListener("click", () => { if (!detailSession || !dirtyEditor(detailSession)) location.reload(); else detailSession.message.textContent = "Enregistrez ou annulez votre brouillon avant d’actualiser."; });
    }
    $("snapshot-refresh-help").textContent = "Suivi des candidatures synchronisé toutes les 10 secondes. Rechargez pour actualiser les offres et les sources.";
  } else if (liveEnabled) {
    $("workspace-mode").textContent = "Consultation en direct";
    $("snapshot-kind").textContent = "DASHBOARD PRIVÉ";
    $("generated-caption").textContent = "Données actualisées le";
    $("snapshot-refresh-help").textContent = "Les données sont relues à chaque ouverture. Actualisez pour voir les dernières offres et l’état des sources.";
    $("refresh-dashboard").hidden = false;
    $("refresh-dashboard").addEventListener("click", () => location.reload());
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
    ["Offres prioritaires", summary.high_priority, "Actives · échéance non dépassée · score ≥ 70", "◎", ""],
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
    nomura_position_specifications: {origin: "description", kinds: ["professional"], label: "Expérience indiquée par Nomura", source: "Description employeur · Position Specifications → Experience"},
    totalenergies_experience_level: {origin: "employer_field", kinds: ["professional"], label: "Expérience indiquée par TotalEnergies", source: "Champ Experience de l'employeur"}
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
    if (state.view === "agenda") renderAgenda();
  }
  let refreshingApplications = false;
  async function refreshApplications() {
    if (!editingEnabled || document.hidden || refreshingApplications || detailSession?.pending) return;
    refreshingApplications = true;
    const epoch = applicationEpoch;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 8000);
    try {
      const response = await fetch(applicationsAPI, {headers: {"X-Radar-Token": data.editing.token},
        signal: controller.signal, credentials: requestCredentials, cache: "no-store", redirect: "error", referrerPolicy: "no-referrer"});
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
      $("snapshot-refresh-help").textContent = "Suivi synchronisé · " + date(new Date().toISOString(), true) + ". Rechargez pour actualiser les offres et les sources.";
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
    session.message.textContent = changes ? "Enregistrement du suivi…" : "Lecture du suivi actuel…";
    session.message.className = "editor-message";
    const controller = new AbortController(); session.controller = controller;
    const timer = setTimeout(() => controller.abort(), 15000);
    try {
      const options = {method: changes ? "POST" : "GET", headers: {"X-Radar-Token": data.editing.token},
        signal: controller.signal, credentials: requestCredentials, cache: "no-store", redirect: "error", referrerPolicy: "no-referrer"};
      if (changes) { options.headers["Content-Type"] = "application/json"; options.body = JSON.stringify({revision: session.revision, changes}); }
      const response = await fetch(applicationsAPI + "/" + encodeURIComponent(session.job.id), options);
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
    tracking.append(make("h3", editingEnabled ? "Suivi de candidature" : "Suivi de candidature · lecture seule"));
    const trackingGrid = make("dl", null, "detail-grid"); const application = session.job.application || {};
    applicationFields.forEach(([field, label]) => {
      const value = field === "status" ? statusLabel(application[field]) : application[field];
      const wrap = make("div"); wrap.append(make("dt", label), make("dd", value || "Non renseigné")); trackingGrid.append(wrap);
    });
    tracking.append(trackingGrid);
    if (editingEnabled) {
      tracking.append(make("p", "Vos modifications sont conservées dans le radar et accessibles sur vos appareils. Enregistrer un statut n’envoie aucune candidature.", "editor-help"));
      session.message = make("p", message, "editor-message"); session.message.setAttribute("role", "status"); session.message.setAttribute("aria-live", "polite");
      session.editButton = actionButton("Modifier le suivi", () => requestApplication(session), true);
      tracking.append(session.editButton, session.message); renderApplicationHistory(session);
    }
  }
  function renderApplicationEditor(session) {
    const form = make("form", null, "application-editor"); form.setAttribute("aria-label", "Modifier le suivi");
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
    const shortcuts = make("div", null, "tracking-shortcuts");
    shortcuts.setAttribute("aria-label", "Raccourcis du suivi");
    const refreshShortcuts = () => {
      shortcuts.replaceChildren();
      const actions = radarTracking.shortcuts(session.job, applicationValues(session), new Date().toISOString());
      if (!actions.length) return;
      shortcuts.append(make("p", "Préremplissez une action, puis enregistrez pour valider.", "editor-help"));
      actions.forEach((action) => shortcuts.append(actionButton(action.label, () => {
        Object.entries(action.changes).forEach(([field, value]) => { form.elements.namedItem(field).value = value ?? ""; });
        form.elements.namedItem("next_action").setCustomValidity("");
        session.message.textContent = "Raccourci préparé. Vérifiez les champs et enregistrez pour valider.";
        refreshShortcuts(); form.elements.namedItem("next_action").focus();
      })));
    };
    form.prepend(shortcuts); refreshShortcuts();
    form.addEventListener("change", (event) => { if (event.target.name === "status") refreshShortcuts(); });
    form.addEventListener("input", (event) => { if (event.target.name === "next_action") refreshShortcuts(); });
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
  const educationLabels = {bachelor: "Bachelor / Licence", master: "Master", doctorate: "Doctorat", bac_plus_4: "Bac+4", bac_plus_5: "Bac+5", unspecified_level: "Diplôme sans niveau précis"};
  function educationLevels(job) {
    return ((job.education || {}).levels || []).filter((level) => Object.hasOwn(educationLabels, level));
  }
  function showDetail(job) {
    const content = $("job-detail"); content.replaceChildren();
    const title = make("h2", job.title); title.id = "detail-title";
    const top = make("div", null, "detail-top");
    top.append(make("span", radarProgramme.label(job.programme), "badge"));
    const statusBadge = make("span", statusLabel((job.application || {}).status), "badge");
    top.append(scorePill(job.score), make("span", job.is_active ? "Offre active" : "Offre inactive", "badge"), statusBadge);
    if (job.is_expired) top.append(make("span", "Échéance dépassée", "badge"));
    else if ((job.deadline || {}).precision === "conflict") top.append(make("span", "Échéance à vérifier", "badge"));
    content.append(title, make("p", [job.company, job.location].filter(Boolean).join(" · "), "detail-company"), top);
    const url = safeURL(job.apply_url);
    if (url) {
      const link = make("a", "Consulter l’offre officielle ↗", "official-link");
      link.href = url; link.target = "_blank"; link.rel = "noopener noreferrer";
      link.setAttribute("aria-label", "Consulter l’offre officielle (nouvel onglet)"); content.append(link);
    } else content.append(make("p", "Lien officiel indisponible.", "detail-company"));
    const conditions = job.conditions || {};
    const programmeSection = detailSection("Programme");
    programmeSection.append(make("p", radarProgramme.label(job.programme)));
    (job.programme?.evidence || []).forEach((excerpt) => programmeSection.append(make("blockquote", excerpt, "description")));
    (job.programme?.issues || []).forEach((issue) => programmeSection.append(make("p", issue, "editor-error")));
    content.append(programmeSection);
    if (job.internship_alert) {
      const criteria = job.internship_alert;
      const alertSection = detailSection("Critères d’alerte Telegram");
      alertSection.append(make("p", internshipAlertLabels[criteria.status] || internshipAlertLabels.unavailable),
        make("p", "Année ciblée : " + criteria.target_year + " · seuil de score : " + criteria.score_threshold));
      criteria.reasons.forEach((reason) => alertSection.append(make("p", reason.message, "experience-help")));
      criteria.warnings.forEach((warning) => alertSection.append(make("p", warning, "experience-help")));
      alertSection.append(make("p", "Une alerte nécessite aussi une nouvelle détection, une réouverture ou une modification significative dans une collecte validée. Cet état ne confirme pas un envoi Telegram et ne relance pas les anciennes offres.", "experience-help"));
      content.append(alertSection);
    }
    const opportunitySection = detailSection("Pays, durée et début");
    opportunitySection.append(make("p", (job.location_facts?.countries || []).map((item) => item.label).join(" / ") || "Pays non reconnu"),
      make("p", radarOpportunity.durationLabel(job.duration)), make("p", radarOpportunity.startLabel(job.start)));
    (job.duration?.evidence || []).forEach((excerpt) => opportunitySection.append(make("blockquote", excerpt, "description")));
    content.append(opportunitySection);
    const start = conditions.start || {};
    const authorization = ((conditions.authorization || {}).evidence || []);
    const dates = detailSection("Calendrier et droit au travail");
    const startLabels = {preferred: "Début dans les périodes prioritaires de 2027.", outside: "Début hors des périodes prioritaires de 2027.", mixed: "Fenêtre de début partiellement compatible avec les périodes prioritaires de 2027."};
    dates.append(make("p", start.precision === "conflict" ? "Dates de début contradictoires : à vérifier." : (startLabels[start.target_window] || "Fenêtre de début à vérifier dans l’annonce.")));
    (start.evidence || []).forEach((excerpt) => dates.append(make("blockquote", excerpt, "description")));
    authorization.forEach((excerpt) => dates.append(make("blockquote", excerpt, "description")));
    if (!authorization.length) dates.append(make("p", "Aucune condition de visa ou de droit au travail reconnue. À vérifier dans l’offre officielle."));
    content.append(dates);
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
    if (!educationEvidence.length) educationSection.append(make("p", "Aucune mention de diplôme reconnue dans les rubriques prises en charge de cette annonce. Cela ne signifie pas qu’aucun diplôme n’est demandé."));
    educationEvidence.forEach((item) => {
      educationSection.append(make("p", "Critères de l’annonce · " + item.heading, "detail-company"),
        make("blockquote", item.excerpt, "description experience-excerpt"));
    });
    educationSection.append(make("p", "Ces mentions peuvent être des exigences, des préférences ou des alternatives. L’extrait conserve les conditions de l’employeur. Vérifiez l’annonce officielle pour apprécier votre éligibilité."));
    content.append(educationSection);
    const timing = detailSection("Repères"); const grid = make("dl", null, "detail-grid");
    const deadline = job.deadline || {};
    const timingValues = [
      ["Publication · source", radarPublication.label(job.publication_day)],
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
    const programmeFilter = $("programme").value;
    const programmeYear = $("programme-year").value;
    const countryFilter = $("country").value; const durationFilter = $("duration").value;
    const startFrom = $("start-from").value; const startTo = $("start-to").value;
    const validStart = radarPublication.validRange(startFrom, startTo) && !$("start-from").validity.badInput && !$("start-to").validity.badInput;
    $("start-error").hidden = validStart;
    $("start-error").textContent = validStart ? "" : "Vérifiez la période de début : la borne de départ doit précéder ou égaler la borne de fin. Ce filtre attend une période valide.";
    ["start-from", "start-to"].forEach((id) => $(id).setAttribute("aria-invalid", String(!validStart)));
    const from = $("publication-from").value; const to = $("publication-to").value;
    const validPeriod = radarPublication.validRange(from, to) && !$("publication-from").validity.badInput && !$("publication-to").validity.badInput;
    $("publication-error").hidden = validPeriod;
    $("publication-error").textContent = validPeriod ? "" : "Vérifiez les dates : le début doit précéder ou égaler la fin. Le filtre de publication n’est pas appliqué tant que la période est invalide.";
    ["publication-from", "publication-to"].forEach((id) => $(id).setAttribute("aria-invalid", String(!validPeriod)));
    let results = jobs.filter((job) =>
      (!query || searchText.get(job.id).includes(query)) && (!company || job.company === company) &&
      job.score >= score && (active === "all" || (active === "available" ? job.is_active && !job.is_expired : active === "expired" ? job.is_expired : Boolean(job.is_active) === (active === "active"))) &&
      (!application || (job.application || {}).status === application) &&
      (!experienceCategory || experience(job).category === experienceCategory) &&
      radarProgramme.matches(job.programme, programmeFilter) &&
      radarProgramme.yearMatches(job.programme, programmeYear) &&
      radarOpportunity.country(job.location_facts, countryFilter) &&
      radarOpportunity.duration(job.duration, durationFilter) &&
      (!validStart || radarOpportunity.start(job.start, startFrom, startTo)) &&
      (!education || (education === "unrecognized" ? !educationLevels(job).length : educationLevels(job).includes(education))) &&
      (!validPeriod || radarPublication.within(job.publication_day, from, to)) &&
      (state.view !== "applications" || (job.application || {}).status !== "New")
    );
    const sorting = $("sort").value;
    const timestamp = (value) => { const stamp = Date.parse(value); return Number.isFinite(stamp) ? stamp : 0; };
    const deadlineTime = (job) => timestamp((job.deadline || {}).instant || (job.deadline || {}).day) || Number.MAX_SAFE_INTEGER;
    results.sort((a, b) => (sorting.startsWith("publication-") ? radarPublication.compare(a.publication_day, b.publication_day, sorting === "publication-oldest") : sorting === "company" ? collator.compare(a.company, b.company) : sorting === "recent" ? timestamp(b.first_seen) - timestamp(a.first_seen) : sorting === "deadline" ? deadlineTime(a) - deadlineTime(b) : b.score - a.score) || collator.compare(a.title, b.title) || collator.compare(a.id, b.id));
    const pages = Math.max(1, Math.ceil(results.length / pageSize)); state.page = Math.min(state.page, pages);
    const start = (state.page - 1) * pageSize;
    $("job-rows").replaceChildren();
    $("mobile-jobs").replaceChildren();
    results.slice(start, start + pageSize).forEach((job) => {
      const row = make("tr"); const jobCell = make("td");
      const button = make("button", job.title, "job-title"); button.type = "button"; button.addEventListener("click", () => showDetail(job));
      const companyLine = make("div", null, "company-line"); const initial = make("span", job.company.slice(0, 2).toUpperCase(), "company-initial"); initial.setAttribute("aria-hidden", "true");
      companyLine.append(initial, make("span", job.company)); if (!job.is_active) companyLine.append(make("span", "Inactive", "badge"));
      if (job.is_expired) companyLine.append(make("span", "Échéance dépassée", "badge"));
      if (job.programme?.kind && job.programme.kind !== "unspecified") companyLine.append(make("span", radarProgramme.label(job.programme), "badge"));
      if (job.internship_alert) companyLine.append(make("span", internshipAlertLabels[job.internship_alert.status], "badge"));
      jobCell.append(button, companyLine, make("span", experienceLabel(job), "experience-indicator"));
      experienceEvidence(job).filter((item) => item.kind === "industry_or_academia").forEach((item) => {
        jobCell.append(make("span", evidenceLabel(item), "experience-indicator experience-practice"));
      });
      const degrees = educationLevels(job);
      if (degrees.length) jobCell.append(make("span", "Diplômes cités · " + degrees.map((level) => educationLabels[level]).join(" · "), "experience-indicator"));
      const scoreCell = make("td"); scoreCell.append(scorePill(job.score));
      const statusCell = make("td"); statusCell.append(make("span", statusLabel((job.application || {}).status), "badge"));
      const detailCell = make("td"); const detailButton = make("button", "↗", "arrow-button"); detailButton.type = "button"; detailButton.setAttribute("aria-label", "Détail : " + job.title + " chez " + job.company); detailButton.addEventListener("click", () => showDetail(job)); detailCell.append(detailButton);
      const publicationCell = make("td", undefined, "date-cell");
      const publicationDay = radarPublication.day(job.publication_day);
      if (publicationDay) {
        const published = make("time", radarPublication.label(publicationDay)); published.dateTime = publicationDay;
        publicationCell.append(published);
      } else publicationCell.textContent = "Non précisée";
      row.append(jobCell, make("td", job.location || "Non précisée", "location-cell"), scoreCell, statusCell, publicationCell, make("td", date(job.first_seen), "date-cell"), detailCell);
      $("job-rows").append(row);
      const card = make("article", null, "mobile-job-card");
      const heading = make("h3"); const open = actionButton(job.title, () => showDetail(job));
      open.className = "job-title"; heading.append(open);
      const badges = make("div", null, "mobile-badges");
      badges.append(scorePill(job.score), make("span", statusLabel(job.application?.status || "New"), "badge"));
      if (job.internship_alert) badges.append(make("span", internshipAlertLabels[job.internship_alert.status], "badge"));
      card.append(heading, make("p", job.company + " · " + (job.location || "Lieu non précisé")), badges,
        make("p", radarProgramme.label(job.programme) + " · " + radarOpportunity.durationLabel(job.duration)),
        make("p", "Début : " + radarOpportunity.startLabel(job.start)));
      if (job.application?.next_action) card.append(make("p", "Prochaine action : " + job.application.next_action + (job.application.next_action_date ? " · " + date(job.application.next_action_date) : ""), "mobile-next-action"));
      if (job.deadline?.day) card.append(make("p", "Date limite : " + date(job.deadline.day), job.is_expired ? "editor-error" : ""));
      card.append(actionButton(editingEnabled ? "Ouvrir le suivi" : "Voir la fiche", () => showDetail(job)));
      $("mobile-jobs").append(card);
    });
    $("empty-state").hidden = results.length > 0;
    const emptyText = $("empty-state").querySelector("p");
    emptyText.textContent = state.view === "applications" ? "Cette vue affiche les offres dont le suivi a quitté le statut « À découvrir ». Vous pouvez aussi élargir les filtres." : "Élargissez vos filtres ou recherchez un autre mot-clé.";
    $("result-count").textContent = number(results.length) + (results.length === 1 ? " offre" : " offres") + (state.view === "applications" ? (results.length === 1 ? " suivie" : " suivies") : " dans votre sélection");
    $("page-info").textContent = results.length ? (start + 1) + "–" + Math.min(start + pageSize, results.length) + " sur " + number(results.length) + " · Page " + state.page + " / " + pages : "0 offre";
    $("previous").disabled = state.page <= 1; $("next").disabled = state.page >= pages;
  }
  function agendaSelection(now) {
    const today = radarAgenda.parisDay(now);
    const selected = $("agenda-period").value;
    const end = new Date(today + "T12:00:00Z"); end.setUTCDate(end.getUTCDate() + (selected === "month" ? 29 : 6));
    const until = end.toISOString().slice(0, 10);
    return radarAgenda.entries(jobs, now).filter((entry) => selected === "all" || (selected === "overdue" ? entry.overdue : !entry.overdue && entry.day >= today && entry.day <= until));
  }
  function renderAgenda() {
    const entries = agendaSelection(new Date().toISOString());
    $("agenda-items").replaceChildren();
    entries.forEach((entry) => {
      const card = make("article", null, "agenda-card" + (entry.overdue ? " overdue" : ""));
      const exact = entry.kind === "deadline" && entry.job.deadline?.precision === "instant";
      const instant = exact ? entry.job.deadline.instant : entry.day;
      const when = make("time", date(instant, exact)); when.dateTime = instant;
      card.append(when, make("span", entry.kind === "action" ? "Prochaine action" : "Date limite", "badge"),
        make("h3", entry.text), make("p", entry.job.company + " · " + entry.job.title),
        actionButton(editingEnabled ? "Ouvrir le suivi" : "Voir la fiche", () => showDetail(entry.job)));
      $("agenda-items").append(card);
    });
    $("agenda-count").textContent = number(entries.length) + " échéance(s)";
    $("agenda-empty").hidden = entries.length > 0;
    $("export-agenda").disabled = entries.length === 0;
  }
  function exportAgenda() {
    const message = $("calendar-message");
    try {
      const now = new Date().toISOString(); const calendar = radarCalendar.build(agendaSelection(now),now);
      if (!calendar.count) {message.textContent = "Aucune échéance datée à exporter dans cette période."; return;}
      const url = URL.createObjectURL(new Blob([calendar.text],{type:"text/calendar;charset=utf-8"}));
      const link = make("a");link.href = url;link.download = "radar-echeances-" + radarAgenda.parisDay(now) + ".ics";
      document.body.append(link);link.click();link.remove();setTimeout(() => URL.revokeObjectURL(url),1000);
      message.textContent = number(calendar.count) + " échéance(s) exportée(s). Ouvrez le fichier dans votre application de calendrier. Cet export ne se synchronise pas automatiquement.";
    } catch (_) {message.textContent = "L’export est indisponible dans ce navigateur. Vous pouvez consulter les échéances ici.";}
  }
  function renderCoverage() {
    const coverage = data.internship_coverage || {};
    const labels = {validated:"Référence stages validée", pending:"Référence stages en attente", prevalidated:"Prévalidée par configuration"};
    const summary = $("coverage-summary");
    if (coverage.status === "disabled") summary.textContent = "La veille stages est désactivée.";
    else if (coverage.status !== "ok") summary.textContent = "La référence des stages est indisponible. Aucun état de couverture n’est déduit.";
    else summary.textContent = number(coverage.validated_sources) + " / " + number(coverage.enabled_sources) + " sources avec une référence stages observée" + (coverage.baseline_at ? " depuis le " + date(coverage.baseline_at, true) : " · référence prévalidée par configuration, sans date observée") + ".";
    $("coverage-sources").replaceChildren();
    if (coverage.status !== "ok") return;
    const sources = [...(health.sources || [])].sort((a,b) => (a.status === "fresh") - (b.status === "fresh") || (coverage.sources?.[a.source]?.status === "validated") - (coverage.sources?.[b.source]?.status === "validated") || a.company.localeCompare(b.company,"fr"));
    sources.forEach((source) => {
      const reference = coverage.sources?.[source.source] || {};
      const card = make("article", null, "coverage-card");
      card.append(make("h4", source.company), make("span", source.source, "source-key"), healthBadge(source.status),
        make("p", labels[reference.status] || "Référence inconnue", reference.status === "validated" ? "coverage-ready" : "coverage-pending"));
      if (reference.validated_at) card.append(make("p", "Validée le " + date(reference.validated_at, true), "source-key"));
      if (source.failure) card.append(make("p", source.failure.label));
      if (source.status !== "fresh") card.append(make("p", "Dernier succès : " + date(source.last_success, true), "source-key"));
      const stages = jobs.filter((job) => job.source === source.source && job.is_active && job.programme?.kind === "internship");
      card.append(make("p", number(stages.length) + " stages actifs en base · tous formats confondus", "source-key"));
      $("coverage-sources").append(card);
    });
  }
  function renderHealth() {
    renderCoverage();
    const badge = healthBadge(health.status); $("health-status").className = badge.className; $("health-status").textContent = badge.textContent;
    $("health-explanation").textContent = (editingEnabled || liveEnabled ? "État calculé au chargement de la page. " : "État calculé lors de l’export. ") + "Une source est à jour si sa dernière collecte réussie date de moins de " + (health.max_age_hours || 24) + " heures, sans échec ultérieur ni fiche incomplète signalée. " + (editingEnabled || liveEnabled ? "Rechargez la page pour actualiser les offres et les sources. Le calendrier indique la première heure possible, pas une garantie de passage ; il dépend du scanner et des places disponibles." : "Les données ne s’actualisent pas automatiquement. Le calendrier est une estimation au moment de l’export.");
    (health.sources || []).forEach((source) => {
      const row = make("tr"); const name = make("td"); name.append(make("span", source.company, "source-name"), make("span", source.source, "source-key"));
      const status = make("td"); status.append(healthBadge(source.status));
      if (source.failure) {
        status.append(make("p", source.failure.label, "source-key"));
        status.append(make("span", "Dernier échec : " + date(source.last_failure, true), "source-key"));
      }
      if ((source.listing_gaps || []).length) {
        status.append(make("p", "Fiches incomplètes ou détail indisponible : " + source.listing_gaps.join(", ") + ". Les autres offres sont actualisées ; ces références ne sont pas déclarées fermées.", "source-key"));
      }
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
      const history = data.source_history;
      const observation = history?.sources?.[source.source];
      if (observation) {
        const details = make("details", undefined, "collection-conflicts");
        details.append(make("summary", number(observation.success_rate) + " % de collectes réussies · " + number(observation.attempts) + " essais"));
        details.append(make("p", "Sur les 24 dernières heures, observations depuis le " + date(observation.since, true) + ". Durée moyenne : " + number(observation.average_seconds) + " s.", "source-key"));
        if (history.legacy_scans) details.append(make("p", "Historique en cours de constitution : les anciens essais sans attribution par source sont exclus.", "source-key"));
        const labels = { successful: "Réussie", failed: "Échec", partial: "Fiches incomplètes", degraded: "Références en conflit" };
        observation.latest.forEach((attempt) => details.append(make("p", date(attempt.at, true) + " · " + labels[attempt.status] + (attempt.failure ? " · " + attempt.failure.label : ""), "source-key")));
        const selectionAttempt = observation.latest.find((attempt) => attempt.selection);
        if (selectionAttempt) {
          const selection = selectionAttempt.selection;
          details.append(make("p", number(selection.examined) + " annonces examinées · " + number(selection.selected) + " retenues par les filtres. " + (selection.scope === "search_results" ? "Périmètre limité aux recherches configurées." : "Catalogue public examiné ; ciblage partiel."), "source-key"));
          const rejectionLabel = (reason) => reason.startsWith("excluded_title:") ? "Terme exclu : " + reason.slice(15) : ({no_title_match: "Intitulé hors du ciblage", prospect: "Formulaire général", event: "Événement", hidden: "Annonce masquée", unpublished: "Publication non confirmée", department: "Équipe hors du ciblage"}[reason] || "Hors du ciblage");
          Object.entries(selection.rejected).forEach(([reason, count]) => details.append(make("p", rejectionLabel(reason) + " · " + number(count), "source-key")));
          selection.samples.forEach((sample) => details.append(make("p", sample.title + " · " + rejectionLabel(sample.reason), "source-key")));
        }
        success.append(details);
      } else success.append(make("span", history?.status === "unavailable" ? "Historique indisponible" : "Historique en cours de constitution", "source-key"));
      if (source.age_hours !== null && source.age_hours !== undefined) success.append(make("span", "Il y a " + number(Math.round(source.age_hours * 10) / 10) + " h", "source-key"));
      const schedule = make("td");
      if (source.schedule) {
        schedule.append(make("span", "Intervalle : " + number(source.schedule.interval_seconds / 60) + " min", "source-name"));
        if (source.schedule.eligible_now === null) schedule.append(make("span", "Date incohérente : calendrier indisponible", "source-key"));
        else if (source.schedule.eligible_now) schedule.append(make("span", "Collecte possible · en cours ou en attente du scanner", "source-key"));
        else schedule.append(make("span", "Prochaine collecte possible : " + date(source.schedule.next_eligible_at, true), "source-key"));
        if (source.failure) schedule.append(make("span", "Délai après échec : " + number(source.schedule.cooldown_seconds / 60) + " min", "source-key"));
      } else schedule.textContent = "Non précisé";
      row.append(name, status, success, schedule, make("td", number(source.last_snapshot_jobs ?? source.last_count)), make("td", number(source.consecutive_failures))); $("source-rows").append(row);
    });
    $("record-health").hidden = !editingEnabled || privateEditing;
    $("health-capture-help").hidden = !editingEnabled || privateEditing;
    renderHealthHistory();
  }
  function renderHealthHistory() {
    $("health-history").replaceChildren();
    const monitoring = data.monitoring || {};
    const snapshots = monitoring.snapshots || [];
    if (monitoring.status === "unavailable") $("health-history").append(make("p", "L’historique local est indisponible. " + ((monitoring.error || {}).message || ""), "history-empty"));
    else if (!snapshots.length) $("health-history").append(make("p", "Aucun rapport de santé enregistré. Cette vue affiche les rapports déjà présents dans le projet.", "history-empty"));
    const comparison = monitoring.latest_comparison;
    if (comparison) {
      const panel = make("div", null, "health-comparison");
      panel.append(make("strong", "Évolution entre les deux derniers contrôles"));
      const periods = [comparison.previous_id, comparison.current_id].map((id) => snapshots.find((snapshot) => snapshot.id === id));
      if (periods.every(Boolean)) panel.append(make("p", "Du " + date(periods[0].recorded_at, true) + " au " + date(periods[1].recorded_at, true)));
      panel.append(make("p", "État général : " + (healthLabels[comparison.before] || comparison.before) + " → " + (healthLabels[comparison.after] || comparison.after)));
      if (!comparison.same_freshness_threshold) panel.append(make("p", "Les seuils de fraîcheur diffèrent : les changements peuvent venir du seuil choisi."));
      if (!comparison.sources_comparable) panel.append(make("p", "Sources non comparables : la base était indisponible lors d’un contrôle."));
      else if (!comparison.source_changes.length) panel.append(make("p", "Aucun changement d’état des sources."));
      else {
        const list = make("ul");
        const labels = { improved: "Amélioration", regressed: "Dégradation", changed: "Diagnostic modifié", added: "Source ajoutée", removed: "Source retirée" };
        comparison.source_changes.forEach((change) => {
          const source = (health.sources || []).find((item) => item.source === change.source);
          const name = source ? source.company + " (" + change.source + ")" : change.source;
          list.append(make("li", name + " · " + labels[change.change] + " : " + (healthLabels[change.before] || "Hors périmètre") + " → " + (healthLabels[change.after] || "Hors périmètre")));
        });
        panel.append(list);
      }
      $("health-history").append(panel);
    } else if (snapshots.length === 1) $("health-history").append(make("p", "Un second contrôle permettra de comparer l’état des sources.", "history-empty"));
    snapshots.forEach((snapshot) => {
      const row = make("article", null, "history-row"); const description = make("div");
      description.append(make("strong", date(snapshot.recorded_at, true)), make("div", number((snapshot.source_summary || {}).fresh || 0) + " sources à jour · " + number((snapshot.issues || []).length) + " points à examiner", "history-meta"));
      row.append(description, healthBadge(snapshot.status)); $("health-history").append(row);
    });
  }
  async function recordHealth() {
    const button = $("record-health");
    if (!editingEnabled || privateEditing || button.disabled) return;
    button.disabled = true;
    const message = $("health-capture-message");
    message.textContent = "Enregistrement du contrôle…";
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch("/api/health-snapshots", {
        method: "POST", credentials: "same-origin", cache: "no-store", signal: controller.signal,
        headers: { "Content-Type": "application/json", "X-Radar-Token": data.editing.token }, body: "{}"
      });
      const result = await response.json();
      if (response.status !== 201 || result.status !== "ok" || !result.snapshot || !result.monitoring) {
        message.textContent = (result.error || {}).message || "Enregistrement non confirmé. Rechargez la page pour vérifier l’historique.";
        return;
      }
      data.monitoring = result.monitoring;
      renderHealthHistory();
      message.textContent = "Contrôle enregistré le " + date(result.snapshot.recorded_at, true) + ". " + (result.monitoring.status === "ok" ? "Historique actualisé ci-dessous." : "L’historique reste indisponible ; le nouveau contrôle a bien été conservé.");
    } catch (_) {
      message.textContent = "Enregistrement non confirmé. Rechargez la page pour vérifier l’historique avant de réessayer.";
    } finally {
      clearTimeout(timeout);
      button.disabled = false;
    }
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
    $("trend-window").textContent = daily.length ? "Du " + trendDate(daily[0].date) + " au " + trendDate(daily[daily.length - 1].date) + " · " + daily.length + " jours calendaires · journée en cours incluse." : "Aucun jour d’historique disponible.";
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
      bar.setAttribute("aria-label", "Premières détections le " + trendDate(day.date) );
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
  const filterOptions = () => Object.fromEntries(radarPreferences.fields.filter((id) => $(id).tagName === "SELECT").map((id) => [id,[...$(id).options].map((option) => option.value)]));
  const captureFilters = () => Object.fromEntries(radarPreferences.fields.map((id) => [id,$(id).value]));
  let savedFilterViews = {};
  const filterStorage = () => window.localStorage;
  function restoreFilters(view) {
    HTMLFormElement.prototype.reset.call($("filters")); $("sort").value = "score";
    if (view === "applications") $("active").value = "all";
    const saved = savedFilterViews[view];
    if (saved) Object.entries(saved).forEach(([id,value]) => {if (radarPreferences.fields.includes(id)) $(id).value = value;});
  }
  function persistFilters() {
    if (["jobs","applications"].includes(state.view)) savedFilterViews[state.view] = captureFilters();
    if (!$("remember-filters").checked) return;
    let stored = false;
    try {stored = radarPreferences.save(filterStorage(),savedFilterViews,filterOptions());} catch (_) {}
    $("filter-memory-message").textContent = stored ? "Filtres retenus sur cet appareil · alertes inchangées." : "La mémorisation est indisponible. Vos filtres restent utilisables dans cette fenêtre.";
  }
  try {
    const saved = radarPreferences.load(filterStorage(),filterOptions());
    if (saved.status === "ok") {
      savedFilterViews = saved.views; $("remember-filters").checked = true; restoreFilters("jobs");
      $("filter-memory-message").textContent = "Vos filtres de consultation ont été restaurés. Réinitialisez pour élargir la sélection.";
    }
  } catch (_) {}
  function setView(view) {
    if (view !== state.view) {
      if (["jobs","applications"].includes(state.view)) savedFilterViews[state.view] = captureFilters();
      if (["jobs","applications"].includes(view)) restoreFilters(view);
    }
    state.view = view; state.page = 1;
    document.querySelectorAll(".nav-item").forEach((button) => {
      const selected = button.dataset.view === view; button.classList.toggle("selected", selected);
      if (selected) button.setAttribute("aria-current", "page"); else button.removeAttribute("aria-current");
    });
    $("jobs-view").hidden = !["jobs", "applications"].includes(view); $("health-view").hidden = view !== "health"; $("trends-view").hidden = view !== "trends"; $("agenda-view").hidden = view !== "agenda";
    $("metrics").hidden = view === "trends";
    const headings = {
      jobs: ["OFFRES", "Le marché, à votre portée.", "Repérez les offres pertinentes. Gardez le cap sur votre recherche."],
      applications: ["CANDIDATURES", "Chaque candidature compte.", "Consultez votre suivi, vos contacts et vos prochaines actions."],
      agenda: ["ÉCHÉANCES", "Gardez une longueur d’avance.", "Vos prochaines actions et vos dates limites, accessibles sur téléphone."],
      health: ["SANTÉ DES SOURCES", "La santé de votre veille.", "Vérifiez la fraîcheur des collectes et les derniers rapports locaux."],
      trends: ["TENDANCES", "Le rythme de votre veille.", "Suivez les détections, les changements et la fiabilité des collectes."]
    };
    ["breadcrumb-view", "page-title", "page-subtitle"].forEach((id, index) => { $(id).textContent = headings[view][index]; });
    $("results-heading").textContent = view === "applications" ? "Votre suivi de candidatures" : "Toutes les offres";
    if (["jobs", "applications"].includes(view)) renderJobs();
    if (view === "agenda") renderAgenda();
  }
  document.querySelectorAll(".nav-item").forEach((button) => button.addEventListener("click", () => setView(button.dataset.view)));
  $("filters").addEventListener("submit", (event) => event.preventDefault());
  $("trend-days").addEventListener("change", renderTrends);
  $("agenda-period").addEventListener("change", renderAgenda);
  $("export-agenda").addEventListener("click", exportAgenda);
  $("record-health").addEventListener("click", recordHealth);
  $("service-details").addEventListener("click", () => setView("health"));
  radarPreferences.fields.forEach((id) => $(id).addEventListener(id === "search" || id.startsWith("publication-") || id.startsWith("start-") ? "input" : "change", () => { state.page = 1; renderJobs(); persistFilters(); }));
  $("reset").addEventListener("click", () => { HTMLFormElement.prototype.reset.call($("filters")); if (state.view === "applications") $("active").value = "all"; $("sort").value = "score"; state.page = 1; renderJobs(); persistFilters(); });
  $("remember-filters").addEventListener("change", () => {
    if ($("remember-filters").checked) persistFilters();
    else {
      let cleared = false; try {cleared = radarPreferences.clear(filterStorage());} catch (_) {}
      $("filter-memory-message").textContent = cleared ? "Filtres oubliés sur cet appareil. Ils restent actifs dans cette fenêtre." : "Cet appareil refuse l’accès à la mémorisation. Vous pouvez supprimer les données du site dans votre navigateur.";
    }
  });
  [["quick-off-cycle","off_cycle"],["quick-long","long"],["quick-priority",null]].forEach(([id,format]) => $(id).addEventListener("click", () => {
    if (format) {
      $("programme").value = format;
      if (data.internship_scope?.enabled) $("programme-year").value = String(data.internship_scope.target_year);
    } else $("score").value = "70";
    state.page = 1; renderJobs(); persistFilters();
  }));
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
