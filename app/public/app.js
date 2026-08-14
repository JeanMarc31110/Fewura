const state = { results: [], prospects: [], stages: [], priorities: [], stats: {}, searchMeta: null, selectedProspect: null, activities: [], selectedIds: new Set() };
const stageLabels = { new: "Nouveaux", qualified: "Qualifiés", contacted: "Contactés", replied: "Réponses", meeting: "Rendez-vous", proposal: "Propositions", won: "Gagnés", lost: "Perdus", excluded: "Exclus" };
const activityLabels = { note: "Note", call: "Appel", email: "Email", meeting: "Rendez-vous", task: "Tâche", stage_change: "Pipeline", email_draft: "Brouillon", gmail_draft: "Brouillon Gmail" };
const stageOrder = ["new", "qualified", "contacted", "replied", "meeting", "proposal", "won", "lost", "excluded"];

const $ = (selector) => document.querySelector(selector);
const escapeHtml = (value = "") => String(value).replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char]));
const showToast = (message) => { const toast = $("#toast"); toast.textContent = message; toast.classList.add("show"); setTimeout(() => toast.classList.remove("show"), 2800); };
const formatCurrency = (value) => `${new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(Number(value) || 0)} €`;
const formatDate = (value) => value ? new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium" }).format(new Date(value.includes("T") ? value : `${value}T12:00:00`)) : "Non renseignée";
const formatDateTime = (value) => value ? new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "";
const isOverdue = (prospect) => Boolean(prospect.nextActionAt && prospect.nextActionAt < new Date().toISOString().slice(0, 10) && !["won", "lost", "excluded"].includes(prospect.stage));

async function api(url, options = {}) {
  const response = await fetch(url, { headers: { "Content-Type": "application/json", ...(options.headers || {}) }, ...options });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || "Une erreur est survenue.");
  return data;
}

async function loadHealth() {
  try {
    const data = await api("/api/health");
    $("#healthText").textContent = data.braveConfigured ? `Brave connecté${data.hunterConfigured ? " · Hunter connecté" : ""} · CRM prêt` : "CRM prêt · clé Brave à configurer";
    $(".status-dot").style.background = data.braveConfigured ? "#91d65e" : "#f5b94c";
  } catch { $("#healthText").textContent = "Connexion à vérifier"; $(".status-dot").style.background = "#ed6a5a"; }
}

function renderSearchResults() {
  $("#resultCount").textContent = state.results.length;
  $("#resultsTitle").textContent = state.results.length ? "Prospects compatibles avec FÉWURA" : "Aucun prospect compatible";
  $("#searchSources").textContent = state.searchMeta?.sources?.length ? `Sources interrogées : ${state.searchMeta.sources.map((source) => source.name).join(" · ")}` : "";
  $("#searchMessage h3").textContent = state.searchMeta ? "Aucune entreprise ne respecte les deux critères." : "Votre prochaine liste de prospects commence ici.";
  $("#searchMessage p").textContent = state.searchMeta
    ? `${state.searchMeta.rejected.withoutEmail} sans e-mail · ${state.searchMeta.rejected.publicEntity} organisme(s) public(s) · ${state.searchMeta.rejected.withoutOfferFit} sans adéquation suffisante avec FÉWURA.`
    : "Les entreprises trouvées apparaîtront avec leur site source, e-mail et téléphone lorsqu’ils sont détectés.";
  $("#searchMessage").classList.toggle("hidden", state.results.length > 0);
  $("#resultsList").classList.toggle("hidden", state.results.length === 0);
  $("#resultsList").innerHTML = state.results.map((result, index) => `
    <article class="prospect-row">
      <div><div class="prospect-name">${escapeHtml(result.businessName)}</div><div class="prospect-meta">${escapeHtml(result.profession)} · ${escapeHtml(result.region)} · <span>${escapeHtml(result.confidence)}</span></div><div class="prospect-meta">Signaux : ${escapeHtml((result.fitReasons || []).join(" · "))}</div><div class="prospect-meta">Sources : ${escapeHtml([...new Set((result.sources || []).map((source) => source.name).filter(Boolean))].join(" · ") || "Brave Search")}</div><a class="source-link" href="${escapeHtml(result.sourceUrl)}" target="_blank" rel="noreferrer">${escapeHtml(result.sourceTitle || result.sourceUrl)}</a></div>
      <div><div class="contact-line"><strong>✉</strong> ${escapeHtml((result.allEmails?.length ? result.allEmails : [result.email]).filter(Boolean).join(", ") || "E-mail non trouvé")}</div><div class="contact-line"><strong>⌕</strong> ${escapeHtml((result.allPhones?.length ? result.allPhones : [result.phone]).filter(Boolean).join(", ") || "Téléphone non trouvé")}</div></div>
      <button class="save-button ${result.saved ? "saved" : ""}" data-result-index="${index}" ${result.saved ? "disabled" : ""}>${result.saved ? "Ajouté" : "+ Ajouter au CRM"}</button>
    </article>`).join("");
  document.querySelectorAll("[data-result-index]").forEach((button) => button.addEventListener("click", () => saveResult(Number(button.dataset.resultIndex))));
}

async function saveResult(index) {
  try {
    const result = state.results[index];
    const data = await api("/api/prospects", { method: "POST", body: JSON.stringify(result) });
    state.results[index].saved = true;
    renderSearchResults();
    await loadProspects();
    showToast(data.created ? "Prospect ajouté au CRM" : "Prospect mis à jour dans le CRM");
  } catch (error) { showToast(error.message); }
}

async function runSearch(event) {
  event.preventDefault();
  const button = $("#searchForm .button.primary");
  const region = $("#region").value.trim();
  const selectedProfession = $("#professions").value.trim();
  const customProfession = $("#customProfession").value.trim();
  const profession = customProfession || selectedProfession;
  if (!profession) {
    showToast("Choisissez une profession ou saisissez un corps de métier.");
    return;
  }
  const professions = [profession];
  button.disabled = true; button.querySelector("span").textContent = "Recherche en cours…";
  try {
    const data = await api("/api/search", { method: "POST", body: JSON.stringify({ region, professions, count: $("#count").value }) });
    state.results = data.results || [];
    state.searchMeta = data;
    renderSearchResults();
  } catch (error) { showToast(error.message); }
  finally { button.disabled = false; button.querySelector("span").textContent = "Rechercher avec Brave"; }
}

function currentCrmQuery() {
  const params = new URLSearchParams();
  const q = $("#crmSearch").value.trim();
  const stage = $("#crmStageFilter").value;
  const priority = $("#crmPriorityFilter").value;
  if (q) params.set("q", q);
  if (stage) params.set("stage", stage);
  if (priority) params.set("priority", priority);
  if ($("#crmOverdueFilter").checked) params.set("overdue", "true");
  return params.toString();
}

function renderStats() {
  const stats = state.stats || {};
  $("#crmCount").textContent = `${state.prospects.length} affiché${state.prospects.length > 1 ? "s" : ""} · ${stats.total || 0} au total`;
  $("#statTotal").textContent = stats.total || 0;
  $("#statQualified").textContent = stats.qualified || 0;
  $("#statOverdue").textContent = stats.overdue || 0;
  $("#statOpenValue").textContent = formatCurrency(stats.openValue);
  $("#statWonValue").textContent = formatCurrency(stats.wonValue);
}

function renderFilterOptions() {
  const selected = $("#crmStageFilter").value;
  $("#crmStageFilter").innerHTML = `<option value="">Toutes les étapes</option>${state.stages.map((stage) => `<option value="${escapeHtml(stage)}">${escapeHtml(stageLabels[stage] || stage)}</option>`).join("")}`;
  $("#crmStageFilter").value = state.stages.includes(selected) ? selected : "";
  const group = $("#bulkGroupSelect");
  const selectedGroup = group.value;
  group.innerHTML = `<option value="">Sélectionner un groupe…</option>${state.stages.map((stage) => `<option value="${escapeHtml(stage)}">${escapeHtml(stageLabels[stage] || stage)}</option>`).join("")}`;
  group.value = state.stages.includes(selectedGroup) ? selectedGroup : "";
}

async function loadProspects() {
  try {
    const query = currentCrmQuery();
    const data = await api(`/api/prospects${query ? `?${query}` : ""}`);
    state.prospects = data.prospects || [];
    state.stages = data.stages || stageOrder;
    state.priorities = data.priorities || ["low", "normal", "high"];
    state.stats = data.stats || {};
    const visibleIds = new Set(state.prospects.map((prospect) => prospect.id));
    state.selectedIds = new Set([...state.selectedIds].filter((id) => visibleIds.has(id)));
    renderFilterOptions(); renderStats(); renderPipeline();
  } catch (error) { showToast(error.message); }
}

function renderPipeline() {
  $("#pipeline").innerHTML = state.stages.map((stage) => {
    const prospects = state.prospects.filter((prospect) => prospect.stage === stage);
    return `<section class="stage-column"><div class="stage-head"><div><h3>${escapeHtml(stageLabels[stage] || stage)}</h3><small>${prospects.length} contact${prospects.length > 1 ? "s" : ""}</small></div><span>${state.stats?.byStage?.[stage] || 0}</span></div>${prospects.length ? prospects.map(renderCrmCard).join("") : `<div class="column-empty">Aucun prospect</div>`}</section>`;
  }).join("");
  document.querySelectorAll("[data-open-prospect]").forEach((button) => button.addEventListener("click", () => openProspect(Number(button.dataset.openProspect))));
  document.querySelectorAll("[data-email-id]").forEach((button) => button.addEventListener("click", () => openEmail(Number(button.dataset.emailId))));
  document.querySelectorAll("[data-next-id]").forEach((button) => button.addEventListener("click", () => moveNext(Number(button.dataset.nextId))));
  document.querySelectorAll("[data-delete-id]").forEach((button) => button.addEventListener("click", () => { state.selectedIds = new Set([Number(button.dataset.deleteId)]); deleteSelected(); }));
  document.querySelectorAll("[data-select-id]").forEach((input) => input.addEventListener("change", () => toggleSelection(Number(input.dataset.selectId), input.checked)));
  updateSelectionUi();
}

function renderCrmCard(prospect) {
  const overdue = isOverdue(prospect);
  const contact = prospect.contact_name || prospect.email || "Contact à qualifier";
  return `<article class="crm-card ${overdue ? "is-overdue" : ""}"><div class="crm-card-select"><label><input type="checkbox" data-select-id="${prospect.id}" ${state.selectedIds.has(prospect.id) ? "checked" : ""} /><span>Sélectionner</span></label></div><button class="crm-card-main" data-open-prospect="${prospect.id}" type="button"><div class="crm-card-top"><h4 title="${escapeHtml(prospect.business_name)}">${escapeHtml(prospect.business_name)}</h4><span class="priority-dot priority-${escapeHtml(prospect.priority || "normal")}" title="Priorité ${escapeHtml(prospect.priority || "normal")}"></span></div><p>${escapeHtml(contact)}</p><p>${escapeHtml(prospect.profession || "Profession non renseignée")} · ${escapeHtml(prospect.region || "Région non renseignée")}</p>${prospect.nextAction ? `<p class="next-action ${overdue ? "overdue-text" : ""}">${overdue ? "⚠ " : "↳ "}${escapeHtml(prospect.nextAction)}${prospect.nextActionAt ? ` · ${escapeHtml(formatDate(prospect.nextActionAt))}` : ""}</p>` : ""}<div class="crm-card-footer"><span>${prospect.dealValue ? formatCurrency(prospect.dealValue) : "Sans montant"}</span><span>${prospect.lastContactAt ? `Dernier contact ${escapeHtml(formatDate(prospect.lastContactAt))}` : "Jamais contacté"}</span></div></button><div class="card-actions"><button data-email-id="${prospect.id}" type="button">✉ Email</button><button data-next-id="${prospect.id}" type="button">Étape →</button><button data-delete-id="${prospect.id}" type="button">Effacer</button></div></article>`;
}

function toggleSelection(id, checked) {
  if (checked) state.selectedIds.add(id); else state.selectedIds.delete(id);
  updateSelectionUi();
}

function updateSelectionUi() {
  const visibleIds = state.prospects.map((prospect) => prospect.id);
  const selectedVisible = visibleIds.filter((id) => state.selectedIds.has(id));
  $("#selectionCount").textContent = `${state.selectedIds.size} sélectionné${state.selectedIds.size > 1 ? "s" : ""}`;
  $("#selectAllProspects").checked = visibleIds.length > 0 && selectedVisible.length === visibleIds.length;
  $("#bulkDeleteButton").disabled = state.selectedIds.size === 0;
  $("#bulkEmailButton").disabled = state.selectedIds.size === 0;
}

function setSelection(ids) {
  state.selectedIds = new Set(ids);
  renderPipeline();
}

function selectedProspects() {
  return state.prospects.filter((prospect) => state.selectedIds.has(prospect.id));
}

async function deleteSelected() {
  const selected = selectedProspects();
  if (!selected.length) return showToast("Sélectionnez au moins un prospect.");
  const label = selected.length === 1 ? selected[0].business_name : `${selected.length} prospects sélectionnés`;
  if (!window.confirm(`Effacer ${label} ? Cette action supprimera aussi son historique et ses tâches.`)) return;
  try {
    const data = await api("/api/prospects/bulk-delete", { method: "POST", body: JSON.stringify({ ids: selected.map((prospect) => prospect.id) }) });
    state.selectedIds.clear();
    await loadProspects();
    showToast(`${data.deleted} prospect${data.deleted > 1 ? "s" : ""} effacé${data.deleted > 1 ? "s" : ""}`);
  } catch (error) { showToast(error.message); }
}

async function validateSelectedEmails() {
  const selected = selectedProspects();
  if (!selected.length) return showToast("Sélectionnez au moins un prospect.");
  const results = [];
  for (const prospect of selected) {
    try {
      const data = await api(`/api/prospects/${prospect.id}/email`, { method: "POST", body: JSON.stringify({ senderName: $("#senderName").value, offer: $("#offer").value }) });
      results.push({ ok: true, name: prospect.business_name, email: prospect.email, subject: data.subject });
    } catch (error) {
      results.push({ ok: false, name: prospect.business_name, email: prospect.email, error: error.message });
    }
  }
  const success = results.filter((item) => item.ok).length;
  $("#bulkEmailSummary").textContent = `${success}/${results.length} brouillon${results.length > 1 ? "s" : ""} généré${results.length > 1 ? "s" : ""}. Aucun e-mail n’a été envoyé.`;
  $("#bulkEmailResults").innerHTML = results.map((item) => `<div class="bulk-result ${item.ok ? "is-ok" : "is-error"}"><strong>${item.ok ? "✓" : "!"} ${escapeHtml(item.name)}</strong><span>${escapeHtml(item.ok ? `${item.email || "Sans e-mail"} · ${item.subject}` : item.error)}</span></div>`).join("");
  $("#bulkEmailDialog").showModal();
  await loadProspects();
}

function fillProspectDetail(prospect) {
  state.selectedProspect = prospect;
  $("#prospectDialogTitle").textContent = prospect.business_name || "Prospect";
  $("#prospectDialogSubtitle").textContent = [prospect.profession, prospect.region].filter(Boolean).join(" · ") || "Informations à compléter";
  $("#prospectFitBadge").textContent = prospect.offerFit ? `Compatible FÉWURA · ${prospect.fitScore || 0}` : "Adéquation à vérifier";
  $("#detailEmail").textContent = prospect.email || "Non renseigné"; $("#detailEmail").href = prospect.email ? `mailto:${prospect.email}` : "#";
  $("#detailPhone").textContent = prospect.phone || "Non renseigné"; $("#detailPhone").href = prospect.phone ? `tel:${prospect.phone.replace(/\s/g, "")}` : "#";
  $("#detailWebsite").textContent = prospect.website || "Non renseigné"; $("#detailWebsite").href = prospect.website || "#";
  $("#detailAddress").textContent = prospect.address || "Non renseignée";
  $("#detailStage").innerHTML = state.stages.map((stage) => `<option value="${escapeHtml(stage)}">${escapeHtml(stageLabels[stage] || stage)}</option>`).join(""); $("#detailStage").value = prospect.stage;
  $("#detailPriority").value = prospect.priority || "normal"; $("#detailDealValue").value = prospect.dealValue || 0; $("#detailNextAction").value = prospect.nextAction || ""; $("#detailNextActionAt").value = prospect.nextActionAt || ""; $("#detailNotes").value = prospect.notes || ""; $("#detailOptOut").checked = Boolean(prospect.optOut);
  $("#detailLastContact").textContent = prospect.lastContactAt ? `Dernier contact : ${formatDateTime(prospect.lastContactAt)}` : "Aucun contact enregistré";
  $("#detailFitScore").textContent = `${prospect.fitScore || 0} pts`; $("#detailFitReasons").textContent = (prospect.fitReasons || []).join(" · ") || "Aucun signal détaillé";
  $("#detailAllContacts").textContent = [...(prospect.emails || []), ...(prospect.phones || [])].join(" · ") || "Aucune autre coordonnée";
  $("#detailSource").textContent = prospect.source?.title || prospect.source?.url || "Source non renseignée"; $("#detailSource").href = prospect.source?.url || "#";
}

async function openProspect(id) {
  const prospect = state.prospects.find((item) => item.id === id); if (!prospect) return;
  fillProspectDetail(prospect); $("#prospectDialog").showModal(); await loadActivities(id);
}

async function loadActivities(id) {
  try { const data = await api(`/api/prospects/${id}/activities`); state.activities = data.activities || []; renderActivities(); }
  catch (error) { showToast(error.message); }
}

function renderActivities() {
  $("#activityList").innerHTML = state.activities.length ? state.activities.map((activity) => `<article class="activity-item"><span class="activity-icon">${activity.type === "call" ? "☎" : activity.type === "email" || activity.type === "email_draft" ? "✉" : activity.type === "meeting" ? "◷" : activity.type === "stage_change" ? "→" : "•"}</span><div><div class="activity-meta"><strong>${escapeHtml(activityLabels[activity.type] || activity.type)}</strong><span>${escapeHtml(formatDateTime(activity.created_at))}</span></div><p>${escapeHtml(activity.content)}</p></div></article>`).join("") : `<div class="activity-empty">Aucune activité enregistrée.</div>`;
}

async function saveProspectDetail() {
  const prospect = state.selectedProspect; if (!prospect) return;
  try {
    const data = await api(`/api/prospects/${prospect.id}`, { method: "PATCH", body: JSON.stringify({ stage: $("#detailStage").value, priority: $("#detailPriority").value, dealValue: $("#detailDealValue").value, nextAction: $("#detailNextAction").value, nextActionAt: $("#detailNextActionAt").value, notes: $("#detailNotes").value, optOut: $("#detailOptOut").checked }) });
    fillProspectDetail(data.prospect); await loadProspects(); showToast("Fiche prospect enregistrée");
  } catch (error) { showToast(error.message); }
}

async function addActivity() {
  const prospect = state.selectedProspect; const content = $("#activityContent").value.trim(); if (!prospect || !content) return showToast("Ajoutez un contenu à l’activité.");
  try { await api(`/api/prospects/${prospect.id}/activities`, { method: "POST", body: JSON.stringify({ type: $("#activityType").value, content }) }); $("#activityContent").value = ""; await loadActivities(prospect.id); await loadProspects(); showToast("Activité ajoutée"); }
  catch (error) { showToast(error.message); }
}

async function moveNext(id) {
  const prospect = state.prospects.find((item) => item.id === id); if (!prospect) return;
  const next = state.stages[state.stages.indexOf(prospect.stage) + 1]; if (!next) return showToast("Cette carte est déjà dans la dernière colonne.");
  try { await api(`/api/prospects/${id}`, { method: "PATCH", body: JSON.stringify({ stage: next }) }); await loadProspects(); showToast("Étape du pipeline mise à jour"); }
  catch (error) { showToast(error.message); }
}

async function openEmail(id) {
  const prospect = state.prospects.find((item) => item.id === id); if (!prospect) return;
  state.selectedProspect = prospect;
  $("#emailTitle").textContent = `Message pour ${prospect.business_name}`;
  try { const data = await api(`/api/prospects/${id}/email`, { method: "POST", body: JSON.stringify({ senderName: $("#senderName").value, offer: $("#offer").value }) }); $("#emailSubject").textContent = data.subject; $("#emailBody").textContent = data.body; $("#emailHtmlPreview").innerHTML = data.html; $("#emailDisclaimer").textContent = data.disclaimer; try { await copyEmailContent(false); showToast("Corps du mail copié automatiquement"); } catch { showToast("Brouillon généré ; utilisez le bouton de copie pour le placer dans Gmail"); } $("#emailDialog").showModal(); }
  catch (error) { showToast(error.message); }
}

async function copyEmailContent(showMessage = true) {
  const text = `Objet : ${$("#emailSubject").textContent}\n\n${$("#emailBody").textContent}`;
  const html = `<!doctype html><html lang="fr"><head><meta charset="UTF-8"></head><body>${$("#emailHtmlPreview").innerHTML}</body></html>`;
  if (navigator.clipboard?.write && window.ClipboardItem) {
    await navigator.clipboard.write([new ClipboardItem({ "text/html": new Blob([html], { type: "text/html" }), "text/plain": new Blob([text], { type: "text/plain" }) })]);
  } else {
    const helper = document.createElement("div");
    helper.contentEditable = "true"; helper.innerHTML = html; helper.style.position = "fixed"; helper.style.left = "-10000px"; helper.style.top = "0";
    document.body.appendChild(helper);
    const selection = window.getSelection(); const range = document.createRange(); range.selectNodeContents(helper); selection.removeAllRanges(); selection.addRange(range);
    if (!document.execCommand("copy")) throw new Error("La copie enrichie n’est pas disponible dans ce navigateur.");
    selection.removeAllRanges(); helper.remove();
  }
  if (showMessage) showToast("Brouillon formaté copié");
}

async function openGmailCompose() {
  const prospect = state.selectedProspect;
  if (!prospect?.email) return showToast("Ce prospect n’a pas d’adresse email valide.");
  const composeUrl = new URL("https://mail.google.com/mail/u/0/");
  composeUrl.search = new URLSearchParams({ view: "cm", fs: "1", tf: "1", to: prospect.email, su: $("#emailSubject").textContent, body: $("#emailBody").textContent }).toString();
  const gmailWindow = window.open(composeUrl.toString(), "_blank", "noopener");
  if (!gmailWindow) return showToast("Gmail n’a pas pu être ouvert : autorisez les fenêtres surgissantes.");
  try { await copyEmailContent(false); showToast("Gmail ouvert ; le corps HTML est prêt à être collé"); } catch { showToast("Gmail est ouvert avec le destinataire et l’objet préremplis"); }
}

async function createGmailDraft() {
  const prospect = state.selectedProspect;
  if (!prospect) return showToast("Sélectionnez d’abord un prospect.");
  try {
    const data = await api(`/api/prospects/${prospect.id}/gmail-draft`, { method: "POST", body: JSON.stringify({ senderName: $("#senderName").value, offer: $("#offer").value }) });
    showToast(`Brouillon Gmail créé pour ${data.to}`);
    window.open("https://mail.google.com/mail/u/0/#drafts", "_blank", "noopener");
    await loadActivities(prospect.id);
  } catch (error) { showToast(error.message); }
}

function exportProspects() {
  const rows = state.prospects; if (!rows.length) return showToast("Aucun prospect à exporter dans la vue actuelle.");
  const headers = ["Entreprise", "Contact", "Profession", "Région", "Email", "Téléphone", "Étape", "Priorité", "Valeur", "Prochaine action", "Date relance", "Dernier contact", "Notes"];
  const csvValue = (value) => `"${String(value ?? "").replace(/"/g, '""')}"`;
  const csv = [headers, ...rows.map((p) => [p.business_name, p.contact_name, p.profession, p.region, p.email, p.phone, stageLabels[p.stage] || p.stage, p.priority, p.dealValue, p.nextAction, p.nextActionAt, p.lastContactAt, p.notes])].map((row) => row.map(csvValue).join(";")).join("\n");
  const link = document.createElement("a"); link.href = URL.createObjectURL(new Blob([`\uFEFF${csv}`], { type: "text/csv;charset=utf-8" })); link.download = `fewura-crm-${new Date().toISOString().slice(0, 10)}.csv`; link.click(); URL.revokeObjectURL(link.href);
}

$("#searchForm").addEventListener("submit", runSearch);
$("#refreshButton").addEventListener("click", loadProspects);
$("#exportButton").addEventListener("click", exportProspects);
$("#crmStageFilter").addEventListener("change", loadProspects); $("#crmPriorityFilter").addEventListener("change", loadProspects); $("#crmOverdueFilter").addEventListener("change", loadProspects);
$("#crmSearch").addEventListener("input", (() => { let timer; return () => { clearTimeout(timer); timer = setTimeout(loadProspects, 260); }; })());
$("#resetCrmFilters").addEventListener("click", () => { $("#crmSearch").value = ""; $("#crmStageFilter").value = ""; $("#crmPriorityFilter").value = ""; $("#crmOverdueFilter").checked = false; loadProspects(); });
$("#closeProspectDialog").addEventListener("click", () => $("#prospectDialog").close()); $("#saveProspectDetail").addEventListener("click", saveProspectDetail); $("#addActivity").addEventListener("click", addActivity);
$("#detailEmailButton").addEventListener("click", () => state.selectedProspect && openEmail(state.selectedProspect.id));
$("#selectAllProspects").addEventListener("change", (event) => setSelection(event.target.checked ? state.prospects.map((prospect) => prospect.id) : []));
$("#selectVisibleButton").addEventListener("click", () => setSelection(state.prospects.map((prospect) => prospect.id)));
$("#selectGroupButton").addEventListener("click", () => {
  const group = $("#bulkGroupSelect").value;
  if (!group) return showToast("Choisissez un groupe à sélectionner.");
  setSelection(state.prospects.filter((prospect) => prospect.stage === group).map((prospect) => prospect.id));
});
$("#clearSelectionButton").addEventListener("click", () => setSelection([]));
$("#bulkDeleteButton").addEventListener("click", deleteSelected);
$("#bulkEmailButton").addEventListener("click", validateSelectedEmails);
$("#copyEmail").addEventListener("click", async () => { try { await copyEmailContent(); } catch (error) { showToast(error.message || "Copie impossible"); } });
$("#openGmail").addEventListener("click", openGmailCompose);
$("#createGmailDraft").addEventListener("click", createGmailDraft);
loadHealth(); loadProspects();
