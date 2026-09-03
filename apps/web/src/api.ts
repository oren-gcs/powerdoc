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
};

export const AnalyticsAPI = {
  summary: () => api("/api/v1/analytics/summary"),
  activity: () => api("/api/v1/analytics/activity"),
  notes: () => api("/api/v1/analytics/notifications"),
  read: (id: number) => api(`/api/v1/analytics/notifications/${id}/read`, { method: "POST" }),
};

export const AdminAPI = {
  stats: () => api("/api/v1/admin/stats"),
  users: () => api("/api/v1/admin/users"),
  createUser: (body: object) => api("/api/v1/admin/users", { method: "POST", body: JSON.stringify(body) }),
  block: (id: number) => api(`/api/v1/admin/users/${id}/block`, { method: "POST" }),
  tenants: () => api("/api/v1/admin/tenants"),
  flags: () => api("/api/v1/admin/flags"),
  models: () => api("/api/v1/admin/models"),
  health: () => api("/api/v1/admin/health"),
};
