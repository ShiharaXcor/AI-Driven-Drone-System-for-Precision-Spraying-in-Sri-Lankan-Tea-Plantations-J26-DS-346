import { useState } from "react";
import { useTheme } from "../../context/ThemeContext";

export default function ManualControl() {
  const { isDark } = useTheme();
  const [mode, setMode] = useState("auto"); // "auto" | "manual" | "emergency"
  const [sprayOn, setSprayOn] = useState(false);
  const [confirmAction, setConfirmAction] = useState(null); // { type, label, run }
  const [log, setLog] = useState([
    { time: "14:32", event: "System started in Auto mode" },
  ]);

  const cardBg = isDark ? "bg-surface" : "bg-light-surface";
  const border = isDark ? "border-border" : "border-light-border";
  const textMuted = isDark ? "text-muted" : "text-light-muted";
  const textPrimary = isDark ? "text-white" : "text-light-text";
  const inner = isDark ? "bg-ink" : "bg-light-bg";
  const accentBg = isDark ? "bg-accent" : "bg-light-primary";
  const accentTextOn = isDark ? "text-ink" : "text-white";

  function addLog(event) {
    const now = new Date();
    const time = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
    setLog((prev) => [{ time, event }, ...prev]);
  }

  function requestConfirm(type, label, run) {
    setConfirmAction({ type, label, run });
  }

  function runConfirmed() {
    confirmAction.run();
    setConfirmAction(null);
  }

  function triggerEmergencyStop() {
    setMode("emergency");
    setSprayOn(false);
    addLog("EMERGENCY STOP activated — all systems halted");
  }

  function engageManualOverride() {
    setMode("manual");
    addLog("Manual override engaged by operator");
  }

  function resumeAuto() {
    setMode("auto");
    setSprayOn(false);
    addLog("Resumed Automatic mode");
  }

  function toggleSpray() {
    const next = !sprayOn;
    setSprayOn(next);
    addLog(`Spray manually turned ${next ? "ON" : "OFF"}`);
  }

  const modeMeta = {
    auto: { label: "AUTOMATIC", color: isDark ? "bg-accent text-ink" : "bg-light-primary text-white" },
    manual: { label: "MANUAL", color: "bg-amber-500 text-white" },
    emergency: { label: "EMERGENCY STOPPED", color: "bg-red-500 text-white" },
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Mode status banner */}
      <div className={`${cardBg} border ${border} rounded-2xl p-4 flex items-center justify-between flex-wrap gap-3`}>
        <div>
          <p className={`text-xs ${textMuted}`}>Current control mode</p>
          <p className={`text-lg font-bold ${textPrimary}`}>{modeMeta[mode].label}</p>
        </div>
        <span className={`text-xs font-semibold px-3 py-1.5 rounded-full ${modeMeta[mode].color}`}>
          ● {mode === "emergency" ? "HALTED" : mode === "manual" ? "OPERATOR CONTROL" : "MODEL CONTROL"}
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Left: controls */}
        <div className="flex flex-col gap-4">
          {/* Emergency stop */}
          <div className={`${cardBg} border ${border} rounded-2xl p-5`}>
            <p className={`text-xs ${textMuted} mb-3`}>Safety control</p>
            <button
              onClick={() =>
                requestConfirm(
                  "emergency",
                  "This will immediately halt spraying and flight decisions. Confirm emergency stop?",
                  triggerEmergencyStop
                )
              }
              disabled={mode === "emergency"}
              className="w-full py-4 rounded-2xl bg-red-500 text-white font-bold text-base tracking-wide hover:bg-red-600 transition disabled:opacity-40"
            >
              EMERGENCY STOP
            </button>
            <p className={`text-[10px] ${textMuted} mt-2`}>
              Immediately halts spray pump and hands full control to the operator.
            </p>
          </div>

          {/* Manual override */}
          <div className={`${cardBg} border ${border} rounded-2xl p-5`}>
            <div className="flex items-center justify-between mb-3">
              <p className={`text-xs ${textMuted}`}>Manual override</p>
              <button
                onClick={() =>
                  mode === "manual"
                    ? requestConfirm("resume", "Hand control back to the automatic decision model?", resumeAuto)
                    : requestConfirm("manual", "Switch from Automatic to Manual control?", engageManualOverride)
                }
                disabled={mode === "emergency"}
                className={`w-11 h-6 rounded-full relative transition disabled:opacity-40 ${
                  mode === "manual" ? accentBg : isDark ? "bg-border" : "bg-light-border"
                }`}
              >
                <span
                  className={`absolute top-0.5 w-5 h-5 rounded-full bg-white transition-all ${
                    mode === "manual" ? "left-5" : "left-0.5"
                  }`}
                />
              </button>
            </div>

            {mode === "manual" ? (
              <div>
                <p className={`text-xs ${textPrimary} mb-2`}>Spray pump</p>
                <button
                  onClick={toggleSpray}
                  className={`w-full py-3 rounded-xl font-semibold text-sm transition ${
                    sprayOn ? "bg-red-500 text-white" : `${accentBg} ${accentTextOn}`
                  }`}
                >
                  {sprayOn ? "TURN SPRAY OFF" : "TURN SPRAY ON"}
                </button>
              </div>
            ) : (
              <p className={`text-[10px] ${textMuted}`}>
                Enable manual override to take direct control of the spray pump.
              </p>
            )}
          </div>

          {/* Resume auto */}
          <button
            onClick={() => requestConfirm("resume", "Resume fully Automatic mode?", resumeAuto)}
            disabled={mode === "auto"}
            className={`py-3 rounded-full border ${border} text-sm font-semibold ${textPrimary} hover:opacity-80 transition disabled:opacity-40`}
          >
            Resume Automatic mode
          </button>
        </div>

        {/* Right: live reference + activity log */}
        <div className="flex flex-col gap-4">
          <div className={`${cardBg} border ${border} rounded-2xl p-4`}>
            <p className={`text-xs ${textMuted} mb-2`}>Live feed reference</p>
            <div className={`relative rounded-xl h-40 ${inner} border border-dashed ${border} flex items-center justify-center`}>
              <p className={`text-xs ${textMuted}`}>Camera feed placeholder</p>
            </div>
            <div className="grid grid-cols-2 gap-3 mt-3">
              <div className={`${inner} rounded-lg p-2`}>
                <p className={`text-[10px] ${textMuted}`}>Tea confidence</p>
                <p className={`text-sm font-semibold ${textPrimary}`}>0.91</p>
              </div>
              <div className={`${inner} rounded-lg p-2`}>
                <p className={`text-[10px] ${textMuted}`}>Spray status</p>
                <p className={`text-sm font-semibold ${textPrimary}`}>{sprayOn ? "ON" : "OFF"}</p>
              </div>
            </div>
          </div>

          <div className={`${cardBg} border ${border} rounded-2xl p-4 flex-1`}>
            <p className={`text-xs ${textMuted} mb-3`}>Control activity log</p>
            <div className="flex flex-col gap-2 max-h-48 overflow-y-auto">
              {log.map((entry, i) => (
                <div key={i} className={`flex gap-2 text-xs ${textPrimary}`}>
                  <span className={`font-mono ${textMuted}`}>{entry.time}</span>
                  <span>{entry.event}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Confirmation modal */}
      {confirmAction && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 px-6">
          <div className={`${cardBg} border ${border} rounded-2xl p-6 max-w-sm w-full`}>
            <p className={`text-sm font-semibold ${textPrimary} mb-2`}>Confirm action</p>
            <p className={`text-xs ${textMuted} mb-5`}>{confirmAction.label}</p>
            <div className="flex gap-2">
              <button
                onClick={() => setConfirmAction(null)}
                className={`flex-1 py-2.5 rounded-full border ${border} text-sm font-semibold ${textPrimary}`}
              >
                Cancel
              </button>
              <button
                onClick={runConfirmed}
                className={`flex-1 py-2.5 rounded-full text-sm font-semibold ${
                  confirmAction.type === "emergency" ? "bg-red-500 text-white" : `${accentBg} ${accentTextOn}`
                }`}
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}