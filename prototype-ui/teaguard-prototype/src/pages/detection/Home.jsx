import { useState } from "react";
import { useTheme } from "../../context/ThemeContext";

const INITIAL_ALERTS = [
  { id: 1, time: "14:32", type: "Person detected", message: "Person detected in zone A-11, spray halted", priority: "critical" },
  { id: 2, time: "14:28", type: "Low battery", message: "Battery below 80%, plan return soon", priority: "warning" },
  { id: 3, time: "14:20", type: "Sync complete", message: "Detection log synced to server", priority: "info" },
];

const PRIORITY_STYLES = {
  critical: { dark: "bg-red-500/15 text-red-400 border-red-500/30", light: "bg-red-50 text-red-600 border-red-200" },
  warning: { dark: "bg-amber-500/15 text-amber-400 border-amber-500/30", light: "bg-amber-50 text-amber-600 border-amber-200" },
  info: { dark: "bg-blue-500/15 text-blue-400 border-blue-500/30", light: "bg-blue-50 text-blue-600 border-blue-200" },
};

export default function Home() {
  const { isDark } = useTheme();
  const [alerts, setAlerts] = useState(INITIAL_ALERTS);
  const [controlMode, setControlMode] = useState("auto"); // "auto" | "manual" | "emergency"

  const cardBg = isDark ? "bg-surface" : "bg-light-surface";
  const border = isDark ? "border-border" : "border-light-border";
  const textMuted = isDark ? "text-muted" : "text-light-muted";
  const textPrimary = isDark ? "text-white" : "text-light-text";
  const inner = isDark ? "bg-ink" : "bg-light-bg";
  const accent = isDark ? "bg-accent" : "bg-light-primary";
  const accentText = isDark ? "text-accent" : "text-light-primary";
  const accentTextOn = isDark ? "text-ink" : "text-white";

  function acknowledgeAlert(id) {
    setAlerts((prev) => prev.filter((a) => a.id !== id));
  }

  const decision = "SPRAY";
  const decisionReason = "Tea detected with high confidence, no anomalies in frame";

  return (
    <div className="flex flex-col gap-4">
      {/* Quick stats strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          ["Flight time", "00:42:18"],
          ["Battery", "78%"],
          ["Spray status", "ON"],
          ["Alert count", alerts.length],
        ].map(([label, value]) => (
          <div key={label} className={`${cardBg} border ${border} rounded-xl p-3`}>
            <p className={`text-[10px] ${textMuted}`}>{label}</p>
            <p className={`text-base font-semibold ${textPrimary}`}>{value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Section 1 — Live camera feed */}
        <div className={`lg:col-span-2 ${cardBg} border ${border} rounded-2xl p-4`}>
          <div className="flex items-center justify-between mb-2">
            <p className={`text-xs ${textMuted}`}>Live feed — Block 7</p>
            <span className={`text-[10px] ${textMuted}`}>Updating every 1.5s</span>
          </div>
          <div className={`relative rounded-xl h-64 ${inner} border border-dashed ${border} overflow-hidden`}>
            <div className="absolute left-8 top-8 w-24 h-20 border-2 rounded" style={{ borderColor: isDark ? "#C6F135" : "#2F5233" }}>
              <span className={`absolute -top-5 left-0 text-[10px] font-semibold px-1.5 py-0.5 rounded ${accent} ${accentTextOn}`}>
                tea 0.91
              </span>
            </div>
            <div className="absolute right-10 bottom-10 w-16 h-24 border-2 border-red-500 rounded">
              <span className="absolute -top-5 left-0 text-[10px] font-semibold px-1.5 py-0.5 rounded bg-red-500 text-white">
                person 0.86
              </span>
            </div>
          </div>
        </div>

        {/* Section 4 — Spray decision card */}
        <div className={`${accent} rounded-2xl p-4 flex flex-col justify-center`}>
          <p className={`text-[10px] font-semibold ${accentTextOn} opacity-80 mb-1`}>CURRENT DECISION</p>
          <p className={`text-3xl font-bold ${accentTextOn} mb-2`}>{decision}</p>
          <p className={`text-xs ${accentTextOn} opacity-90 leading-snug`}>{decisionReason}</p>
        </div>
      </div>

      {/* Section 2 — Telemetry */}
      <div className={`${cardBg} border ${border} rounded-2xl p-4`}>
        <p className={`text-xs ${textMuted} mb-3`}>Telemetry</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className={`${inner} rounded-lg p-3`}>
            <p className={`text-[10px] ${textMuted}`}>GPS</p>
            <p className={`text-sm font-mono ${textPrimary}`}>7.2906, 80.6337</p>
          </div>
          <div className={`${inner} rounded-lg p-3`}>
            <p className={`text-[10px] ${textMuted}`}>Altitude</p>
            <p className={`text-sm font-semibold ${textPrimary}`}>2.6 m</p>
          </div>
          <div className={`${inner} rounded-lg p-3`}>
            <p className={`text-[10px] ${textMuted}`}>Spray status</p>
            <p className={`text-sm font-semibold ${accentText}`}>ON</p>
          </div>
          <div className={`${inner} rounded-lg p-3`}>
            <p className={`text-[10px] ${textMuted}`}>Decision</p>
            <p className={`text-sm font-semibold ${accentText}`}>SPRAY</p>
          </div>
        </div>
      </div>

      {/* Section 3 — Confidence scores */}
      <div className={`${cardBg} border ${border} rounded-2xl p-4`}>
        <p className={`text-xs ${textMuted} mb-3`}>Detection confidence</p>
        <div className="flex flex-col gap-3">
          {[
            ["Tea", 0.91],
            ["Person", 0.86],
            ["Animal", 0.12],
            ["Anomaly", 0.34],
          ].map(([label, value]) => (
            <div key={label}>
              <div className="flex justify-between mb-1">
                <span className={`text-xs ${textMuted}`}>{label}</span>
                <span className={`text-xs font-semibold ${textPrimary}`}>{value.toFixed(2)}</span>
              </div>
              <div className={`h-1.5 ${inner} rounded-full overflow-hidden`}>
                <div
                  className={`h-full rounded-full ${accent}`}
                  style={{ width: `${value * 100}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Section 5 — Alert panel */}
        <div className={`${cardBg} border ${border} rounded-2xl p-4`}>
          <p className={`text-xs ${textMuted} mb-3`}>Active alerts</p>
          <div className="flex flex-col gap-2">
            {alerts.length === 0 && (
              <p className={`text-xs ${textMuted}`}>No active alerts.</p>
            )}
            {alerts.map((alert) => {
              const style = PRIORITY_STYLES[alert.priority];
              return (
                <div
                  key={alert.id}
                  className={`flex items-start justify-between gap-3 p-2.5 rounded-lg border ${isDark ? style.dark : style.light}`}
                >
                  <div>
                    <p className="text-[10px] font-mono opacity-70">{alert.time} · {alert.type}</p>
                    <p className="text-xs mt-0.5">{alert.message}</p>
                  </div>
                  <button
                    onClick={() => acknowledgeAlert(alert.id)}
                    className={`text-[10px] font-semibold px-2 py-1 rounded-md whitespace-nowrap ${cardBg} border ${border} ${textPrimary}`}
                  >
                    Acknowledge
                  </button>
                </div>
              );
            })}
          </div>
        </div>

        {/* Section 6 — Emergency controls */}
        <div className={`${cardBg} border ${border} rounded-2xl p-4`}>
          <div className="flex items-center justify-between mb-3">
            <p className={`text-xs ${textMuted}`}>Control mode</p>
            <span
              className={`text-[10px] font-semibold px-2 py-1 rounded-full ${
                controlMode === "emergency"
                  ? "bg-red-500 text-white"
                  : controlMode === "manual"
                  ? "bg-amber-500 text-white"
                  : `${accent} ${accentTextOn}`
              }`}
            >
              {controlMode.toUpperCase()}
            </span>
          </div>

          <button
            onClick={() => setControlMode("emergency")}
            className="w-full py-3 rounded-full bg-red-500 text-white font-semibold text-sm mb-2 hover:bg-red-600 transition"
          >
            EMERGENCY STOP
          </button>

          <div className={`flex items-center justify-between ${inner} rounded-lg p-3 mb-2`}>
            <span className={`text-xs ${textPrimary}`}>Manual override</span>
            <button
              onClick={() => setControlMode(controlMode === "manual" ? "auto" : "manual")}
              className={`w-10 h-5 rounded-full relative transition ${
                controlMode === "manual" ? accent : isDark ? "bg-border" : "bg-light-border"
              }`}
            >
              <span
                className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all ${
                  controlMode === "manual" ? "left-5" : "left-0.5"
                }`}
              />
            </button>
          </div>

          <button
            onClick={() => setControlMode("auto")}
            className={`w-full py-2.5 rounded-full border ${border} text-sm font-semibold ${textPrimary} hover:opacity-80 transition`}
          >
            Resume auto mode
          </button>
        </div>
      </div>
    </div>
  );
}