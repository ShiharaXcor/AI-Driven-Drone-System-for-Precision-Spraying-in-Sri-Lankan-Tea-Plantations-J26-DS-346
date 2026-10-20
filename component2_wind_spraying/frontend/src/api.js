// All calls to the Component 2 backend (FastAPI) live here.
// Change API_URL if the backend runs somewhere else.
export const API_URL = "http://localhost:8000";

async function call(path, options = {}) {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : `HTTP ${res.status}`);
  }
  return res.json();
}

export const getRecommendation = (inputs) =>
  call("/recommend", { method: "POST", body: JSON.stringify(inputs) });

export const getDriftCurve = (inputs) =>
  call("/drift-curve", { method: "POST", body: JSON.stringify(inputs) });

export const getWeather = (region) => call(`/weather/${encodeURIComponent(region)}`);

export const simulateMission = (inputs) =>
  call("/mission/simulate", { method: "POST", body: JSON.stringify(inputs) });
