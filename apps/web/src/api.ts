const TOKEN = "docflow.token";
const REFRESH = "docflow.refresh";

export const apiBase = "";

export function getToken() {
  return localStorage.getItem(TOKEN) || "";
}

export function setTokens(access: string, refresh?: string) {
  localStorage.setItem(TOKEN, access);
  if (refresh) localStorage.setItem(REFRESH, refresh);
}

export function clearTokens() {
  localStorage.removeItem(TOKEN);
  localStorage.removeItem(REFRESH);
}

export async function api<T = any>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (!(init.body instanceof FormData) && !headers.has("Content-Type") && init.body) {
    headers.set("Content-Type", "application/json");
  }
  const res = await fetch(`${apiBase}${path}`, { ...init, headers });
  if (res.status === 401) {
    clearTokens();
    if (!path.includes("/auth/login")) window.location.href = "/login";
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const j = await res.json();
      detail = j.detail || JSON.stringify(j);
    } catch {
      /* empty */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const AuthAPI = {
  login: (email: string, password: string) =>
    api("/api/v1/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  register: (payload: object) =>
    api("/api/v1/auth/register", { method: "POST", body: JSON.stringify(payload) }),
  me: () => api("/api/v1/auth/me"),
};

export const DocsAPI = {
  list: () => api("/api/v1/documents"),
  detail: (id: number) => api(`/api/v1/documents/${id}/detail`),
  upload: (file: File, run = true) => {
    const fd = new FormData();
    fd.append("file", file);
    return api(`/api/v1/documents/upload?run_pipeline=${run}`, { method: "POST", body: fd });
  },
  download: (id: number) => `${apiBase}/api/v1/documents/${id}/download`,
};

export const WfAPI = {
  list: () => api("/api/v1/workflows"),
  create: (body: object) => api("/api/v1/workflows", { method: "POST", body: JSON.stringify(body) }),
  execute: (id: number, documentId: number) =>
    api(`/api/v1/workflows/${id}/execute?document_id=${documentId}`, { method: "POST" }),
  runs: () => api("/api/v1/workflows/runs/recent"),
  n8n: (id: number) => api(`/api/v1/workflows/${id}/n8n`),
};

export const AutoAPI = {
  list: () => api("/api/v1/automations"),
  create: (body: object) => api("/api/v1/automations", { method: "POST", body: JSON.stringify(body) }),
  toggle: (id: number) => api(`/api/v1/automations/${id}/toggle`, { method: "POST" }),
};

export const AgentAPI = {
  status: () => api("/api/v1/agent/status"),
  logs: () => api("/api/v1/agent/logs"),
  skills: () => api("/api/v1/agent/skills"),
  runSkill: (id: string, prompt: string) =>
    api(`/api/v1/agent/skills/${id}/run?prompt=${encodeURIComponent(prompt)}`, { method: "POST" }),
  process: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return api("/api/v1/agent/process-document", { method: "POST", body: fd });
  },
  ollama: () => api("/api/v1/agent/ollama"),
  useOllama: (model = "") => api(`/api/v1/agent/ollama/use?model=${encodeURIComponent(model)}`, { method: "POST" }),
};

export const AnalyticsAPI = {
  summary: () => api("/api/v1/analytics/summary"),
  activity: () => api("/api/v1/analytics/activity"),
  notes: () => api("/api/v1/analytics/notifications"),
  read: (id: number) => api(`/api/v1/analytics/notifications/${id}/read`, { method: "POST" }),
};

export const OrgAPI = {
  tree: () => api("/api/v1/org/tree"),
  layer: (body: object) => api("/api/v1/org/layers", { method: "POST", body: JSON.stringify(body) }),
  member: (layerId: number, body: object) =>
    api(`/api/v1/org/layers/${layerId}/members`, { method: "POST", body: JSON.stringify(body) }),
  folder: (body: object) => api("/api/v1/org/folders", { method: "POST", body: JSON.stringify(body) }),
  grant: (body: object) => api("/api/v1/org/grants", { method: "POST", body: JSON.stringify(body) }),
};

export const FormsAPI = {
  list: () => api("/api/v1/forms"),
  get: (id: number) => api(`/api/v1/forms/${id}`),
  create: (body: object) => api("/api/v1/forms", { method: "POST", body: JSON.stringify(body) }),
  update: (id: number, body: object) => api(`/api/v1/forms/${id}`, { method: "PUT", body: JSON.stringify(body) }),
  remove: (id: number) => api(`/api/v1/forms/${id}`, { method: "DELETE" }),
  copy: (id: number) => api(`/api/v1/forms/${id}/copy`, { method: "POST" }),
  archive: (id: number, keep_answers: boolean) =>
    api(`/api/v1/forms/${id}/archive`, { method: "POST", body: JSON.stringify({ keep_answers }) }),
  unarchive: (id: number) => api(`/api/v1/forms/${id}/unarchive`, { method: "POST" }),
  compose: (body: object) => api("/api/v1/forms/compose", { method: "POST", body: JSON.stringify(body) }),
  publish: (id: number) => api(`/api/v1/forms/${id}/publish`, { method: "POST" }),
  setAnonymousReplies: (id: number, enabled: boolean) =>
    api(`/api/v1/forms/${id}/anonymous-replies`, {
      method: "PATCH",
      body: JSON.stringify({ enabled }),
    }),
  share: (id: number, body: object) => api(`/api/v1/forms/${id}/share`, { method: "POST", body: JSON.stringify(body) }),
  submissions: (id: number) => api(`/api/v1/forms/${id}/submissions`),
  answered: (id: number) => api(`/api/v1/forms/${id}/answered`),
  digest: (formId: number, submissionId: number, body: object) =>
    api(`/api/v1/forms/${formId}/submissions/${submissionId}/digest`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  ingest: (formId: number, submissionId: number, body: object = {}) =>
    api(`/api/v1/forms/${formId}/submissions/${submissionId}/ingest`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  publicGet: (token: string, email?: string) => {
    const q = email ? `?email=${encodeURIComponent(email)}` : "";
    return api(`/api/v1/public/forms/${token}${q}`);
  },
  publicSubmit: (
    token: string,
    body: { name?: string; email?: string; answers?: Record<string, unknown>; signature?: string | null; locale?: string },
    uploads?: Record<string, File[]>
  ) => {
    const files = uploads || {};
    const hasUploads = Object.values(files).some((list) => Array.isArray(list) && list.length > 0);
    if (!hasUploads) {
      return api(`/api/v1/public/forms/${token}/submit`, { method: "POST", body: JSON.stringify(body) });
    }
    const fd = new FormData();
    fd.append("name", body.name || "");
    fd.append("email", body.email || "");
    fd.append("answers", JSON.stringify(body.answers || {}));
    if (body.signature) fd.append("signature", body.signature);
    fd.append("locale", body.locale || "en");
    for (const [fieldId, list] of Object.entries(files)) {
      for (const file of list || []) {
        fd.append(`file__${fieldId}`, file);
      }
    }
    return api(`/api/v1/public/forms/${token}/submit`, { method: "POST", body: fd });
  },
};

export const ConnectAPI = {
  list: () => api("/api/v1/connectors"),
  add: (body: object) => api("/api/v1/connectors", { method: "POST", body: JSON.stringify(body) }),
  browse: (id: number, path = "") =>
    api(`/api/v1/connectors/${id}/browse?path=${encodeURIComponent(path)}`),
  sync: (id: number, paths?: string[]) =>
    api(`/api/v1/connectors/${id}/sync`, {
      method: "POST",
      body: JSON.stringify(paths ? { paths } : {}),
    }),
};

export const SearchAPI = {
  query: (q: string) => api(`/api/v1/search?q=${encodeURIComponent(q)}`),
};

export const AdminAPI = {
  stats: () => api("/api/v1/admin/stats"),
  users: () => api("/api/v1/admin/users"),
  createUser: (body: object) => api("/api/v1/admin/users", { method: "POST", body: JSON.stringify(body) }),
  block: (id: number) => api(`/api/v1/admin/users/${id}/block`, { method: "POST" }),
  tenants: () => api("/api/v1/admin/tenants"),
  flags: () => api("/api/v1/admin/flags"),
  toggleFlag: (key: string) => api(`/api/v1/admin/flags/${encodeURIComponent(key)}/toggle`, { method: "POST" }),
  models: () => api("/api/v1/admin/models"),
  health: () => api("/api/v1/admin/health"),
  ragSources: () => api("/api/v1/admin/rag/sources"),
  ragToggleSource: (id: number) => api(`/api/v1/admin/rag/sources/${id}/toggle`, { method: "POST" }),
  ragChunks: (params?: { q?: string; tag?: string; source_type?: string }) => {
    const sp = new URLSearchParams();
    if (params?.q) sp.set("q", params.q);
    if (params?.tag) sp.set("tag", params.tag);
    if (params?.source_type) sp.set("source_type", params.source_type);
    const qs = sp.toString();
    return api(`/api/v1/admin/rag/chunks${qs ? `?${qs}` : ""}`);
  },
  ragPatchTags: (id: number, tags: string[]) =>
    api(`/api/v1/admin/rag/chunks/${id}/tags`, { method: "PATCH", body: JSON.stringify({ tags }) }),
  ragSettings: () => api("/api/v1/admin/rag/settings"),
};
