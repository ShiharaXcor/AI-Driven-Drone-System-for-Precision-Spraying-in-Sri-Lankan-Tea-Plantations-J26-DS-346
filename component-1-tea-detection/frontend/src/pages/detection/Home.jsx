import { useEffect, useRef, useState } from "react";
import { useTheme } from "../../context/ThemeContext";
import { useLive } from "../../context/LiveContext";
import { api, fileUrl } from "../../api";
import { normalizeAlert } from "../../utils";

const PRIORITY_STYLES = {
  critical: { dark: "bg-red-500/15 text-red-400 border-red-500/30", light: "bg-red-50 text-red-600 border-red-200" },
  warning: { dark: "bg-amber-500/15 text-amber-400 border-amber-500/30", light: "bg-amber-50 text-amber-600 border-amber-200" },
  info: { dark: "bg-blue-500/15 text-blue-400 border-blue-500/30", light: "bg-blue-50 text-blue-600 border-blue-200" },
};

const KNOWN = ["tea_plant", "person", "animal"];

export default function Home() {
  const { isDark } = useTheme();
  const { status, events, alerts: rawAlerts, online, ack, refreshStatus, refreshEvents } = useLive();

  const [detail, setDetail] = useState(null);      // detections of the newest event
  const [models, setModels] = useState(null);      // which weights are loaded (demo or trained)
  const [gps, setGps] = useState(null);
  const [showShadow, setShowShadow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const fileRef = useRef(null);

  const cardBg = isDark ? "bg-surface" : "bg-light-surface";
  const border = isDark ? "border-border" : "border-light-border";
  const textMuted = isDark ? "text-muted" : "text-light-muted";
  const textPrimary = isDark ? "text-white" : "text-light-text";
  const inner = isDark ? "bg-ink" : "bg-light-bg";
  const accent = isDark ? "bg-accent" : "bg-light-primary";
  const accentText = isDark ? "text-accent" : "text-light-primary";
  const accentTextOn = isDark ? "text-ink" : "text-white";

  const latest = events[0] || null;
  const latestId = latest?.id;

  // Load the detections of the newest event (needed for the anomaly bar)
  useEffect(() => {
    if (!latestId) return;
    let on = true;
    api.event(latestId).then((d) => on && setDetail(d)).catch(() => {});
    return () => { on = false; };
  }, [latestId]);

  // Which weights are in use (decides whether to show the DEMO warning)
  useEffect(() => {
    api.models().then(setModels).catch(() => {});
  }, []);

  // Live GPS position
  useEffect(() => {
    let on = true;
    const load = () => api.gps().then((g) => on && setGps(g)).catch(() => {});
    load();
    const t = setInterval(load, 3000);
    return () => { on = false; clearInterval(t); };
  }, []);

  const alerts = rawAlerts.filter((a) => !a.acked).slice(0, 5).map(normalizeAlert);
  const activeCount = rawAlerts.filter((a) => !a.acked).length;

  const controlMode = status?.emergency ? "emergency" : status?.manual ? "manual" : "auto";
  const sprayStatus = status?.relay_on ? "ON" : "OFF";

  const decision = latest?.decision ?? "NO DATA";
  const decisionReason = latest?.reason ?? "Waiting for the first detection. Run detection on an image.";
  const [decisionBg, decisionText] =
    {
      SPRAY: [accent, accentTextOn],
      NO_SPRAY: ["bg-red-500", "text-white"],
      UNCERTAIN: ["bg-amber-500", "text-white"],
    }[decision] || [`${cardBg} border ${border}`, textPrimary];

  const tea = latest?.tea_conf ?? 0;
  const person = latest?.person_conf ?? 0;
  const animal = latest?.animal_conf ?? 0;
  const anomaly =
    detail && detail.id === latestId
      ? Math.max(0, ...detail.detections.filter((d) => !KNOWN.includes(d.cls)).map((d) => d.conf))
      : 0;

  const shadowUrl = latest?.image_url ? latest.image_url.replace(/\.jpg$/, "_shadow.jpg") : "";
  const feedImage = latest?.image_url ? fileUrl(showShadow ? shadowUrl : latest.image_url) : "";
  const demo = models && !models.main_model.exists;

  async function onPick(e) {
    const file = e.target.files[0];
    e.target.value = "";
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      await api.infer(file);
      setShowShadow(false);
      await refreshEvents();
      await refreshStatus();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function control(fn) {
    setError("");
    try {
      await fn();
      await refreshStatus();
    } catch (err) {
      setError(err.message);
    }
  }

  const resume = () =>
    control(async () => {
      if (status?.emergency) await api.emergency(false);
      await api.manual("AUTO");
    });

  return (
    <div className="flex flex-col gap-4">
      {/* Quick stats strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          ["Flight time", "00:42:18"],   // comes from Component 2 (flight control) later
          ["Battery", "78%"],            // comes from Component 2 (flight control) later
          ["Spray status", sprayStatus],
          ["Alert count", activeCount],
        ].map(([label, value]) => (
          <div key={label} className={`${cardBg} border ${border} rounded-xl p-3`}>
            <p className={`text-[10px] ${textMuted}`}>{label}</p>
            <p className={`text-base font-semibold ${textPrimary}`}>{value}</p>
          </div>
        ))}
      </div>

      {demo && (
        <div className={`rounded-xl border p-3 text-xs ${isDark ? PRIORITY_STYLES.warning.dark : PRIORITY_STYLES.warning.light}`}>
          DEMO mode: no trained model is loaded yet. Tea detection is a green-colour estimate, and person/animal come from a general pretrained model.
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Section 1 — Live camera feed */}
        <div className={`lg:col-span-2 ${cardBg} border ${border} rounded-2xl p-4`}>
          <div className="flex items-center justify-between mb-2 gap-2 flex-wrap">
            <p className={`text-xs ${textMuted}`}>Live feed — Block 7</p>
            <div className="flex items-center gap-2">
              <span className={`text-[10px] ${textMuted}`}>{online ? "Live" : "Offline, reconnecting..."}</span>
              {feedImage && (
                <button
                  onClick={() => setShowShadow((v) => !v)}
                  className={`text-[10px] font-semibold px-2.5 py-1 rounded-lg border ${border} ${textPrimary}`}
                >
                  {showShadow ? "Show detections" : "Show shadow"}
                </button>
              )}
              <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={onPick} />
              <button
                onClick={() => fileRef.current.click()}
                disabled={busy}
                className={`text-[10px] font-semibold px-2.5 py-1 rounded-lg ${accent} ${accentTextOn} disabled:opacity-40`}
              >
                {busy ? "Running..." : "Run detection on image"}
              </button>
            </div>
          </div>
          <div className={`relative rounded-xl h-64 ${inner} border border-dashed ${border} overflow-hidden flex items-center justify-center`}>
            {feedImage ? (
              <img src={feedImage} alt="latest detection" className="w-full h-full object-contain" />
            ) : (
              <p className={`text-xs ${textMuted}`}>No image yet. Run detection on an image to see boxes here.</p>
            )}
          </div>
          {busy && <p className={`text-[10px] ${textMuted} mt-2`}>The first image loads the models and can take up to a minute.</p>}
          {latest && latest.shadow_ratio != null && (
            <p className={`text-[10px] ${textMuted} mt-2`}>
              Shadow {(latest.shadow_ratio * 100).toFixed(0)}%
              {latest.enh_method && latest.enh_method !== "none" ? ` · enhancement ${latest.enh_method}` : ""}
              {latest.tea_before != null ? ` · tea confidence ${latest.tea_before.toFixed(2)}${latest.tea_after != null ? ` to ${latest.tea_after.toFixed(2)}` : ""}` : ""}
              {latest.latency_ms != null ? ` · ${latest.latency_ms.toFixed(0)} ms` : ""}
            </p>
          )}
        </div>

        {/* Section 4 — Spray decision card */}
        <div className={`${decisionBg} rounded-2xl p-4 flex flex-col justify-center`}>
          <p className={`text-[10px] font-semibold ${decisionText} opacity-80 mb-1`}>CURRENT DECISION</p>
          <p className={`text-3xl font-bold ${decisionText} mb-2`}>{decision}</p>
          <p className={`text-xs ${decisionText} opacity-90 leading-snug`}>{decisionReason}</p>
        </div>
      </div>

      {/* Section 2 — Telemetry */}
      <div className={`${cardBg} border ${border} rounded-2xl p-4`}>
        <p className={`text-xs ${textMuted} mb-3`}>Telemetry</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className={`${inner} rounded-lg p-3`}>
            <p className={`text-[10px] ${textMuted}`}>GPS</p>
            <p className={`text-sm font-mono ${textPrimary}`}>
              {gps ? `${gps.lat.toFixed(4)}, ${gps.lon.toFixed(4)}` : "-"}
            </p>
          </div>
          <div className={`${inner} rounded-lg p-3`}>
            <p className={`text-[10px] ${textMuted}`}>Altitude</p>
            <p className={`text-sm font-semibold ${textPrimary}`}>{gps ? `${gps.alt.toFixed(1)} m` : "-"}</p>
          </div>
          <div className={`${inner} rounded-lg p-3`}>
            <p className={`text-[10px] ${textMuted}`}>Spray status</p>
            <p className={`text-sm font-semibold ${accentText}`}>{sprayStatus}</p>
          </div>
          <div className={`${inner} rounded-lg p-3`}>
            <p className={`text-[10px] ${textMuted}`}>Decision</p>
            <p className={`text-sm font-semibold ${accentText}`}>{decision}</p>
          </div>
        </div>
      </div>

      {/* Section 3 — Confidence scores */}
      <div className={`${cardBg} border ${border} rounded-2xl p-4`}>
        <p className={`text-xs ${textMuted} mb-3`}>Detection confidence</p>
        <div className="flex flex-col gap-3">
          {[
            ["Tea", tea],
            ["Person", person],
            ["Animal", animal],
            ["Anomaly", anomaly],
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
              const style = PRIORITY_STYLES[alert.severity] || PRIORITY_STYLES.info;
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
                    onClick={() => ack([alert.id])}
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
            onClick={() => control(() => api.emergency(true))}
            disabled={controlMode === "emergency"}
            className="w-full py-3 rounded-full bg-red-500 text-white font-semibold text-sm mb-2 hover:bg-red-600 transition disabled:opacity-40"
          >
            EMERGENCY STOP
          </button>

          <div className={`flex items-center justify-between ${inner} rounded-lg p-3 mb-2`}>
            <span className={`text-xs ${textPrimary}`}>Manual override</span>
            <button
              onClick={() => control(() => api.manual(controlMode === "manual" ? "AUTO" : "OFF"))}
              disabled={controlMode === "emergency"}
              className={`w-10 h-5 rounded-full relative transition disabled:opacity-40 ${
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
            onClick={resume}
            disabled={controlMode === "auto"}
            className={`w-full py-2.5 rounded-full border ${border} text-sm font-semibold ${textPrimary} hover:opacity-80 transition disabled:opacity-40`}
          >
            Resume auto mode
          </button>
          {error && <p className="text-[10px] text-red-500 mt-2">{error}</p>}
        </div>
      </div>
    </div>
  );
}