import "dotenv/config";
import express from "express";
import Database from "better-sqlite3";
import { google } from "googleapis";
import path from "node:path";
import { fileURLToPath } from "node:url";
import fs from "node:fs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.env.PORT || 3000);
const DATA_DIR = path.join(__dirname, "data");
const GMAIL_TOKEN_FILE = path.join(DATA_DIR, "gmail-token.json");
fs.mkdirSync(DATA_DIR, { recursive: true });

const db = new Database(path.join(DATA_DIR, "prospecting.db"));
db.pragma("journal_mode = WAL");
db.exec(`
  CREATE TABLE IF NOT EXISTS prospects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_name TEXT NOT NULL,
    contact_name TEXT DEFAULT '',
    profession TEXT DEFAULT '',
    region TEXT DEFAULT '',
    email TEXT DEFAULT '',
    phone TEXT DEFAULT '',
    emails_json TEXT DEFAULT '[]',
    phones_json TEXT DEFAULT '[]',
    offer_fit INTEGER NOT NULL DEFAULT 0,
    fit_score INTEGER NOT NULL DEFAULT 0,
    fit_reasons_json TEXT DEFAULT '[]',
    website TEXT DEFAULT '',
    address TEXT DEFAULT '',
    source_url TEXT DEFAULT '',
    source_title TEXT DEFAULT '',
    source_snippet TEXT DEFAULT '',
    collected_at TEXT DEFAULT '',
    confidence TEXT DEFAULT 'à vérifier',
    stage TEXT NOT NULL DEFAULT 'new',
    notes TEXT DEFAULT '',
    opt_out INTEGER NOT NULL DEFAULT 0,
    priority TEXT NOT NULL DEFAULT 'normal',
    deal_value REAL NOT NULL DEFAULT 0,
    next_action TEXT DEFAULT '',
    next_action_at TEXT DEFAULT '',
    last_contact_at TEXT DEFAULT '',
    tags_json TEXT DEFAULT '[]',
    sources_json TEXT DEFAULT '[]',
    account_type TEXT DEFAULT 'TPE / PME',
    contact_role TEXT DEFAULT '',
    lead_source TEXT DEFAULT 'Prospection agent',
    owner_name TEXT DEFAULT 'Jean Marc',
    probability INTEGER NOT NULL DEFAULT 0,
    expected_close_date TEXT DEFAULT '',
    lost_reason TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
  );
  CREATE UNIQUE INDEX IF NOT EXISTS idx_prospects_email ON prospects(email) WHERE email <> '';
  CREATE TABLE IF NOT EXISTS activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prospect_id INTEGER NOT NULL,
    type TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (prospect_id) REFERENCES prospects(id) ON DELETE CASCADE
  );
  CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prospect_id INTEGER,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    due_at TEXT DEFAULT '',
    priority TEXT NOT NULL DEFAULT 'normal',
    status TEXT NOT NULL DEFAULT 'open',
    owner_name TEXT DEFAULT 'Jean Marc',
    completed_at TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (prospect_id) REFERENCES prospects(id) ON DELETE CASCADE
  );
`);

const prospectColumns = new Set(db.prepare("PRAGMA table_info(prospects)").all().map((column) => column.name));
if (!prospectColumns.has("emails_json")) db.exec("ALTER TABLE prospects ADD COLUMN emails_json TEXT DEFAULT '[]'");
if (!prospectColumns.has("phones_json")) db.exec("ALTER TABLE prospects ADD COLUMN phones_json TEXT DEFAULT '[]'");
if (!prospectColumns.has("offer_fit")) db.exec("ALTER TABLE prospects ADD COLUMN offer_fit INTEGER NOT NULL DEFAULT 0");
if (!prospectColumns.has("fit_score")) db.exec("ALTER TABLE prospects ADD COLUMN fit_score INTEGER NOT NULL DEFAULT 0");
if (!prospectColumns.has("fit_reasons_json")) db.exec("ALTER TABLE prospects ADD COLUMN fit_reasons_json TEXT DEFAULT '[]'");
if (!prospectColumns.has("priority")) db.exec("ALTER TABLE prospects ADD COLUMN priority TEXT NOT NULL DEFAULT 'normal'");
if (!prospectColumns.has("deal_value")) db.exec("ALTER TABLE prospects ADD COLUMN deal_value REAL NOT NULL DEFAULT 0");
if (!prospectColumns.has("next_action")) db.exec("ALTER TABLE prospects ADD COLUMN next_action TEXT DEFAULT ''");
if (!prospectColumns.has("next_action_at")) db.exec("ALTER TABLE prospects ADD COLUMN next_action_at TEXT DEFAULT ''");
if (!prospectColumns.has("last_contact_at")) db.exec("ALTER TABLE prospects ADD COLUMN last_contact_at TEXT DEFAULT ''");
if (!prospectColumns.has("tags_json")) db.exec("ALTER TABLE prospects ADD COLUMN tags_json TEXT DEFAULT '[]'");
if (!prospectColumns.has("sources_json")) db.exec("ALTER TABLE prospects ADD COLUMN sources_json TEXT DEFAULT '[]'");
if (!prospectColumns.has("account_type")) db.exec("ALTER TABLE prospects ADD COLUMN account_type TEXT DEFAULT 'TPE / PME'");
if (!prospectColumns.has("contact_role")) db.exec("ALTER TABLE prospects ADD COLUMN contact_role TEXT DEFAULT ''");
if (!prospectColumns.has("lead_source")) db.exec("ALTER TABLE prospects ADD COLUMN lead_source TEXT DEFAULT 'Prospection agent'");
if (!prospectColumns.has("owner_name")) db.exec("ALTER TABLE prospects ADD COLUMN owner_name TEXT DEFAULT 'Jean Marc'");
if (!prospectColumns.has("probability")) db.exec("ALTER TABLE prospects ADD COLUMN probability INTEGER NOT NULL DEFAULT 0");
if (!prospectColumns.has("expected_close_date")) db.exec("ALTER TABLE prospects ADD COLUMN expected_close_date TEXT DEFAULT ''");
if (!prospectColumns.has("lost_reason")) db.exec("ALTER TABLE prospects ADD COLUMN lost_reason TEXT DEFAULT ''");

const app = express();
app.use(express.json({ limit: "1mb" }));
app.use(express.static(path.join(__dirname, "public")));

const STAGES = ["new", "qualified", "contacted", "replied", "meeting", "proposal", "won", "lost", "excluded"];
const PRIORITIES = ["low", "normal", "high"];
const ACTIVITY_TYPES = ["note", "call", "email", "meeting", "task", "stage_change", "email_draft", "gmail_draft"];
const TASK_STATUSES = ["open", "in_progress", "done", "cancelled"];
const ALL_ACTIVITIES = "toutes les activités";

function now() {
  return new Date().toISOString();
}

function braveKey() {
  return String(process.env.BRAVE_SEARCH_API_KEY || "").trim().replace(/\s+Brave\s*$/i, "");
}

function hunterKey() {
  return String(process.env.HUNTER_API_KEY || "").trim();
}

function hunterLimit() {
  return Math.min(Math.max(Number(process.env.HUNTER_MAX_LOOKUPS) || 5, 0), 50);
}

function isAllActivities(value) {
  return normalizedText(value) === normalizedText(ALL_ACTIVITIES);
}

const GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.compose"];

function gmailConfig() {
  return {
    account: String(process.env.GMAIL_ACCOUNT || "softwareinnovatech@gmail.com").trim(),
    clientId: String(process.env.GMAIL_CLIENT_ID || "").trim(),
    clientSecret: String(process.env.GMAIL_CLIENT_SECRET || "").trim(),
    redirectUri: String(process.env.GMAIL_REDIRECT_URI || `http://localhost:${PORT}/auth/gmail/callback`).trim(),
    refreshToken: String(process.env.GMAIL_REFRESH_TOKEN || "").trim()
  };
}

function readGmailTokens() {
  try { return JSON.parse(fs.readFileSync(GMAIL_TOKEN_FILE, "utf8")); } catch { return {}; }
}

function writeGmailTokens(tokens) {
  fs.writeFileSync(GMAIL_TOKEN_FILE, JSON.stringify(tokens, null, 2), { encoding: "utf8", mode: 0o600 });
}

function gmailOAuthClient() {
  const config = gmailConfig();
  if (!config.clientId || !config.clientSecret) throw new Error("GMAIL_CLIENT_ID et GMAIL_CLIENT_SECRET doivent être renseignés dans .env.");
  return new google.auth.OAuth2(config.clientId, config.clientSecret, config.redirectUri);
}

function gmailRefreshToken() {
  return gmailConfig().refreshToken || readGmailTokens().refresh_token || "";
}

function gmailIsAuthorized() {
  return Boolean(gmailConfig().clientId && gmailConfig().clientSecret && gmailRefreshToken());
}

function authorizedGmailClient() {
  const refreshToken = gmailRefreshToken();
  if (!refreshToken) throw new Error("Gmail n’est pas encore autorisé. Ouvrez /auth/gmail pour autoriser la boîte professionnelle.");
  const client = gmailOAuthClient();
  client.setCredentials({ refresh_token: refreshToken });
  return client;
}

function base64Url(value) {
  return Buffer.from(value).toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

function encodedMimeHeader(value) {
  return `=?UTF-8?B?${Buffer.from(value, "utf8").toString("base64")}?=`;
}

function buildGmailRawMessage({ to, subject, body, html }) {
  const boundary = `fewura_${Date.now()}_${Math.random().toString(16).slice(2)}`;
  const raw = [
    `To: ${to}`,
    `Subject: ${encodedMimeHeader(subject)}`,
    "MIME-Version: 1.0",
    `Content-Type: multipart/alternative; boundary="${boundary}"`,
    "",
    `--${boundary}`,
    "Content-Type: text/plain; charset=UTF-8",
    "Content-Transfer-Encoding: base64",
    "",
    Buffer.from(body, "utf8").toString("base64"),
    `--${boundary}`,
    "Content-Type: text/html; charset=UTF-8",
    "Content-Transfer-Encoding: base64",
    "",
    Buffer.from(html, "utf8").toString("base64"),
    `--${boundary}--`,
    ""
  ].join("\r\n");
  return base64Url(raw);
}

function clean(value, max = 2000) {
  return String(value ?? "").trim().slice(0, max);
}

function unique(values) {
  return [...new Set(values.filter(Boolean))];
}

function escapeEmailHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char]));
}

const OFFER_SIGNAL_GROUPS = [
  { label: "gestion et opérations", terms: ["commande", "devis", "factur", "document", "stock", "planning", "production", "livraison", "chantier", "reservation"] },
  { label: "clients et commercial", terms: ["client", "demande", "rendez-vous", "reponse", "relance", "support"] },
  { label: "pilotage", terms: ["suivi", "activite", "equipe", "agenda", "catalogue"] }
];

const PUBLIC_ENTITY_TERMS = [
  "mairie", "collectivite", "prefecture", "ministere",
  "conseil municipal", "service public", "hotel de ville", "office public",
  "syndicat intercommunal", "universite publique", "hopital public"
];

const PROFESSION_VARIANTS = {
  plomberie: ["plombier", "entreprise plomberie", "artisan plombier", "plombier chauffagiste"],
  "électricité bâtiment": ["électricien", "entreprise électricité", "artisan électricien"],
  "chauffage climatisation": ["chauffagiste", "climaticien", "entreprise chauffage"],
  menuiserie: ["menuisier", "entreprise menuiserie", "artisan menuisier"],
  "couverture toiture": ["couvreur", "entreprise couverture", "artisan couvreur"],
  "entreprise de rénovation": ["entreprise rénovation", "artisan rénovation", "rénovation bâtiment"],
  "garage automobile carrosserie": ["garage automobile", "carrossier", "réparateur automobile"],
  "boulangerie pâtisserie artisanale": ["boulanger", "boulangerie", "pâtisserie artisanale"],
  "cabinet comptable": ["expert comptable", "cabinet expertise comptable", "comptable"],
  "agence immobilière": ["agent immobilier", "agence immobiliere", "transaction immobilière"]
};

function normalizedText(value) {
  return String(value || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
}

function isPublicEntity({ title, description, pageText }) {
  const text = normalizedText(`${title} ${description} ${pageText}`);
  return PUBLIC_ENTITY_TERMS.some((term) => text.includes(term))
    || /\b(commune|departement|metropole)\s+de\s+/i.test(text)
    || text.includes("conseil departemental")
    || text.includes("administration publique");
}

function qualifyForFewura({ title, description, pageText }) {
  const text = normalizedText(`${title} ${description} ${pageText}`);
  const matchedGroups = OFFER_SIGNAL_GROUPS.map((group) => ({
    label: group.label,
    terms: group.terms.filter((term) => text.includes(term))
  })).filter((group) => group.terms.length > 0);
  const matchedSignals = unique(matchedGroups.flatMap((group) => group.terms));
  const operationalSignals = matchedGroups.find((group) => group.label === "gestion et opérations")?.terms.length || 0;
  const clientSignals = matchedGroups.find((group) => group.label === "clients et commercial")?.terms.length || 0;
  const pilotageSignals = matchedGroups.find((group) => group.label === "pilotage")?.terms.length || 0;
  const fit = operationalSignals >= 1 || clientSignals >= 2 || pilotageSignals >= 1;
  return {
    fit,
    score: matchedGroups.length * 10 + matchedSignals.length,
    reasons: matchedGroups.map((group) => `${group.label}: ${group.terms.slice(0, 3).join(", ")}`)
  };
}

function htmlToText(html) {
  return html
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .replace(/<style[\s\S]*?<\/style>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/gi, " ")
    .replace(/&amp;/gi, "&")
    .replace(/&#39;|&apos;/gi, "'")
    .replace(/&quot;/gi, '"')
    .replace(/\s+/g, " ")
    .trim();
}

function extractEmails(text) {
  const blockedDomains = ["sentry.io", "wixpress.com", "cloudflare.com", "googleusercontent.com", "gstatic.com", "schema.org"];
  return unique((text.match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi) || [])
    .map((email) => email.toLowerCase())
    .filter((email) => {
      const [local, domain] = email.split("@");
      return local && domain && domain.includes(".")
        && !blockedDomains.some((blocked) => domain === blocked || domain.endsWith(`.${blocked}`))
        && !/^(noreply|no-reply|donotreply|do-not-reply|mailer-daemon)$/i.test(local)
        && !/\.(png|jpg|jpeg|gif|webp|svg)$/i.test(email);
    }));
}

function extractPhones(text) {
  const matches = text.match(/(?:\+33|0033|0)[\s.\-()]*[1-9](?:[\s.\-()]*\d){8}/g) || [];
  return unique(matches.map((phone) => phone.replace(/\s+/g, " ").trim()));
}

function departmentCode(region) {
  const normalizedRegion = normalizedText(region);
  if (normalizedRegion.includes("correz") || /(?:^|\D)19(?:\D|$)/.test(normalizedRegion)) return "19";
  return "";
}

async function fetchJson(url, options = {}, timeoutMs = 12000) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { ...options, signal: controller.signal });
    const payload = await response.json().catch(() => ({}));
    return { response, payload };
  } finally {
    clearTimeout(timeout);
  }
}

function registryResultToCandidate(item, profession, region) {
  const establishment = item.siege || item.matching_etablissements?.[0] || {};
  const address = [establishment.adresse, establishment.code_postal, establishment.libelle_commune].filter(Boolean).join(", ");
  const postalCode = clean(establishment.code_postal || "", 10);
  return {
    businessName: clean(item.nom_complet || item.nom_raison_sociale || "Entreprise identifiée", 160),
    profession,
    region,
    address: clean(address, 240),
    postalCode,
    regionMatch: !departmentCode(region) || postalCode.startsWith(departmentCode(region)),
    website: "",
    email: "",
    phone: "",
    siret: clean(establishment.siret || item.siret || "", 20),
    siren: clean(item.siren || "", 20),
    activityCode: clean(establishment.activite_principale || "", 20),
    sources: [{ name: "API Recherche d’entreprises", type: "registry", status: "found", url: "https://recherche-entreprises.api.gouv.fr/" }]
  };
}

async function searchOfficialBusinesses({ region, profession, limit }) {
  const department = departmentCode(region);
  try {
    const normalizedProfession = normalizedText(profession);
    const allActivities = isAllActivities(profession);
    const variantKey = Object.keys(PROFESSION_VARIANTS).find((key) => normalizedText(key) === normalizedProfession);
    const registryBroadTerms = allActivities
      ? ["entreprise", "société", "commerce", "artisan", "services"]
      : normalizedProfession.includes("immobilier")
      ? ["immobilier", "agence", "gestion immobilière", "transaction immobilière"]
      : [];
    const terms = unique([...(allActivities ? [] : [profession]), ...(PROFESSION_VARIANTS[variantKey] || []), ...registryBroadTerms]).slice(0, 8);
    const requests = terms.flatMap((term) => [1, 2].map((page) => ({ term, page })));
    const responses = await Promise.all(requests.map(async ({ term, page }) => {
      const params = new URLSearchParams({ q: department ? term : `${term} ${region}`, page: String(page), per_page: "20" });
      if (department) params.set("departement", department);
      try {
        const { response, payload } = await fetchJson(`https://recherche-entreprises.api.gouv.fr/search?${params}`, { headers: { Accept: "application/json", "User-Agent": "FEWURA-Prospecting-Agent/1.0" } }, 12000);
        return response.ok ? (payload.results || []) : [];
      } catch { return []; }
    }));
    const candidates = [...new Map(responses.flat().filter((item) => !item.siege?.etat_administratif || item.siege.etat_administratif === "A").map((item) => [item.siren || item.nom_complet, registryResultToCandidate(item, profession, region)])).values()].filter((candidate) => candidate.regionMatch).slice(0, Math.min(Math.max(limit * 4, 20), 120));
    return { candidates, source: { name: "API Recherche d’entreprises", type: "registry", status: "used", count: candidates.length, url: "https://recherche-entreprises.api.gouv.fr/" } };
  } catch (error) {
    return { candidates: [], source: { name: "API Recherche d’entreprises", type: "registry", status: "unavailable", error: clean(error.message, 200), url: "https://recherche-entreprises.api.gouv.fr/" } };
  }
}

function overpassRegex(value) {
  return normalizedText(value).replace(/[^a-z0-9 ]/g, " ").trim().split(/\s+/).filter(Boolean).slice(0, 5).join("|") || "entreprise";
}

async function searchOpenStreetMap({ region, profession, limit }) {
  const endpoints = unique([
    String(process.env.OVERPASS_API_URL || "https://overpass-api.de/api/interpreter").trim(),
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter"
  ]).slice(0, 2);
  const area = String(region || "").replace(/["\\]/g, " ").trim();
  const professionPattern = overpassRegex(profession);
  const normalizedProfession = normalizedText(profession);
    const selectors = isAllActivities(profession)
      ? [`nwr["name"](area.searchArea)`]
      : [`nwr["name"~"${professionPattern}",i](area.searchArea)`];
  if (normalizedProfession.includes("immobilier")) selectors.push('nwr["office"="estate_agent"](area.searchArea)');
  if (normalizedProfession.includes("plomb")) selectors.push('nwr["craft"="plumber"](area.searchArea)');
  if (normalizedProfession.includes("electric")) selectors.push('nwr["craft"="electrician"](area.searchArea)');
  const query = `[out:json][timeout:20];area["name"="${area}"]["boundary"="administrative"]->.searchArea;(${selectors.join(";")};);out center tags;`;
  for (const endpoint of endpoints) {
    try {
      const { response, payload } = await fetchJson(endpoint, {
        method: "POST",
        headers: { Accept: "application/json", "Content-Type": "application/x-www-form-urlencoded", "User-Agent": "FEWURA-Prospecting-Agent/1.0" },
        body: new URLSearchParams({ data: query })
      }, 7000);
      if (!response.ok) continue;
      const candidates = (payload.elements || []).slice(0, limit).map((element) => {
        const tags = element.tags || {};
        return {
          businessName: clean(tags.name || "Entreprise identifiée", 160),
          profession,
          region,
          address: clean([tags["addr:street"], tags["addr:housenumber"], tags["addr:postcode"], tags["addr:city"]].filter(Boolean).join(" "), 240),
          website: clean(tags.website || tags["contact:website"] || "", 500),
          email: clean(tags.email || tags["contact:email"] || "", 320).toLowerCase(),
          phone: clean(tags.phone || tags["contact:phone"] || "", 80),
          sources: [{ name: "OpenStreetMap/Overpass", type: "osm", status: "found", url: "https://www.openstreetmap.org/" }]
        };
      });
      return { candidates, source: { name: "OpenStreetMap/Overpass", type: "osm", status: "used", count: candidates.length, url: "https://www.openstreetmap.org/" } };
    } catch { /* essaie l’instance Overpass suivante */ }
  }
  return { candidates: [], source: { name: "OpenStreetMap/Overpass", type: "osm", status: "unavailable", url: endpoints[0] } };
}

function websiteDomain(url) {
  try {
    const hostname = new URL(url).hostname.toLowerCase().replace(/^www\./, "");
    if (["fnaim.fr", "pagesjaunes.fr", "superimmo.com", "seloger.com", "immodvisor.com", "leboncoin.fr"].some((domain) => hostname === domain || hostname.endsWith(`.${domain}`))) return "";
    return hostname;
  } catch { return ""; }
}

function isDirectoryUrl(url) {
  try {
    const hostname = new URL(url).hostname.toLowerCase().replace(/^www\./, "");
    return ["fnaim.fr", "pagesjaunes.fr", "superimmo.com", "seloger.com", "immodvisor.com", "leboncoin.fr", "rubypayeur.com", "pappers.fr", "societe.com", "annuaire-entreprises.data.gouv.fr", "leguidepratique.com", "infonet.fr", "avendrealouer.fr", "meilleur-artisan.com", "lefigaro.fr", "crunchbase.com"].some((domain) => hostname === domain || hostname.endsWith(`.${domain}`));
  } catch { return false; }
}

function filterUsableEmails(emails, sourceUrl = "") {
  let sourceDomain = "";
  try { sourceDomain = new URL(sourceUrl).hostname.toLowerCase().replace(/^www\./, ""); } catch { /* URL absente */ }
  return unique(emails).filter((email) => {
    const [local, domain] = String(email).toLowerCase().split("@");
    if (!local || !domain || /^\.+/.test(local)) return false;
    if (String(email).toLowerCase().includes("exemple") || String(email).toLowerCase().includes("example")) return false;
    if (/^(adresse|email|mail|test|demo|exemple|example|noreply|no-reply|webmaster|postmaster|dpo|rgpd|privacy|legal|abuse)$/.test(local)) return false;
    if (/^(example\.com|example\.fr|mail\.com|test\.com)$/.test(domain)) return false;
    if (isDirectoryUrl(sourceUrl) && (domain === sourceDomain || domain.endsWith(`.${sourceDomain}`))) return false;
    return true;
  });
}

function textMatchesRegion(region, text) {
  const normalizedRegion = normalizedText(region);
  const normalized = normalizedText(text);
  if (normalizedRegion.includes("correz")) {
    return normalized.includes("correze") || /\b19\d{3}\b/.test(normalized)
      || ["brive", "tulle", "ussel", "malemort", "objat", "egletons", "bort-les-orgues", "meymac", "neuvic", "argentat", "beynat", "saint-sornin-lavolps"].some((city) => normalized.includes(normalizedText(city)));
  }
  return normalized.includes(normalizedRegion);
}

function matchesRegistryCandidate(candidate, result) {
  const text = normalizedText(`${result.title || ""} ${result.url || ""}`);
  const tokens = normalizedText(candidate.businessName)
    .replace(/[^a-z0-9]/g, " ")
    .split(/\s+/)
    .filter((token) => token.length >= 4 && !["agence", "immobilier", "immobiliere", "groupe", "societe", "entreprise"].includes(token));
  return tokens.some((token) => text.includes(token));
}

function emailMatchesBusiness(email, candidate, businessName) {
  const domain = String(email).toLowerCase().split("@")[1] || "";
  const tokens = normalizedText(candidate?.businessName || businessName)
    .replace(/[^a-z0-9]/g, " ")
    .split(/\s+/)
    .filter((token) => token.length >= 4 && !["agence", "immobilier", "immobiliere", "groupe", "societe", "entreprise", "contact"].includes(token));
  return tokens.some((token) => domain.includes(token));
}

async function hunterDomainSearch(domain, company = "") {
  if (!hunterKey() || (!domain && !company)) return { emails: [], domain: "", source: { name: "Hunter API", type: "hunter", status: "not_configured" } };
  try {
    const params = new URLSearchParams({ limit: "5", api_key: hunterKey() });
    if (domain) params.set("domain", domain);
    else params.set("company", company);
    const { response, payload } = await fetchJson(`https://api.hunter.io/v2/domain-search?${params}`, { headers: { Accept: "application/json", "User-Agent": "FEWURA-Prospecting-Agent/1.0" } }, 12000);
    if (!response.ok) return { emails: [], domain: "", source: { name: "Hunter API", type: "hunter", status: "unavailable" } };
    const emails = unique((payload.data?.emails || []).map((item) => item.value).filter(Boolean).map((email) => email.toLowerCase()));
    return { emails, domain: payload.data?.domain || domain || "", source: { name: "Hunter API", type: "hunter", status: emails.length ? "found" : "no_result", count: emails.length } };
  } catch {
    return { emails: [], domain: "", source: { name: "Hunter API", type: "hunter", status: "unavailable" } };
  }
}

function hunterMatchesCompany(candidate, hunter) {
  const domain = normalizedText(hunter.domain).replace(/[^a-z0-9]/g, " ");
  const tokens = normalizedText(candidate.businessName)
    .replace(/[^a-z0-9]/g, " ")
    .split(/\s+/)
    .filter((token) => token.length >= 4 && !["agence", "immobilier", "immobiliere", "groupe", "societe", "entreprise"].includes(token));
  return tokens.some((token) => domain.includes(token));
}

function extractContactLinks(baseUrl, html) {
  if (!/^https?:\/\//i.test(baseUrl)) return [];
  let base;
  try { base = new URL(baseUrl); } catch { return []; }
  const links = [];
  const pattern = /<a\b[^>]*href\s*=\s*["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/gi;
  let match;
  while ((match = pattern.exec(html)) && links.length < 8) {
    const [href, label] = [match[1], htmlToText(match[2])];
    const signal = normalizedText(`${href} ${label}`);
    if (!/(contact|contactez|nous-ecrire|equipe|agence|immobilier|a-propos|mentions-legales|coordonnees|brive|tulle|ussel|malemort|objat|meymac|egletons)/.test(signal)) continue;
    try {
      const candidate = new URL(href, baseUrl);
      if (!/^https?:$/i.test(candidate.protocol) || candidate.hostname !== base.hostname) continue;
      candidate.hash = "";
      if (candidate.pathname === base.pathname && candidate.search === base.search) continue;
      if (/\.(pdf|jpg|jpeg|png|gif|svg|webp|zip)$/i.test(candidate.pathname)) continue;
      links.push(candidate.toString());
    } catch { /* lien relatif invalide */ }
  }
  return unique(links).slice(0, 6);
}

async function inspectPublicPage(url, followContactPages = true) {
  if (!/^https?:\/\//i.test(url)) return { emails: [], phones: [], pageText: "", contactUrls: [] };
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 6000);
  try {
    const response = await fetch(url, {
      signal: controller.signal,
      redirect: "follow",
      headers: { "user-agent": "FÉWURA-Prospecting-Agent/0.1 (public-business-research)" }
    });
    if (!response.ok) return { emails: [], phones: [], pageText: "", contactUrls: [] };
    const type = response.headers.get("content-type") || "";
    if (!type.includes("text/html")) return { emails: [], phones: [], pageText: "", contactUrls: [] };
    const html = (await response.text()).slice(0, 1_500_000);
    const text = htmlToText(html);
    const own = { emails: extractEmails(`${html} ${text}`), phones: extractPhones(text), pageText: text.slice(0, 120000), contactUrls: extractContactLinks(url, html) };
    if (!followContactPages || own.contactUrls.length === 0 || (own.emails.length > 0 && own.phones.length > 0)) return own;
    const contactPages = await Promise.all(own.contactUrls.map((contactUrl) => inspectPublicPage(contactUrl, false)));
    return {
      emails: unique([own.emails, ...contactPages.map((page) => page.emails)].flat()),
      phones: unique([own.phones, ...contactPages.map((page) => page.phones)].flat()),
      pageText: [own.pageText, ...contactPages.map((page) => page.pageText)].join(" ").slice(0, 120000),
      contactUrls: own.contactUrls
    };
  } catch {
    return { emails: [], phones: [], pageText: "", contactUrls: [] };
  } finally {
    clearTimeout(timeout);
  }
}

function buildSearchQuery(region, professions) {
  return buildSearchQueries(region, professions)[0];
}

function buildSearchQueries(region, professions) {
  if (professions.some(isAllActivities)) {
    const exclusions = "-mairie -metropole -prefecture -ministere";
    return unique([
      `entreprises ${region} contact email ${exclusions}`,
      `sociétés ${region} email ${exclusions}`,
      `commerces ${region} contact ${exclusions}`,
      `artisans ${region} email ${exclusions}`,
      `services ${region} contact email ${exclusions}`
    ]).slice(0, 8);
  }
  const variants = unique(professions.flatMap((profession) => {
    const normalizedProfession = normalizedText(profession);
    const variantKey = Object.keys(PROFESSION_VARIANTS).find((key) => normalizedText(key) === normalizedProfession);
    return [profession, ...(PROFESSION_VARIANTS[variantKey] || [])];
  }));
  const exclusions = "-mairie -metropole -prefecture -ministere";
  const normalizedRegion = normalizedText(region);
  const locations = normalizedRegion.includes("correz")
    ? ["Corrèze", "Brive-la-Gaillarde", "Tulle", "Ussel", "Malemort", "Objat", "Égletons", "Bort-les-Orgues", "Meymac"]
    : [region];
  const queries = [];
  if (normalizedRegion.includes("correz")) {
    queries.push(
      `${variants[0]} ${region} email ${exclusions}`,
      `${variants[0]} ${region} contact ${exclusions}`,
      ...variants.slice(1, 2).map((variant) => `${variant} ${region} contact email ${exclusions}`),
      `site:fnaim.fr agences immobilières Corrèze email`,
      `site:pagesjaunes.fr agences immobilières Corrèze`,
      `site:superimmo.com agences immobilières Corrèze`
    );
    for (const location of locations.slice(0, 9)) queries.push(`${variants[0]} ${location} contact email ${exclusions}`);
    return unique(queries).slice(0, 16);
  }
  for (const variant of variants.slice(0, 5)) queries.push(`${variant} ${region} ${exclusions}`);
  queries.push(...variants.slice(0, 3).map((variant) => `${variant} ${region} contact email ${exclusions}`));
  return unique(queries).slice(0, 8);
}

async function braveSearch({ region, professions, count }) {
  const key = braveKey();
  if (!key) throw new Error("BRAVE_SEARCH_API_KEY est absente du fichier .env.");
  const requestedCount = Math.min(Math.max(Number(count) || 10, 1), 20);
  const primaryProfession = professions[0] || "entreprise";
  const [registry, osm] = await Promise.all([
    searchOfficialBusinesses({ region, profession: primaryProfession, limit: requestedCount * 3 }),
    searchOpenStreetMap({ region, profession: primaryProfession, limit: requestedCount * 3 })
  ]);
  const sourceCandidates = unique([...registry.candidates, ...osm.candidates].map((candidate) => candidate.businessName)).slice(0, Math.min(Math.max(requestedCount * 2, 10), 30));
  const seedQueries = sourceCandidates.map((businessName) => `"${businessName}" ${region} contact email`);
  const queries = unique([...seedQueries, ...buildSearchQueries(region, professions).slice(0, 16)]).slice(0, 46);
  const searchResponses = await Promise.all(queries.map(async (query) => {
    const params = new URLSearchParams({ q: query, count: "20", search_lang: "fr", country: "fr" });
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 12000);
    try {
      const response = await fetch(`https://api.search.brave.com/res/v1/web/search?${params}`, {
        signal: controller.signal,
        headers: { Accept: "application/json", "X-Subscription-Token": key }
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) return [];
      return payload?.web?.results || [];
    } catch {
      return [];
    } finally {
      clearTimeout(timeout);
    }
  }));
  const osmWebsiteResults = osm.candidates.filter((candidate) => candidate.website).map((candidate) => ({
    url: candidate.website,
    title: candidate.businessName,
    description: candidate.address,
    osmCandidate: candidate
  }));
  const uniqueResults = [...new Map([...searchResponses.flat(), ...osmWebsiteResults].filter((result) => result.url).map((result) => {
    try {
      const canonical = new URL(result.url);
      canonical.search = "";
      canonical.hash = "";
      return [canonical.toString().replace(/\/$/, ""), result];
    } catch { return [result.url, result]; }
  })).values()].sort((left, right) => {
    const rightEmail = extractEmails(`${right.title || ""} ${right.description || ""}`).length;
    const leftEmail = extractEmails(`${left.title || ""} ${left.description || ""}`).length;
    return rightEmail - leftEmail;
  });
  const candidateLimit = Math.min(Math.max(requestedCount * 2, 20), 40);
  const inspected = (await Promise.all(uniqueResults.slice(0, candidateLimit).map(async (result, resultIndex) => {
    const contacts = await inspectPublicPage(result.url, false);
    const snippetEmails = extractEmails(`${result.title || ""} ${result.description || ""}`);
    const snippetPhones = extractPhones(`${result.title || ""} ${result.description || ""}`);
    const registryCandidate = registry.candidates.find((candidate) => normalizedText(result.title).includes(normalizedText(candidate.businessName)) || normalizedText(candidate.businessName).includes(normalizedText(result.title)) || matchesRegistryCandidate(candidate, result));
    const osmCandidate = result.osmCandidate || osm.candidates.find((candidate) => websiteDomain(candidate.website) && websiteDomain(candidate.website) === websiteDomain(result.url));
    contacts.emails = filterUsableEmails([...contacts.emails, ...snippetEmails, ...(osmCandidate?.email ? [osmCandidate.email] : [])], result.url);
    contacts.phones = unique([...contacts.phones, ...snippetPhones, ...(osmCandidate?.phone ? [osmCandidate.phone] : [])]);
    const directoryPage = /(fnaim\.fr|pagesjaunes\.fr|superimmo\.com|seloger\.com|immodvisor\.com|leboncoin\.fr)/i.test(result.url || "");
    if (contacts.emails.length === 0 && contacts.contactUrls?.length && (resultIndex < 20 || directoryPage)) {
      const contactPages = await Promise.all(contacts.contactUrls.slice(0, directoryPage ? 5 : 1).map((contactUrl) => inspectPublicPage(contactUrl, false)));
      contacts.emails = filterUsableEmails([...contacts.emails, ...contactPages.flatMap((page) => page.emails)], result.url);
      contacts.phones = unique([...contacts.phones, ...contactPages.flatMap((page) => page.phones)]);
      contacts.pageText = [contacts.pageText, ...contactPages.map((page) => page.pageText)].join(" ").slice(0, 120000);
    }
    let hunter = { emails: [], source: { name: "Hunter API", type: "hunter", status: "not_used" } };
    if (contacts.emails.length === 0 && resultIndex < hunterLimit()) hunter = await hunterDomainSearch(websiteDomain(result.url));
    contacts.emails = filterUsableEmails([...contacts.emails, ...hunter.emails], result.url);
    const publicEntity = isPublicEntity({ title: result.title, description: result.description, pageText: contacts.pageText });
    if (!textMatchesRegion(region, `${result.title || ""} ${result.description || ""} ${contacts.pageText || ""}`)) return null;
    const fit = qualifyForFewura({ title: result.title, description: result.description, pageText: contacts.pageText });
    const registryFit = fit.fit || Boolean(registryCandidate);
    const businessName = clean(result.title?.split(" | ")[0]?.split(" - ")[0] || result.title || "Entreprise identifiée", 160);
    if (isDirectoryUrl(result.url)) {
      contacts.emails = contacts.emails.filter((email) => emailMatchesBusiness(email, registryCandidate, businessName));
    }
    return {
      businessName,
      profession: professions.join(", "),
      region,
      email: contacts.emails[0] || "",
      phone: contacts.phones[0] || "",
      website: result.url || "",
      sourceUrl: result.url || "",
      sourceTitle: clean(result.title || "", 300),
      sourceSnippet: clean(result.description || "", 1000),
      collectedAt: now(),
      confidence: contacts.emails.length ? "email public + offre compatible" : "à vérifier",
      allEmails: contacts.emails,
      allPhones: contacts.phones,
      publicEntity,
      offerFit: registryFit,
      fitScore: fit.score + (registryCandidate ? 8 : 0),
      fitReasons: unique([...fit.reasons, ...(registryCandidate ? ["entreprise correspondante au registre officiel"] : [])]),
      sources: [
        { name: "Brave Search API", type: "brave", status: "found", url: result.url },
        { name: "Exploration du site", type: "website", status: contacts.emails.length ? "found" : "no_result", url: result.url },
        ...(registryCandidate ? registryCandidate.sources : []),
        ...(osmCandidate ? osmCandidate.sources : []),
        ...(hunter.source.status !== "not_used" ? [hunter.source] : [])
      ]
    };
  }))).filter(Boolean);
  const directOsmInspected = osm.candidates.filter((candidate) => candidate.email && !candidate.website).map((candidate) => {
    const fit = qualifyForFewura({ title: candidate.businessName, description: candidate.address, pageText: `${candidate.businessName} ${candidate.address}` });
    return {
      businessName: candidate.businessName,
      profession: candidate.profession,
      region: candidate.region,
      email: candidate.email,
      phone: candidate.phone,
      website: "",
      sourceUrl: "https://www.openstreetmap.org/",
      sourceTitle: "OpenStreetMap",
      sourceSnippet: candidate.address,
      collectedAt: now(),
      confidence: "e-mail public déclaré sur OpenStreetMap",
      allEmails: [candidate.email],
      allPhones: candidate.phone ? [candidate.phone] : [],
      publicEntity: false,
      offerFit: fit.fit,
      fitScore: fit.score,
      fitReasons: fit.reasons,
      sources: candidate.sources
    };
  });
  const knownEmails = new Set(inspected.flatMap((result) => result.allEmails || []));
  const registryCandidatesForHunter = registry.candidates
    .filter((candidate) => !candidate.email && candidate.businessName)
    .slice(0, hunterLimit());
  const registryHunterProspects = [];
  for (let offset = 0; offset < registryCandidatesForHunter.length; offset += 5) {
    const batch = registryCandidatesForHunter.slice(offset, offset + 5);
    const enrichedBatch = await Promise.all(batch.map(async (candidate) => ({ candidate, hunter: await hunterDomainSearch("", candidate.businessName) })));
    for (const { candidate, hunter } of enrichedBatch) {
      if (hunter.domain && !hunterMatchesCompany(candidate, hunter)) continue;
      const newEmails = hunter.emails.filter((email) => !knownEmails.has(email));
      if (newEmails.length === 0) continue;
      newEmails.forEach((email) => knownEmails.add(email));
      const fit = qualifyForFewura({
        title: candidate.businessName,
        description: `${candidate.profession} ${candidate.address}`,
        pageText: ""
      });
      const registryFit = fit.fit || Boolean(candidate.activityCode);
      registryHunterProspects.push({
        businessName: candidate.businessName,
        profession: candidate.profession,
        region: candidate.region,
        email: newEmails[0],
        phone: candidate.phone,
        website: hunter.domain ? `https://${hunter.domain}` : "",
        address: candidate.address,
        sourceUrl: hunter.domain ? `https://${hunter.domain}` : "https://recherche-entreprises.api.gouv.fr/",
        sourceTitle: candidate.businessName,
        sourceSnippet: candidate.address,
        collectedAt: now(),
        confidence: "e-mail professionnel associé par Hunter + entreprise active au registre",
        allEmails: newEmails,
        allPhones: candidate.phone ? [candidate.phone] : [],
        publicEntity: false,
        offerFit: registryFit,
        fitScore: fit.score + (candidate.activityCode ? 8 : 0),
        fitReasons: unique([...fit.reasons, ...(candidate.activityCode ? ["activité enregistrée au registre officiel"] : [])]),
        sources: [...candidate.sources, hunter.source]
      });
    }
  }
  const allInspected = [...inspected, ...directOsmInspected, ...registryHunterProspects];
  const withEmail = allInspected.filter((result) => result.allEmails.length > 0);
  const privateBusinesses = withEmail.filter((result) => !result.publicEntity);
  const compatible = [...new Map(privateBusinesses.filter((result) => result.offerFit).map((result) => [result.email, result])).values()];
  return {
    query: buildSearchQuery(region, professions),
    queries,
    results: compatible.slice(0, requestedCount),
    inspectedCount: allInspected.length,
    sources: [
      registry.source,
      { name: "Brave Search API", type: "brave", status: "used", count: queries.length, url: "https://api.search.brave.com/" },
      { name: "Exploration du site", type: "website", status: "used", count: inspected.length },
      osm.source,
      { name: "Hunter API", type: "hunter", status: hunterKey() ? "configured" : "not_configured" }
    ],
    rejected: {
      withoutEmail: allInspected.length - withEmail.length,
      publicEntity: withEmail.length - privateBusinesses.length,
      withoutOfferFit: privateBusinesses.length - compatible.length
    }
  };
}

function normalizeProspect(input) {
  const emails = unique([...(Array.isArray(input.allEmails) ? input.allEmails : []), input.email].map((value) => clean(value, 320).toLowerCase()));
  const phones = unique([...(Array.isArray(input.allPhones) ? input.allPhones : []), input.phone].map((value) => clean(value, 80)));
  return {
    businessName: clean(input.businessName || input.business_name, 160),
    contactName: clean(input.contactName || input.contact_name, 160),
    profession: clean(input.profession, 160),
    region: clean(input.region, 160),
    email: clean(input.email, 320).toLowerCase(),
    phone: clean(input.phone, 80),
    emails,
    phones,
    offerFit: input.offerFit === true,
    fitScore: Number(input.fitScore) || 0,
    fitReasons: Array.isArray(input.fitReasons) ? input.fitReasons.map((value) => clean(value, 300)).slice(0, 10) : [],
    website: clean(input.website, 500),
    address: clean(input.address, 300),
    sourceUrl: clean(input.sourceUrl || input.source_url, 500),
    sourceTitle: clean(input.sourceTitle || input.source_title, 300),
    sourceSnippet: clean(input.sourceSnippet || input.source_snippet, 1000),
    collectedAt: clean(input.collectedAt || input.collected_at, 80),
    confidence: clean(input.confidence, 80) || "à vérifier",
    notes: clean(input.notes, 3000),
    priority: PRIORITIES.includes(clean(input.priority, 20)) ? clean(input.priority, 20) : "normal",
    dealValue: Math.max(0, Number(input.dealValue ?? input.deal_value) || 0),
    nextAction: clean(input.nextAction || input.next_action, 500),
    nextActionAt: clean(input.nextActionAt || input.next_action_at, 40),
    lastContactAt: clean(input.lastContactAt || input.last_contact_at, 40),
    tags: Array.isArray(input.tags) ? unique(input.tags.map((value) => clean(value, 40))).slice(0, 12) : [],
    accountType: clean(input.accountType || input.account_type, 80) || "TPE / PME",
    contactRole: clean(input.contactRole || input.contact_role, 120),
    leadSource: clean(input.leadSource || input.lead_source, 120) || "Prospection agent",
    ownerName: clean(input.ownerName || input.owner_name, 120) || "Jean Marc",
    probability: Math.min(100, Math.max(0, Number(input.probability) || 0)),
    expectedCloseDate: clean(input.expectedCloseDate || input.expected_close_date, 40),
    lostReason: clean(input.lostReason || input.lost_reason, 300),
    sources: Array.isArray(input.sources) ? input.sources.slice(0, 12).map((source) => ({
      name: clean(source.name, 100), type: clean(source.type, 40), status: clean(source.status, 40), url: clean(source.url, 500), count: Number(source.count) || undefined
    })) : []
  };
}

function rowToProspect(row) {
  if (!row) return null;
  return {
    ...row,
    emails: JSON.parse(row.emails_json || "[]"),
    phones: JSON.parse(row.phones_json || "[]"),
    offerFit: Boolean(row.offer_fit),
    fitScore: row.fit_score,
    fitReasons: JSON.parse(row.fit_reasons_json || "[]"),
    optOut: Boolean(row.opt_out),
    priority: PRIORITIES.includes(row.priority) ? row.priority : "normal",
    dealValue: Number(row.deal_value) || 0,
    nextAction: row.next_action || "",
    nextActionAt: row.next_action_at || "",
    lastContactAt: row.last_contact_at || "",
    tags: JSON.parse(row.tags_json || "[]"),
    sources: JSON.parse(row.sources_json || "[]"),
    accountType: row.account_type || "TPE / PME",
    contactRole: row.contact_role || "",
    leadSource: row.lead_source || "Prospection agent",
    ownerName: row.owner_name || "Jean Marc",
    probability: Number(row.probability) || 0,
    expectedCloseDate: row.expected_close_date || "",
    lostReason: row.lost_reason || "",
    source: { url: row.source_url, title: row.source_title, snippet: row.source_snippet, collectedAt: row.collected_at }
  };
}

function rowToTask(row) {
  if (!row) return null;
  return {
    ...row,
    prospectId: row.prospect_id || null,
    dueAt: row.due_at || "",
    ownerName: row.owner_name || "Jean Marc",
    completedAt: row.completed_at || ""
  };
}

const listProspects = db.prepare("SELECT * FROM prospects ORDER BY updated_at DESC");
const findById = db.prepare("SELECT * FROM prospects WHERE id = ?");
const findByEmail = db.prepare("SELECT * FROM prospects WHERE email = ?");

app.get("/api/health", (_req, res) => res.json({
  ok: true,
  braveConfigured: Boolean(braveKey() && !braveKey().includes("colle-ta-cle-brave-ici")),
  hunterConfigured: Boolean(hunterKey())
}));

app.get("/api/gmail/status", async (_req, res) => {
  const config = gmailConfig();
  const configured = Boolean(config.clientId && config.clientSecret);
  const authorized = configured && gmailIsAuthorized();
  if (!authorized) return res.json({ configured, authorized: false, account: config.account });
  try {
    const gmail = google.gmail({ version: "v1", auth: authorizedGmailClient() });
    const profile = await gmail.users.getProfile({ userId: "me" });
    res.json({ configured, authorized: true, account: profile.data.emailAddress || config.account });
  } catch (error) {
    res.json({ configured, authorized: false, account: config.account, error: "Autorisation Gmail à renouveler." });
  }
});

app.get("/auth/gmail", (_req, res) => {
  try {
    const config = gmailConfig();
    const client = gmailOAuthClient();
    const url = client.generateAuthUrl({ access_type: "offline", prompt: "select_account consent", scope: GMAIL_SCOPES, login_hint: config.account });
    res.redirect(url);
  } catch (error) {
    res.status(503).send(`<h1>Configuration Gmail incomplète</h1><p>${escapeEmailHtml(error.message)}</p>`);
  }
});

app.get("/auth/gmail/callback", async (req, res) => {
  try {
    if (req.query.error) return res.status(400).send(`<h1>Autorisation Gmail annulée</h1><p>${escapeEmailHtml(req.query.error)}</p>`);
    if (!req.query.code) return res.status(400).send("Code d’autorisation Gmail absent.");
    const client = gmailOAuthClient();
    const { tokens } = await client.getToken(String(req.query.code));
    writeGmailTokens(tokens);
    res.send("<h1>Gmail est autorisé pour FÉWURA.</h1><p>Vous pouvez fermer cette fenêtre et revenir au CRM.</p>");
  } catch (error) {
    res.status(500).send(`<h1>Échec de l’autorisation Gmail</h1><p>${escapeEmailHtml(error.message)}</p>`);
  }
});

app.get("/api/prospects", (req, res) => {
  const clauses = [];
  const params = {};
  const stage = clean(req.query.stage, 30);
  const priority = clean(req.query.priority, 20);
  const region = clean(req.query.region, 160);
  const query = clean(req.query.q, 160).toLowerCase();
  if (stage && STAGES.includes(stage)) { clauses.push("stage = @stage"); params.stage = stage; }
  if (priority && PRIORITIES.includes(priority)) { clauses.push("priority = @priority"); params.priority = priority; }
  if (region) { clauses.push("region = @region"); params.region = region; }
  if (query) {
    clauses.push("(LOWER(business_name) LIKE @query OR LOWER(contact_name) LIKE @query OR LOWER(email) LIKE @query OR LOWER(phone) LIKE @query OR LOWER(profession) LIKE @query)");
    params.query = `%${query}%`;
  }
  if (String(req.query.overdue) === "true") {
    clauses.push("next_action_at <> '' AND next_action_at < @today AND stage NOT IN ('won', 'lost', 'excluded')");
    params.today = now().slice(0, 10);
  }
  const where = clauses.length ? ` WHERE ${clauses.join(" AND ")}` : "";
  const rows = db.prepare(`SELECT * FROM prospects${where} ORDER BY CASE WHEN next_action_at <> '' AND next_action_at < date('now') THEN 0 ELSE 1 END, updated_at DESC`).all(params);
  const stageCounts = db.prepare("SELECT stage, COUNT(*) AS count FROM prospects GROUP BY stage").all();
  const stats = {
    total: db.prepare("SELECT COUNT(*) AS count FROM prospects WHERE stage <> 'excluded'").get().count,
    qualified: db.prepare("SELECT COUNT(*) AS count FROM prospects WHERE stage IN ('qualified', 'contacted', 'replied', 'meeting', 'proposal')").get().count,
    openValue: db.prepare("SELECT COALESCE(SUM(deal_value), 0) AS value FROM prospects WHERE stage IN ('qualified', 'contacted', 'replied', 'meeting', 'proposal')").get().value,
    wonValue: db.prepare("SELECT COALESCE(SUM(deal_value), 0) AS value FROM prospects WHERE stage = 'won'").get().value,
    overdue: db.prepare("SELECT COUNT(*) AS count FROM prospects WHERE next_action_at <> '' AND next_action_at < date('now') AND stage NOT IN ('won', 'lost', 'excluded')").get().count,
    byStage: Object.fromEntries(stageCounts.map((item) => [item.stage, item.count]))
  };
  res.json({ prospects: rows.map(rowToProspect), stages: STAGES, priorities: PRIORITIES, stats });
});

app.get("/api/prospects/:id/activities", (req, res) => {
  const rows = db.prepare("SELECT * FROM activities WHERE prospect_id = ? ORDER BY created_at DESC").all(Number(req.params.id));
  res.json({ activities: rows });
});

app.delete("/api/prospects/:id", (req, res) => {
  const id = Number(req.params.id);
  const prospect = findById.get(id);
  if (!prospect) return res.status(404).json({ error: "Prospect introuvable." });
  const remove = db.transaction(() => {
    db.prepare("DELETE FROM activities WHERE prospect_id = ?").run(id);
    db.prepare("DELETE FROM tasks WHERE prospect_id = ?").run(id);
    db.prepare("DELETE FROM prospects WHERE id = ?").run(id);
  });
  remove();
  res.json({ deleted: 1, ids: [id] });
});

app.post("/api/prospects/bulk-delete", (req, res) => {
  const ids = Array.isArray(req.body.ids)
    ? [...new Set(req.body.ids.map((value) => Number(value)).filter((value) => Number.isInteger(value) && value > 0))]
    : [];
  if (!ids.length) return res.status(400).json({ error: "Sélectionnez au moins un prospect." });
  const placeholders = ids.map(() => "?").join(",");
  const existing = db.prepare(`SELECT id FROM prospects WHERE id IN (${placeholders})`).all(...ids).map((row) => row.id);
  if (!existing.length) return res.status(404).json({ error: "Aucun prospect sélectionné n’existe." });
  const remove = db.transaction(() => {
    const marks = existing.map(() => "?").join(",");
    db.prepare(`DELETE FROM activities WHERE prospect_id IN (${marks})`).run(...existing);
    db.prepare(`DELETE FROM tasks WHERE prospect_id IN (${marks})`).run(...existing);
    db.prepare(`DELETE FROM prospects WHERE id IN (${marks})`).run(...existing);
  });
  remove();
  res.json({ deleted: existing.length, ids: existing });
});

app.get("/api/crm/stats", (_req, res) => {
  res.json({
    total: db.prepare("SELECT COUNT(*) AS count FROM prospects WHERE stage <> 'excluded'").get().count,
    qualified: db.prepare("SELECT COUNT(*) AS count FROM prospects WHERE stage IN ('qualified', 'contacted', 'replied', 'meeting', 'proposal')").get().count,
    openValue: db.prepare("SELECT COALESCE(SUM(deal_value), 0) AS value FROM prospects WHERE stage IN ('qualified', 'contacted', 'replied', 'meeting', 'proposal')").get().value,
    wonValue: db.prepare("SELECT COALESCE(SUM(deal_value), 0) AS value FROM prospects WHERE stage = 'won'").get().value,
    overdue: db.prepare("SELECT COUNT(*) AS count FROM prospects WHERE next_action_at <> '' AND next_action_at < date('now') AND stage NOT IN ('won', 'lost', 'excluded')").get().count
  });
});

app.get("/api/dashboard", (_req, res) => {
  const today = now().slice(0, 10);
  const inSevenDays = new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10);
  const openStages = STAGES.filter((stage) => !["won", "lost", "excluded"].includes(stage));
  const total = db.prepare("SELECT COUNT(*) AS count FROM prospects WHERE stage <> 'excluded'").get().count;
  const openOpportunities = db.prepare("SELECT COUNT(*) AS count FROM prospects WHERE stage IN ('qualified','contacted','replied','meeting','proposal')").get().count;
  const pipelineValue = db.prepare("SELECT COALESCE(SUM(deal_value), 0) AS value FROM prospects WHERE stage IN ('qualified','contacted','replied','meeting','proposal')").get().value;
  const weightedPipeline = db.prepare("SELECT COALESCE(SUM(deal_value * probability / 100.0), 0) AS value FROM prospects WHERE stage IN ('qualified','contacted','replied','meeting','proposal')").get().value;
  const wonValue = db.prepare("SELECT COALESCE(SUM(deal_value), 0) AS value FROM prospects WHERE stage = 'won'").get().value;
  const wonCount = db.prepare("SELECT COUNT(*) AS count FROM prospects WHERE stage = 'won'").get().count;
  const lostCount = db.prepare("SELECT COUNT(*) AS count FROM prospects WHERE stage = 'lost'").get().count;
  const overdueProspects = db.prepare("SELECT COUNT(*) AS count FROM prospects WHERE next_action_at <> '' AND next_action_at < @today AND stage NOT IN ('won','lost','excluded')").get({ today }).count;
  const overdueTasks = db.prepare("SELECT COUNT(*) AS count FROM tasks WHERE status IN ('open','in_progress') AND due_at <> '' AND due_at < @today").get({ today }).count;
  const stagePipeline = db.prepare(`SELECT stage, COUNT(*) AS count, COALESCE(SUM(deal_value), 0) AS value, COALESCE(SUM(deal_value * probability / 100.0), 0) AS weighted_value FROM prospects WHERE stage IN (${openStages.map(() => "?").join(",")}) GROUP BY stage`).all(...openStages);
  const upcomingTasks = db.prepare(`SELECT tasks.*, prospects.business_name FROM tasks LEFT JOIN prospects ON prospects.id = tasks.prospect_id WHERE tasks.status IN ('open','in_progress') AND (tasks.due_at = '' OR tasks.due_at <= @inSevenDays) ORDER BY CASE WHEN tasks.due_at = '' THEN 1 ELSE 0 END, tasks.due_at ASC LIMIT 12`).all({ inSevenDays });
  const recentActivities = db.prepare("SELECT activities.*, prospects.business_name FROM activities LEFT JOIN prospects ON prospects.id = activities.prospect_id ORDER BY activities.created_at DESC LIMIT 12").all();
  const sourceBreakdown = db.prepare("SELECT lead_source AS source, COUNT(*) AS count FROM prospects WHERE stage <> 'excluded' GROUP BY lead_source ORDER BY count DESC").all();
  res.json({
    kpis: { total, openOpportunities, pipelineValue, weightedPipeline, wonValue, wonCount, lostCount, overdue: overdueProspects + overdueTasks, overdueProspects, overdueTasks, winRate: wonCount + lostCount ? Math.round((wonCount / (wonCount + lostCount)) * 100) : 0 },
    pipeline: stagePipeline,
    tasks: upcomingTasks.map(rowToTask),
    activities: recentActivities,
    sources: sourceBreakdown
  });
});

app.get("/api/tasks", (req, res) => {
  const clauses = [];
  const params = {};
  const status = clean(req.query.status, 20);
  const prospectId = Number(req.query.prospectId) || 0;
  if (status && TASK_STATUSES.includes(status)) { clauses.push("tasks.status = @status"); params.status = status; }
  if (prospectId) { clauses.push("tasks.prospect_id = @prospectId"); params.prospectId = prospectId; }
  if (String(req.query.overdue) === "true") { clauses.push("tasks.status IN ('open','in_progress') AND tasks.due_at <> '' AND tasks.due_at < @today"); params.today = now().slice(0, 10); }
  const where = clauses.length ? ` WHERE ${clauses.join(" AND ")}` : "";
  const rows = db.prepare(`SELECT tasks.*, prospects.business_name FROM tasks LEFT JOIN prospects ON prospects.id = tasks.prospect_id${where} ORDER BY CASE WHEN tasks.status = 'done' THEN 1 ELSE 0 END, CASE WHEN tasks.due_at = '' THEN 1 ELSE 0 END, tasks.due_at ASC, tasks.updated_at DESC`).all(params);
  res.json({ tasks: rows.map(rowToTask), statuses: TASK_STATUSES });
});

app.post("/api/tasks", (req, res) => {
  const title = clean(req.body.title, 200);
  const prospectId = Number(req.body.prospectId) || null;
  const status = clean(req.body.status, 20) || "open";
  const priority = PRIORITIES.includes(clean(req.body.priority, 20)) ? clean(req.body.priority, 20) : "normal";
  if (!title) return res.status(400).json({ error: "Le titre de la tâche est requis." });
  if (!TASK_STATUSES.includes(status)) return res.status(400).json({ error: "Statut de tâche invalide." });
  if (prospectId && !findById.get(prospectId)) return res.status(404).json({ error: "Prospect introuvable." });
  const timestamp = now();
  const result = db.prepare("INSERT INTO tasks (prospect_id, title, description, due_at, priority, status, owner_name, created_at, updated_at) VALUES (@prospectId, @title, @description, @dueAt, @priority, @status, @ownerName, @createdAt, @updatedAt)").run({ prospectId, title, description: clean(req.body.description, 2000), dueAt: clean(req.body.dueAt, 40), priority, status, ownerName: clean(req.body.ownerName, 120) || "Jean Marc", createdAt: timestamp, updatedAt: timestamp });
  if (prospectId) db.prepare("UPDATE prospects SET updated_at = ? WHERE id = ?").run(timestamp, prospectId);
  const task = db.prepare("SELECT tasks.*, prospects.business_name FROM tasks LEFT JOIN prospects ON prospects.id = tasks.prospect_id WHERE tasks.id = ?").get(result.lastInsertRowid);
  res.status(201).json({ task: rowToTask(task) });
});

app.patch("/api/tasks/:id", (req, res) => {
  const id = Number(req.params.id);
  const existing = db.prepare("SELECT * FROM tasks WHERE id = ?").get(id);
  if (!existing) return res.status(404).json({ error: "Tâche introuvable." });
  const updates = [];
  const params = { id, updatedAt: now() };
  if (Object.prototype.hasOwnProperty.call(req.body, "title")) { updates.push("title = @title"); params.title = clean(req.body.title, 200); }
  if (Object.prototype.hasOwnProperty.call(req.body, "description")) { updates.push("description = @description"); params.description = clean(req.body.description, 2000); }
  if (Object.prototype.hasOwnProperty.call(req.body, "dueAt")) { updates.push("due_at = @dueAt"); params.dueAt = clean(req.body.dueAt, 40); }
  if (Object.prototype.hasOwnProperty.call(req.body, "priority")) { const priority = clean(req.body.priority, 20); if (!PRIORITIES.includes(priority)) return res.status(400).json({ error: "Priorité invalide." }); updates.push("priority = @priority"); params.priority = priority; }
  if (Object.prototype.hasOwnProperty.call(req.body, "status")) { const status = clean(req.body.status, 20); if (!TASK_STATUSES.includes(status)) return res.status(400).json({ error: "Statut de tâche invalide." }); updates.push("status = @status"); params.status = status; params.completedAt = status === "done" ? now() : ""; updates.push("completed_at = @completedAt"); }
  if (Object.prototype.hasOwnProperty.call(req.body, "ownerName")) { updates.push("owner_name = @ownerName"); params.ownerName = clean(req.body.ownerName, 120); }
  if (updates.length) db.prepare(`UPDATE tasks SET ${updates.join(", ")}, updated_at = @updatedAt WHERE id = @id`).run(params);
  const task = db.prepare("SELECT tasks.*, prospects.business_name FROM tasks LEFT JOIN prospects ON prospects.id = tasks.prospect_id WHERE tasks.id = ?").get(id);
  res.json({ task: rowToTask(task) });
});

app.post("/api/search", async (req, res) => {
  try {
    const region = clean(req.body.region, 160);
    const professions = Array.isArray(req.body.professions)
      ? req.body.professions.map((item) => clean(item, 120)).filter(Boolean).slice(0, 8)
      : clean(req.body.profession, 120) ? [clean(req.body.profession, 120)] : [];
    if (!region || professions.length === 0) return res.status(400).json({ error: "Indiquez une région et une activité ou choisissez Toutes les activités." });
    res.json(await braveSearch({ region, professions, count: req.body.count }));
  } catch (error) {
    res.status(502).json({ error: error.message });
  }
});

app.post("/api/prospects", (req, res) => {
  const prospect = normalizeProspect(req.body);
  if (!prospect.businessName) return res.status(400).json({ error: "Le nom de l’entreprise est requis." });
  if (!prospect.email) return res.status(400).json({ error: "Un e-mail public est obligatoire pour ajouter un prospect." });
  if (!prospect.offerFit) return res.status(400).json({ error: "Ce prospect ne présente pas assez de signaux correspondant à l’offre FÉWURA." });
  const existing = prospect.email ? findByEmail.get(prospect.email) : null;
  const timestamp = now();
  if (existing) {
    db.prepare(`UPDATE prospects SET business_name=@businessName, contact_name=@contactName, profession=@profession,
      region=@region, phone=@phone, website=@website, address=@address, source_url=@sourceUrl, source_title=@sourceTitle,
      source_snippet=@sourceSnippet, collected_at=@collectedAt, confidence=@confidence, emails_json=@emailsJson,
      phones_json=@phonesJson, offer_fit=@offerFit, fit_score=@fitScore, fit_reasons_json=@fitReasonsJson, tags_json=@tagsJson, sources_json=@sourcesJson,
      account_type=@accountType, contact_role=@contactRole, lead_source=@leadSource, owner_name=@ownerName, probability=@probability,
      expected_close_date=@expectedCloseDate, lost_reason=@lostReason,
      updated_at=@updatedAt WHERE id=@id`)
      .run({ ...prospect, emailsJson: JSON.stringify(prospect.emails), phonesJson: JSON.stringify(prospect.phones), offerFit: prospect.offerFit ? 1 : 0, fitScore: prospect.fitScore, fitReasonsJson: JSON.stringify(prospect.fitReasons), tagsJson: JSON.stringify(prospect.tags), sourcesJson: JSON.stringify(prospect.sources), updatedAt: timestamp, id: existing.id });
    return res.json({ prospect: rowToProspect(findById.get(existing.id)), created: false });
  }
  const result = db.prepare(`INSERT INTO prospects
    (business_name, contact_name, profession, region, email, phone, emails_json, phones_json, offer_fit, fit_score, fit_reasons_json, website, address, source_url, source_title, source_snippet, collected_at, confidence, notes, priority, deal_value, next_action, next_action_at, last_contact_at, tags_json, sources_json, account_type, contact_role, lead_source, owner_name, probability, expected_close_date, lost_reason, created_at, updated_at)
    VALUES (@businessName, @contactName, @profession, @region, @email, @phone, @emailsJson, @phonesJson, @offerFit, @fitScore, @fitReasonsJson, @website, @address, @sourceUrl, @sourceTitle, @sourceSnippet, @collectedAt, @confidence, @notes, @priority, @dealValue, @nextAction, @nextActionAt, @lastContactAt, @tagsJson, @sourcesJson, @accountType, @contactRole, @leadSource, @ownerName, @probability, @expectedCloseDate, @lostReason, @createdAt, @updatedAt)`)
    .run({ ...prospect, emailsJson: JSON.stringify(prospect.emails), phonesJson: JSON.stringify(prospect.phones), offerFit: prospect.offerFit ? 1 : 0, fitScore: prospect.fitScore, fitReasonsJson: JSON.stringify(prospect.fitReasons), tagsJson: JSON.stringify(prospect.tags), sourcesJson: JSON.stringify(prospect.sources), createdAt: timestamp, updatedAt: timestamp });
  res.status(201).json({ prospect: rowToProspect(findById.get(result.lastInsertRowid)), created: true });
});

app.patch("/api/prospects/:id", (req, res) => {
  const id = Number(req.params.id);
  const existing = findById.get(id);
  if (!existing) return res.status(404).json({ error: "Prospect introuvable." });
  const stage = clean(req.body.stage, 30);
  if (stage && !STAGES.includes(stage)) return res.status(400).json({ error: "Étape de pipeline invalide." });
  const updates = [];
  const params = { id, updatedAt: now() };
  if (Object.prototype.hasOwnProperty.call(req.body, "stage")) { updates.push("stage = @stage"); params.stage = stage || existing.stage; }
  if (Object.prototype.hasOwnProperty.call(req.body, "notes")) { updates.push("notes = @notes"); params.notes = clean(req.body.notes, 3000); }
  if (Object.prototype.hasOwnProperty.call(req.body, "optOut")) { updates.push("opt_out = @optOut"); params.optOut = req.body.optOut ? 1 : 0; }
  if (Object.prototype.hasOwnProperty.call(req.body, "priority")) {
    const priority = clean(req.body.priority, 20);
    if (!PRIORITIES.includes(priority)) return res.status(400).json({ error: "Priorité invalide." });
    updates.push("priority = @priority"); params.priority = priority;
  }
  if (Object.prototype.hasOwnProperty.call(req.body, "dealValue")) { updates.push("deal_value = @dealValue"); params.dealValue = Math.max(0, Number(req.body.dealValue) || 0); }
  if (Object.prototype.hasOwnProperty.call(req.body, "nextAction")) { updates.push("next_action = @nextAction"); params.nextAction = clean(req.body.nextAction, 500); }
  if (Object.prototype.hasOwnProperty.call(req.body, "nextActionAt")) { updates.push("next_action_at = @nextActionAt"); params.nextActionAt = clean(req.body.nextActionAt, 40); }
  if (Object.prototype.hasOwnProperty.call(req.body, "lastContactAt")) { updates.push("last_contact_at = @lastContactAt"); params.lastContactAt = clean(req.body.lastContactAt, 40); }
  if (Object.prototype.hasOwnProperty.call(req.body, "tags")) { updates.push("tags_json = @tagsJson"); params.tagsJson = JSON.stringify(Array.isArray(req.body.tags) ? unique(req.body.tags.map((value) => clean(value, 40))).slice(0, 12) : []); }
  if (Object.prototype.hasOwnProperty.call(req.body, "accountType")) { updates.push("account_type = @accountType"); params.accountType = clean(req.body.accountType, 80); }
  if (Object.prototype.hasOwnProperty.call(req.body, "contactRole")) { updates.push("contact_role = @contactRole"); params.contactRole = clean(req.body.contactRole, 120); }
  if (Object.prototype.hasOwnProperty.call(req.body, "leadSource")) { updates.push("lead_source = @leadSource"); params.leadSource = clean(req.body.leadSource, 120); }
  if (Object.prototype.hasOwnProperty.call(req.body, "ownerName")) { updates.push("owner_name = @ownerName"); params.ownerName = clean(req.body.ownerName, 120); }
  if (Object.prototype.hasOwnProperty.call(req.body, "probability")) { updates.push("probability = @probability"); params.probability = Math.min(100, Math.max(0, Number(req.body.probability) || 0)); }
  if (Object.prototype.hasOwnProperty.call(req.body, "expectedCloseDate")) { updates.push("expected_close_date = @expectedCloseDate"); params.expectedCloseDate = clean(req.body.expectedCloseDate, 40); }
  if (Object.prototype.hasOwnProperty.call(req.body, "lostReason")) { updates.push("lost_reason = @lostReason"); params.lostReason = clean(req.body.lostReason, 300); }
  if (updates.length) db.prepare(`UPDATE prospects SET ${updates.join(", ")}, updated_at = @updatedAt WHERE id = @id`).run(params);
  if (stage && stage !== existing.stage) {
    db.prepare("INSERT INTO activities (prospect_id, type, content, created_at) VALUES (?, ?, ?, ?)")
      .run(id, "stage_change", `Étape changée de ${existing.stage} à ${stage}`, now());
  }
  res.json({ prospect: rowToProspect(findById.get(id)) });
});

app.post("/api/prospects/:id/activities", (req, res) => {
  const id = Number(req.params.id);
  if (!findById.get(id)) return res.status(404).json({ error: "Prospect introuvable." });
  const type = clean(req.body.type, 30) || "note";
  const content = clean(req.body.content, 3000);
  if (!ACTIVITY_TYPES.includes(type)) return res.status(400).json({ error: "Type d’activité invalide." });
  if (!content) return res.status(400).json({ error: "Le contenu de l’activité est requis." });
  const createdAt = now();
  const result = db.prepare("INSERT INTO activities (prospect_id, type, content, created_at) VALUES (?, ?, ?, ?)")
    .run(id, type, content, createdAt);
  if (["call", "email", "meeting"].includes(type)) {
    db.prepare("UPDATE prospects SET last_contact_at = ?, updated_at = ? WHERE id = ?").run(createdAt, createdAt, id);
  } else {
    db.prepare("UPDATE prospects SET updated_at = ? WHERE id = ?").run(createdAt, id);
  }
  res.status(201).json({ activity: db.prepare("SELECT * FROM activities WHERE id = ?").get(result.lastInsertRowid), prospect: rowToProspect(findById.get(id)) });
});

app.post("/api/prospects/:id/gmail-draft", async (req, res) => {
  try {
    if (!gmailIsAuthorized()) return res.status(503).json({ error: "Gmail n’est pas encore autorisé. Configurez les identifiants OAuth puis ouvrez /auth/gmail." });
    const id = Number(req.params.id);
    const prospect = rowToProspect(findById.get(id));
    if (!prospect) return res.status(404).json({ error: "Prospect introuvable." });
    if (!prospect.email) return res.status(400).json({ error: "Ce prospect n’a pas d’adresse email." });
    if (prospect.optOut || prospect.stage === "excluded") return res.status(400).json({ error: "Ce prospect est exclu des contacts commerciaux." });
    const draftResponse = await fetch(`http://127.0.0.1:${PORT}/api/prospects/${id}/email`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ senderName: req.body.senderName, offer: req.body.offer })
    });
    const draft = await draftResponse.json();
    if (!draftResponse.ok) return res.status(draftResponse.status).json(draft);
    const gmail = google.gmail({ version: "v1", auth: authorizedGmailClient() });
    const created = await gmail.users.drafts.create({ userId: "me", requestBody: { message: { raw: buildGmailRawMessage({ to: prospect.email, subject: draft.subject, body: draft.body, html: draft.html }) } } });
    db.prepare("INSERT INTO activities (prospect_id, type, content, created_at) VALUES (?, ?, ?, ?)")
      .run(id, "gmail_draft", `Brouillon Gmail créé pour ${prospect.email} : ${draft.subject}`, now());
    res.status(201).json({ draftId: created.data.id, messageId: created.data.message?.id || "", to: prospect.email, subject: draft.subject, account: gmailConfig().account });
  } catch (error) {
    res.status(502).json({ error: `Création du brouillon Gmail impossible : ${error.message}` });
  }
});

app.post("/api/prospects/:id/email", (req, res) => {
  const id = Number(req.params.id);
  const prospect = rowToProspect(findById.get(id));
  if (!prospect) return res.status(404).json({ error: "Prospect introuvable." });
  if (prospect.optOut || prospect.stage === "excluded") return res.status(400).json({ error: "Ce prospect est exclu des contacts commerciaux." });
  const sender = clean(req.body.senderName, 100) || "Jean Marc";
  const offer = clean(req.body.offer, 500) || "l’automatisation de tâches répétitives pour les TPE et PME";
  const location = [prospect.profession, prospect.region].filter(Boolean).join(" à ");
  const profession = prospect.profession.toLowerCase();
  const professionWithArticle = profession ? `${/^[aeiouyàâäéèêëîïôöùûüœ]/i.test(profession) ? "d’" : "de "}${profession}` : "";
  const subject = `Une idée pour simplifier votre activité${professionWithArticle ? ` ${professionWithArticle}` : ""}`;
  const sourceUrl = prospect.source.url || prospect.website || "";
  let sourceLabel = sourceUrl;
  try { sourceLabel = new URL(sourceUrl).hostname; } catch {}
  const body = `Bonjour,\n\nJe me permets de vous contacter pour vous faire gagner du temps et de l’argent.${location ? ` Votre entreprise est présentée comme active dans le domaine ${location}.` : ""}\n\n${sender} aide les TPE et PME à étudier ${offer}, à partir d’une tâche concrète et avec une validation humaine à chaque étape.\n\nDans une entreprise comme la vôtre, le temps se perd souvent entre les demandes clients, les devis, le planning, les relances et le suivi des documents. Nous ne savons pas lequel de ces sujets est prioritaire pour vous : c’est précisément ce que nous proposons de vérifier.\n\nQuel sujet vous ferait gagner le plus de temps ?\n1. Répondre aux demandes et préparer les devis\n2. Organiser le planning et les interventions\n3. Relancer et suivre les clients\n4. Rechercher de nouveaux clients\n\nRépondez simplement avec 1, 2, 3 ou 4. Je vous enverrai un exemple adapté à votre activité, ou deux créneaux pour un échange de 15 minutes.\n\nDécouvrir FÉWURA SYSTEMS : https://innovatechsoftware.eu\n\nBien cordialement,\n${sender}\n\nSource de la coordonnée : ${sourceLabel || "page professionnelle publique"}.\nSi vous ne souhaitez plus recevoir de message de prospection de notre part, répondez simplement « stop » et nous ne vous recontacterons plus.`;
  const safe = {
    businessName: escapeEmailHtml(prospect.businessName),
    location: escapeEmailHtml(location),
    sender: escapeEmailHtml(sender),
    offer: escapeEmailHtml(offer),
    source: escapeEmailHtml(sourceLabel || "page professionnelle publique")
  };
  const html = `<!doctype html><html lang="fr"><body style="margin:0;background:#f5f6f1;font-family:Arial,Helvetica,sans-serif;color:#152522;"><div style="max-width:620px;margin:0 auto;padding:28px 16px;"><div style="background:#ffffff;border:1px solid #dfe6df;border-radius:16px;overflow:hidden;"><div style="padding:22px 24px;border-bottom:1px solid #e6ece5;"><table role="presentation" cellpadding="0" cellspacing="0"><tr><td style="width:42px;height:42px;background:#152522;border-radius:11px;text-align:center;vertical-align:middle;color:#bbff6a;font-size:25px;font-weight:700;">F</td><td style="padding-left:12px;vertical-align:middle;"><strong style="font-size:17px;letter-spacing:.05em;">FÉWURA</strong><br><span style="font-size:9px;letter-spacing:.12em;color:#718078;">SYSTÈMES AUTOMATISÉS POUR TPE &amp; PME</span></td></tr></table></div><div style="padding:28px 24px;"><p style="margin:0 0 18px;">Bonjour,</p><p style="margin:0 0 16px;">Je me permets de vous contacter pour vous faire gagner du temps et de l’argent.${safe.location ? ` Votre entreprise est présentée comme active dans le domaine ${safe.location}` : ""}.</p><p style="margin:0 0 16px;"><strong>${safe.sender}</strong> aide les TPE et PME à étudier ${safe.offer}, à partir d’une tâche concrète et avec une validation humaine à chaque étape.</p><p style="margin:0 0 12px;">Quel sujet vous ferait gagner le plus de temps&nbsp;?</p><div style="padding:16px 18px;background:#f3f9e9;border-left:4px solid #bbff6a;border-radius:8px;line-height:1.8;"><strong>1.</strong> Répondre aux demandes et préparer les devis<br><strong>2.</strong> Organiser le planning et les interventions<br><strong>3.</strong> Relancer et suivre les clients<br><strong>4.</strong> Rechercher de nouveaux clients</div><p style="margin:20px 0;">Répondez simplement avec <strong>1, 2, 3 ou 4</strong>. Je vous enverrai un exemple adapté à votre activité, ou deux créneaux pour un échange de 15 minutes.</p><p style="margin:22px 0;"><a href="https://innovatechsoftware.eu" style="display:inline-block;background:#152522;color:#bbff6a;text-decoration:none;padding:12px 18px;border-radius:8px;font-weight:700;">Découvrir FÉWURA SYSTEMS →</a></p><p style="margin:0;">Bien cordialement,<br><strong>${safe.sender}</strong></p></div><div style="padding:16px 24px;background:#fafbf8;color:#718078;font-size:11px;line-height:1.6;">Source de la coordonnée : ${safe.source}.<br>Si vous ne souhaitez plus recevoir de message de prospection de notre part, répondez simplement « stop ».</div></div></div></body></html>`;
  const logoCell = '<td style="width:62px;height:62px;vertical-align:middle;"><img src="https://innovatechsoftware.eu/fewura-logo.png" width="62" height="62" alt="FÉWURA SYSTEMS" style="display:block;width:62px;height:62px;border:0;border-radius:12px;"></td>';
  const htmlWithLogo = html.replace('<td style="width:42px;height:42px;background:#152522;border-radius:11px;text-align:center;vertical-align:middle;color:#bbff6a;font-size:25px;font-weight:700;">F</td>', logoCell);
  db.prepare("INSERT INTO activities (prospect_id, type, content, created_at) VALUES (?, ?, ?, ?)")
    .run(id, "email_draft", `Brouillon créé : ${subject}`, now());
  res.json({ subject, body, html: htmlWithLogo, disclaimer: "Brouillon commercial généré à partir des informations publiques enregistrées. Vérifiez les faits, la source et les règles applicables avant tout envoi." });
});

async function sendProspectEmail(id, options = {}) {
  if (!gmailIsAuthorized()) throw new Error("Gmail n’est pas encore autorisé. Configurez les identifiants OAuth puis ouvrez /auth/gmail.");
  const prospect = rowToProspect(findById.get(Number(id)));
  if (!prospect) throw new Error("Prospect introuvable.");
  if (!prospect.email) throw new Error("Ce prospect n’a pas d’adresse email.");
  if (prospect.optOut || prospect.stage === "excluded") throw new Error("Ce prospect est exclu des contacts commerciaux.");
  const draftResponse = await fetch(`http://127.0.0.1:${PORT}/api/prospects/${prospect.id}/email`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(options)
  });
  const draft = await draftResponse.json();
  if (!draftResponse.ok) throw new Error(draft.error || "Message impossible à préparer.");
  const gmail = google.gmail({ version: "v1", auth: authorizedGmailClient() });
  const sent = await gmail.users.messages.send({ userId: "me", requestBody: { raw: buildGmailRawMessage({ to: prospect.email, subject: draft.subject, body: draft.body, html: draft.html }) } });
  db.prepare("INSERT INTO activities (prospect_id, type, content, created_at) VALUES (?, ?, ?, ?)")
    .run(prospect.id, "email", `E-mail envoyé à ${prospect.email} : ${draft.subject}`, now());
  return { id: prospect.id, businessName: prospect.businessName, to: prospect.email, subject: draft.subject, messageId: sent.data.id || "" };
}

app.post("/api/prospects/:id/send-email", async (req, res) => {
  try {
    res.status(200).json(await sendProspectEmail(req.params.id, { senderName: req.body.senderName, offer: req.body.offer }));
  } catch (error) {
    res.status(502).json({ error: `Envoi impossible : ${error.message}` });
  }
});

app.post("/api/prospects/bulk-send-email", async (req, res) => {
  const ids = [...new Set((Array.isArray(req.body.ids) ? req.body.ids : []).map(Number).filter(Number.isInteger))].slice(0, 500);
  if (!ids.length) return res.status(400).json({ error: "Aucun prospect sélectionné." });
  const results = [];
  for (const id of ids) {
    try {
      results.push({ ok: true, ...(await sendProspectEmail(id, { senderName: req.body.senderName, offer: req.body.offer })) });
    } catch (error) {
      results.push({ ok: false, id, error: error.message });
    }
  }
  res.json({ sent: results.filter((item) => item.ok).length, total: results.length, results });
});

app.get("*", (_req, res) => res.sendFile(path.join(__dirname, "public", "index.html")));

app.listen(PORT, () => console.log(`CRM disponible sur http://localhost:${PORT}`));
