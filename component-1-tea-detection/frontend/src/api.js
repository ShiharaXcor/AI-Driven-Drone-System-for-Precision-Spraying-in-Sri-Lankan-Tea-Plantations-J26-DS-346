const BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const TOKEN_KEY = "teadrone-token";

export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (t) =>
  t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY);

export const fileUrl = (path) => (path ? BASE + path : "");
export const wsUrl = () => BASE.replace(/^http/, "ws") + "/ws/live";
export const downloadUrl = (name) => `${BASE}/api/export/${name}`;

async function request(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let res;
  try {
    res = await fetch(BASE + path, { ...options, headers });
  } catch {
    throw new Error(`Cannot reach the backend at ${BASE}. Is it running?`);
  }

  // Expired or invalid login: clear it and go back to the login page
  if (res.status === 401 && token && path !== "/api/auth/login") {
    setToken(null);
    window.location.assign("/login");
  }

  if (!res.ok) {
    let message = res.statusText;
    try {
      const body = await res.json();
      message = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* keep statusText */
    }
    const err = new Error(message);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

const send = (method, body) => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  login: (username, password) => request("/api/auth/login", send("POST", { username, password })),

  infer: (file, geofenceOk = true) => {
    const form = new FormData();
    form.append("file", file);
    return request(`/api/infer?geofence_ok=${geofenceOk}`, { method: "POST", body: form });
  },

  status: () => request("/api/status"),
  models: () => request("/api/models"),
  gps: () => request("/api/gps"),

  events: (limit = 50) => request(`/api/events?limit=${limit}`),
  event: (id) => request(`/api/events/${id}`),
  detections: (limit = 1000) => request(`/api/detections?limit=${limit}`),

  alerts: (limit = 200) => request(`/api/alerts?limit=${limit}`),
  ack: (id) => request(`/api/alerts/${id}/ack`, { method: "POST" }),

  settings: () => request("/api/settings"),
  saveSettings: (values) => request("/api/settings", send("PUT", values)),

  emergency: (on) => request(`/api/emergency/${on}`, { method: "POST" }),
  manual: (mode) => request(`/api/manual/${mode}`, { method: "POST" }),
};