// Component 4 API client (maturity classification + spray prescription).
// The backend runs from component4_maturity_engine/:  uvicorn api.server:app --port 8000
// In dev, Vite proxies /api to port 8000 (vite.config.js). Override with VITE_C4_API_URL if needed.

export const C4_API = (import.meta.env.VITE_C4_API_URL || "").replace(/\/$/, "");

async function request(path, options = {}) {
  let res;
  try {
    res = await fetch(`${C4_API}${path}`, options);
  } catch {
    throw new Error(
      `Cannot reach the Component 4 API${C4_API ? " at " + C4_API : ""}. Start it with: uvicorn api.server:app --port 8000`
    );
  }
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const d = body.detail;
    const msg = typeof d === "string" ? d : d?.message || `Request failed (${res.status})`;
    const err = new Error(msg);
    err.detail = d;
    throw err;
  }
  return body;
}

export const getHealth = () => request("/api/health");
export const getConfig = () => request("/api/config");
export const saveConfig = (cfg) =>
  request("/api/config", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cfg),
  });
export const listMissions = () => request("/api/missions");
export const getMission = (id) => request(`/api/missions/${encodeURIComponent(id)}`);
export const getMetrics = () => request("/api/metrics");
export const imageUrl = (missionId, regionId) =>
  `${C4_API}/api/missions/${encodeURIComponent(missionId)}/images/${regionId}`;

export function createPrescription(files, field) {
  const form = new FormData();
  [...files].forEach((f) => form.append("files", f));
  form.append("field", field);
  return request("/api/prescriptions", { method: "POST", body: form });
}

// Shared display constants (colours match the original prototype)
export const LEVELS = {
  low: { label: "Low", short: "L", color: "#4ADE80" },
  normal: { label: "Normal", short: "N", color: "#FBBF24" },
  high: { label: "High", short: "H", color: "#F87171" },
};
export const MATURITY_LABEL = { young: "Young", medium: "Medium", mature: "Mature" };

export function downloadFile(name, text, type) {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = Object.assign(document.createElement("a"), { href: url, download: name });
  a.click();
  URL.revokeObjectURL(url);
}

export function prescriptionCsv(p) {
  const cols = ["region_id", "image", "lat", "lon", "maturity", "confidence",
    "spray_level", "rate_multiplier", "flow_l_min", "needs_review", "reason"];
  const esc = (v) => (v == null ? "" : /[",\n]/.test(String(v)) ? `"${String(v).replace(/"/g, '""')}"` : v);
  return [cols.join(","), ...p.regions.map((r) => cols.map((c) => esc(r[c])).join(","))].join("\n");
}
