// The backend sends UTC times without a "Z". Add it, then show local time.
export const toDate = (s) => new Date(/[zZ]|[+-]\d\d:\d\d$/.test(s) ? s : s + "Z");
const pad = (n) => String(n).padStart(2, "0");
export const fmtDate = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
export const fmtClock = (d) => `${pad(d.getHours())}:${pad(d.getMinutes())}`;

export function alertType(message = "") {
  const m = message.toLowerCase();
  if (m.includes("person")) return "Person detected";
  if (m.includes("animal")) return "Animal detected";
  if (m.includes("emergency")) return "Emergency stop";
  if (m.includes("camera") || m.includes("pipeline")) return "Camera failure";
  return "System event";
}

const SEVERITIES = ["critical", "warning", "info"];

// Turns a backend alert row into the shape the Alerts and Home pages use
export function normalizeAlert(a) {
  const d = toDate(a.ts);
  return {
    id: a.id,
    date: fmtDate(d),
    time: fmtClock(d),
    type: alertType(a.message),
    severity: SEVERITIES.includes(a.priority) ? a.priority : "info",
    message: a.message,
    lat: a.lat == null ? "-" : Number(a.lat).toFixed(6),
    lng: a.lon == null ? "-" : Number(a.lon).toFixed(6),
    acknowledged: !!a.acked,
  };
}