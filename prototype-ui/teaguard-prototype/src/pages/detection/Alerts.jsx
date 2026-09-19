import { useState, useMemo } from "react";
import { useTheme } from "../../context/ThemeContext";

const SEVERITIES = ["critical", "warning", "info"];
const ALERT_TYPES = ["Person detected", "Animal detected", "Low battery", "Low confidence", "Camera failure", "Sync complete"];

const SEVERITY_META = {
  critical: {
    dark: "bg-red-500/10 border-red-500/40 text-red-400",
    light: "bg-red-50 border-red-200 text-red-600",
    dot: "#ef4444",
    label: "Critical",
  },
  warning: {
    dark: "bg-amber-500/10 border-amber-500/40 text-amber-400",
    light: "bg-amber-50 border-amber-200 text-amber-600",
    dot: "#f59e0b",
    label: "Warning",
  },
  info: {
    dark: "bg-blue-500/10 border-blue-500/40 text-blue-400",
    light: "bg-blue-50 border-blue-200 text-blue-600",
    dot: "#3b82f6",
    label: "Info",
  },
};

function generateAlerts(count) {
  const alerts = [];
  for (let i = 1; i <= count; i++) {
    const type = ALERT_TYPES[Math.floor(Math.random() * ALERT_TYPES.length)];
    const severity =
      type === "Person detected" || type === "Animal detected"
        ? "critical"
        : type === "Low battery" || type === "Low confidence"
        ? "warning"
        : type === "Camera failure"
        ? "critical"
        : "info";
    const hour = String(8 + Math.floor(Math.random() * 9)).padStart(2, "0");
    const min = String(Math.floor(Math.random() * 60)).padStart(2, "0");
    alerts.push({
      id: `ALT-${String(500 + i)}`,
      time: `${hour}:${min}`,
      date: `2026-08-${String(20 + (i % 8)).padStart(2, "0")}`,
      type,
      severity,
      message: messageFor(type),
      lat: (7.2906 + Math.random() * 0.01).toFixed(6),
      lng: (80.6337 + Math.random() * 0.01).toFixed(6),
      acknowledged: i > 6, // first few stay active, rest are history
    });
  }
  return alerts.sort((a, b) => (a.date + a.time < b.date + b.time ? 1 : -1));
}

function messageFor(type) {
  switch (type) {
    case "Person detected":
      return "Person detected in frame, spray halted immediately";
    case "Animal detected":
      return "Animal detected, pump held, position maintained";
    case "Low battery":
      return "Battery dropped below 30%, plan return to base";
    case "Low confidence":
      return "Detection confidence below threshold for 3 consecutive frames";
    case "Camera failure":
      return "Camera feed interrupted, fallback to last known frame";
    case "Sync complete":
      return "Detection log synced to server successfully";
    default:
      return "System event logged";
  }
}

export default function Alerts() {
  const { isDark } = useTheme();
  const [allAlerts, setAllAlerts] = useState(() => generateAlerts(24));
  const [severityFilter, setSeverityFilter] = useState("all");
  const [search, setSearch] = useState("");

  const cardBg = isDark ? "bg-surface" : "bg-light-surface";
  const border = isDark ? "border-border" : "border-light-border";
  const textMuted = isDark ? "text-muted" : "text-light-muted";
  const textPrimary = isDark ? "text-white" : "text-light-text";
  const inner = isDark ? "bg-ink" : "bg-light-bg";
  const accentBg = isDark ? "bg-accent" : "bg-light-primary";
  const accentTextOn = isDark ? "text-ink" : "text-white";

  const active = useMemo(() => allAlerts.filter((a) => !a.acknowledged), [allAlerts]);
  const history = useMemo(() => allAlerts.filter((a) => a.acknowledged), [allAlerts]);

  const filteredActive = useMemo(() => {
    return active.filter((a) => {
      if (severityFilter !== "all" && a.severity !== severityFilter) return false;
      if (search.trim() && !a.type.toLowerCase().includes(search.toLowerCase()) && !a.message.toLowerCase().includes(search.toLowerCase())) return false;
      return true;
    });
  }, [active, severityFilter, search]);

  const stats = useMemo(() => {
    return {
      total: allAlerts.length,
      active: active.length,
      critical: allAlerts.filter((a) => a.severity === "critical" && !a.acknowledged).length,
      acknowledged: history.length,
    };
  }, [allAlerts, active, history]);

  function acknowledge(id) {
    setAllAlerts((prev) => prev.map((a) => (a.id === id ? { ...a, acknowledged: true } : a)));
  }

  function acknowledgeAll() {
    setAllAlerts((prev) => prev.map((a) => (filteredActive.some((f) => f.id === a.id) ? { ...a, acknowledged: true } : a)));
  }

  return (
    <div className="flex flex-col lg:flex-row gap-4">
      {/* Filters sidebar */}
      <div className={`lg:w-56 flex-shrink-0 ${cardBg} border ${border} rounded-2xl p-4 h-fit`}>
        <p className={`text-xs font-semibold ${textPrimary} mb-3`}>Filters</p>

        <p className={`text-[10px] ${textMuted} mb-1`}>Search</p>
        <input
          type="text"
          placeholder="Alert type or message..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className={`w-full text-xs ${inner} border ${border} rounded-lg px-2 py-1.5 ${textPrimary} mb-3`}
        />

        <p className={`text-[10px] ${textMuted} mb-2`}>Severity</p>
        <div className="flex flex-col gap-1.5 mb-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="radio" checked={severityFilter === "all"} onChange={() => setSeverityFilter("all")} />
            <span className={`text-xs ${textPrimary}`}>All severities</span>
          </label>
          {SEVERITIES.map((s) => (
            <label key={s} className="flex items-center gap-2 cursor-pointer">
              <input type="radio" checked={severityFilter === s} onChange={() => setSeverityFilter(s)} />
              <span className="w-2 h-2 rounded-full" style={{ background: SEVERITY_META[s].dot }} />
              <span className={`text-xs ${textPrimary}`}>{SEVERITY_META[s].label}</span>
            </label>
          ))}
        </div>

        <button
          onClick={acknowledgeAll}
          disabled={filteredActive.length === 0}
          className={`w-full text-xs font-semibold py-2 rounded-lg ${accentBg} ${accentTextOn} disabled:opacity-40`}
        >
          Acknowledge all shown
        </button>
      </div>

      {/* Main content */}
      <div className="flex-1 min-w-0 flex flex-col gap-4">
        {/* Summary stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className={`${cardBg} border ${border} rounded-xl p-3`}>
            <p className={`text-[10px] ${textMuted}`}>Total alerts</p>
            <p className={`text-base font-semibold ${textPrimary}`}>{stats.total}</p>
          </div>
          <div className={`${cardBg} border ${border} rounded-xl p-3`}>
            <p className={`text-[10px] ${textMuted}`}>Active</p>
            <p className="text-base font-semibold text-amber-500">{stats.active}</p>
          </div>
          <div className={`${cardBg} border ${border} rounded-xl p-3`}>
            <p className={`text-[10px] ${textMuted}`}>Critical (active)</p>
            <p className="text-base font-semibold text-red-500">{stats.critical}</p>
          </div>
          <div className={`${cardBg} border ${border} rounded-xl p-3`}>
            <p className={`text-[10px] ${textMuted}`}>Acknowledged</p>
            <p className={`text-base font-semibold ${textPrimary}`}>{stats.acknowledged}</p>
          </div>
        </div>

        {/* Active alerts */}
        <div className={`${cardBg} border ${border} rounded-2xl p-4`}>
          <p className={`text-xs font-semibold ${textPrimary} mb-3`}>Active alerts</p>
          {filteredActive.length === 0 ? (
            <p className={`text-xs ${textMuted}`}>No active alerts matching your filters.</p>
          ) : (
            <div className="flex flex-col gap-2">
              {filteredActive.map((alert) => {
                const meta = SEVERITY_META[alert.severity];
                return (
                  <div
                    key={alert.id}
                    className={`flex items-start justify-between gap-3 p-3 rounded-xl border ${isDark ? meta.dark : meta.light}`}
                  >
                    <div className="flex gap-3">
                      <span className="w-2 h-2 rounded-full mt-1.5 flex-shrink-0" style={{ background: meta.dot }} />
                      <div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <p className="text-xs font-semibold">{alert.type}</p>
                          <span className="text-[9px] font-mono opacity-70">{alert.date} {alert.time}</span>
                          <span className="text-[9px] uppercase font-semibold opacity-70">{meta.label}</span>
                        </div>
                        <p className="text-xs mt-1 opacity-90">{alert.message}</p>
                        <p className="text-[9px] font-mono opacity-60 mt-1">{alert.lat}, {alert.lng}</p>
                      </div>
                    </div>
                    <button
                      onClick={() => acknowledge(alert.id)}
                      className={`text-[10px] font-semibold px-3 py-1.5 rounded-md whitespace-nowrap ${cardBg} border ${border} ${textPrimary}`}
                    >
                      Acknowledge
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Alert history */}
        <div className={`${cardBg} border ${border} rounded-2xl p-4`}>
          <p className={`text-xs font-semibold ${textPrimary} mb-3`}>Alert history</p>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className={`border-b ${border}`}>
                  <th className={`p-2 text-left font-semibold ${textMuted}`}>Timestamp</th>
                  <th className={`p-2 text-left font-semibold ${textMuted}`}>Type</th>
                  <th className={`p-2 text-left font-semibold ${textMuted}`}>Severity</th>
                  <th className={`p-2 text-left font-semibold ${textMuted}`}>Message</th>
                </tr>
              </thead>
              <tbody>
                {history.map((alert) => {
                  const meta = SEVERITY_META[alert.severity];
                  return (
                    <tr key={alert.id} className={`border-b ${border} last:border-0`}>
                      <td className={`p-2 font-mono ${textMuted}`}>{alert.date} {alert.time}</td>
                      <td className={`p-2 ${textPrimary}`}>{alert.type}</td>
                      <td className="p-2">
                        <span className="inline-flex items-center gap-1.5">
                          <span className="w-1.5 h-1.5 rounded-full" style={{ background: meta.dot }} />
                          <span className={textMuted}>{meta.label}</span>
                        </span>
                      </td>
                      <td className={`p-2 ${textMuted}`}>{alert.message}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}