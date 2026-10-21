import { useState } from "react";
import { useTheme } from "../../context/ThemeContext";

const CATEGORIES = [
  { id: "model", label: "Model Settings" },
  { id: "spray", label: "Spray Control" },
  { id: "notifications", label: "Notifications" },
  { id: "gps", label: "GPS & Logging" },
  { id: "system", label: "System" },
];

export default function Settings() {
  const { isDark } = useTheme();
  const [category, setCategory] = useState("model");
  const [savedFlash, setSavedFlash] = useState(null);

  const cardBg = isDark ? "bg-surface" : "bg-light-surface";
  const border = isDark ? "border-border" : "border-light-border";
  const textMuted = isDark ? "text-muted" : "text-light-muted";
  const textPrimary = isDark ? "text-white" : "text-light-text";
  const inner = isDark ? "bg-ink" : "bg-light-bg";
  const accentBg = isDark ? "bg-accent" : "bg-light-primary";
  const accentTextOn = isDark ? "text-ink" : "text-white";
  const accentText = isDark ? "text-accent" : "text-light-primary";

  function flashSaved(section) {
    setSavedFlash(section);
    setTimeout(() => setSavedFlash(null), 1800);
  }

  const shared = { isDark, cardBg, border, textMuted, textPrimary, inner, accentBg, accentTextOn, accentText, flashSaved, savedFlash };

  return (
    <div className="flex flex-col lg:flex-row gap-4">
      {/* Category sidebar */}
      <div className={`lg:w-52 flex-shrink-0 ${cardBg} border ${border} rounded-2xl p-2 h-fit`}>
        {CATEGORIES.map((cat) => (
          <button
            key={cat.id}
            onClick={() => setCategory(cat.id)}
            className={`w-full text-left text-xs px-3 py-2.5 rounded-xl mb-1 transition ${
              category === cat.id ? `${accentBg} ${accentTextOn} font-semibold` : `${textMuted} hover:opacity-80`
            }`}
          >
            {cat.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        {category === "model" && <ModelSettings {...shared} />}
        {category === "spray" && <SprayControlSettings {...shared} />}
        {category === "notifications" && <NotificationSettings {...shared} />}
        {category === "gps" && <GpsLoggingSettings {...shared} />}
        {category === "system" && <SystemInfo {...shared} />}
      </div>
    </div>
  );
}

/* ---------- shared bits ---------- */

function SavedBadge({ show }) {
  if (!show) return null;
  return <span className="text-[10px] text-emerald-500 font-semibold ml-2">✓ Saved</span>;
}

function ThresholdSlider({ label, value, onChange, onSave, saved, accentText, textMuted, textPrimary, accentBg, accentTextOn }) {
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className={`text-xs ${textPrimary}`}>{label}</span>
        <span className={`text-xs font-semibold ${accentText}`}>{value.toFixed(2)}</span>
      </div>
      <div className="flex items-center gap-3">
        <input
          type="range"
          min="0"
          max="1"
          step="0.01"
          value={value}
          onChange={(e) => onChange(parseFloat(e.target.value))}
          className="flex-1"
        />
        <button
          onClick={onSave}
          className={`text-[10px] font-semibold px-2.5 py-1 rounded-lg ${accentBg} ${accentTextOn}`}
        >
          Save
        </button>
      </div>
      <SavedBadge show={saved} />
    </div>
  );
}

/* ---------- Section 1: Model Settings ---------- */

function ModelSettings({ cardBg, border, textMuted, textPrimary, inner, accentBg, accentTextOn, accentText, flashSaved, savedFlash }) {
  const [thresholds, setThresholds] = useState({ tea: 0.6, person: 0.5, animal: 0.5, anomaly: 0.6 });
  const [shadowAware, setShadowAware] = useState(true);

  return (
    <div className="flex flex-col gap-4">
      <div className={`${cardBg} border ${border} rounded-2xl p-4`}>
        <p className={`text-xs font-semibold ${textPrimary} mb-4`}>Confidence thresholds</p>
        <div className="flex flex-col gap-4">
          {[
            ["tea", "Tea threshold"],
            ["person", "Person threshold"],
            ["animal", "Animal threshold"],
            ["anomaly", "Anomaly threshold"],
          ].map(([key, label]) => (
            <ThresholdSlider
              key={key}
              label={label}
              value={thresholds[key]}
              onChange={(v) => setThresholds((prev) => ({ ...prev, [key]: v }))}
              onSave={() => flashSaved(key)}
              saved={savedFlash === key}
              accentText={accentText}
              textMuted={textMuted}
              textPrimary={textPrimary}
              accentBg={accentBg}
              accentTextOn={accentTextOn}
            />
          ))}
        </div>
      </div>

      <div className={`${cardBg} border ${border} rounded-2xl p-4`}>
        <p className={`text-xs font-semibold ${textPrimary} mb-3`}>Shadow-aware detection</p>
        <div className={`flex items-center justify-between ${inner} rounded-lg p-3`}>
          <div>
            <p className={`text-xs ${textPrimary}`}>Enable shadow enhancement pass</p>
            <p className={`text-[10px] ${textMuted} mt-0.5`}>
              Applies preprocessing to improve detection under shaded canopy
            </p>
          </div>
          <button
            onClick={() => setShadowAware((v) => !v)}
            className={`w-10 h-5 rounded-full relative transition flex-shrink-0 ${shadowAware ? accentBg : "bg-gray-500"}`}
          >
            <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all ${shadowAware ? "left-5" : "left-0.5"}`} />
          </button>
        </div>
      </div>

      <div className={`${cardBg} border ${border} rounded-2xl p-4`}>
        <p className={`text-xs font-semibold ${textPrimary} mb-2`}>Model info</p>
        <div className="grid grid-cols-2 gap-3">
          <div className={`${inner} rounded-lg p-2.5`}>
            <p className={`text-[10px] ${textMuted}`}>Model checkpoint</p>
            <p className={`text-xs font-semibold ${textPrimary}`}>yolo-tea-v3.pt</p>
          </div>
          <div className={`${inner} rounded-lg p-2.5`}>
            <p className={`text-[10px] ${textMuted}`}>Last updated</p>
            <p className={`text-xs font-semibold ${textPrimary}`}>2026-08-15</p>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ---------- Section 2: Spray Control ---------- */

function SprayControlSettings({ cardBg, border, textMuted, textPrimary, inner, accentBg, accentTextOn, flashSaved, savedFlash }) {
  const [minOn, setMinOn] = useState(2);
  const [minOff, setMinOff] = useState(1);
  const [smoothing, setSmoothing] = useState(true);
  const [window, setWindowSize] = useState(3);

  return (
    <div className={`${cardBg} border ${border} rounded-2xl p-4 flex flex-col gap-5`}>
      <p className={`text-xs font-semibold ${textPrimary}`}>Spray timing</p>

      <div>
        <div className="flex items-center justify-between mb-1">
          <span className={`text-xs ${textPrimary}`}>Minimum ON time</span>
          <span className={`text-xs font-semibold ${textPrimary}`}>{minOn}s</span>
        </div>
        <div className="flex items-center gap-3">
          <input type="range" min="0" max="10" step="0.5" value={minOn} onChange={(e) => setMinOn(parseFloat(e.target.value))} className="flex-1" />
          <button onClick={() => flashSaved("minOn")} className={`text-[10px] font-semibold px-2.5 py-1 rounded-lg ${accentBg} ${accentTextOn}`}>Save</button>
        </div>
        <SavedBadge show={savedFlash === "minOn"} />
      </div>

      <div>
        <div className="flex items-center justify-between mb-1">
          <span className={`text-xs ${textPrimary}`}>Minimum OFF time</span>
          <span className={`text-xs font-semibold ${textPrimary}`}>{minOff}s</span>
        </div>
        <div className="flex items-center gap-3">
          <input type="range" min="0" max="10" step="0.5" value={minOff} onChange={(e) => setMinOff(parseFloat(e.target.value))} className="flex-1" />
          <button onClick={() => flashSaved("minOff")} className={`text-[10px] font-semibold px-2.5 py-1 rounded-lg ${accentBg} ${accentTextOn}`}>Save</button>
        </div>
        <SavedBadge show={savedFlash === "minOff"} />
      </div>

      <div className={`flex items-center justify-between ${inner} rounded-lg p-3`}>
        <span className={`text-xs ${textPrimary}`}>Temporal smoothing</span>
        <button
          onClick={() => setSmoothing((v) => !v)}
          className={`w-10 h-5 rounded-full relative transition ${smoothing ? accentBg : "bg-gray-500"}`}
        >
          <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all ${smoothing ? "left-5" : "left-0.5"}`} />
        </button>
      </div>

      {smoothing && (
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className={`text-xs ${textPrimary}`}>Smoothing window</span>
            <span className={`text-xs font-semibold ${textPrimary}`}>{window} frames</span>
          </div>
          <div className="flex items-center gap-3">
            <input type="range" min="1" max="10" step="1" value={window} onChange={(e) => setWindowSize(parseInt(e.target.value))} className="flex-1" />
            <button onClick={() => flashSaved("window")} className={`text-[10px] font-semibold px-2.5 py-1 rounded-lg ${accentBg} ${accentTextOn}`}>Save</button>
          </div>
          <SavedBadge show={savedFlash === "window"} />
        </div>
      )}
    </div>
  );
}

/* ---------- Section 3: Notifications ---------- */

function NotificationSettings({ cardBg, border, textMuted, textPrimary, inner, accentBg, accentTextOn, flashSaved, savedFlash }) {
  const [email, setEmail] = useState({ enabled: true, value: "" });
  const [whatsapp, setWhatsapp] = useState({ enabled: false, value: "" });
  const [sms, setSms] = useState({ enabled: false, value: "" });
  const [push, setPush] = useState(false);

  const channels = [
    { key: "email", label: "Email notifications", state: email, setState: setEmail, placeholder: "you@example.com", type: "email" },
    { key: "whatsapp", label: "WhatsApp notifications", state: whatsapp, setState: setWhatsapp, placeholder: "+94 7X XXX XXXX", type: "tel" },
    { key: "sms", label: "SMS notifications (optional)", state: sms, setState: setSms, placeholder: "+94 7X XXX XXXX", type: "tel" },
  ];

  return (
    <div className="flex flex-col gap-4">
      {channels.map((ch) => (
        <div key={ch.key} className={`${cardBg} border ${border} rounded-2xl p-4`}>
          <div className="flex items-center justify-between mb-3">
            <span className={`text-xs font-semibold ${textPrimary}`}>{ch.label}</span>
            <button
              onClick={() => ch.setState((prev) => ({ ...prev, enabled: !prev.enabled }))}
              className={`w-10 h-5 rounded-full relative transition ${ch.state.enabled ? accentBg : "bg-gray-500"}`}
            >
              <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all ${ch.state.enabled ? "left-5" : "left-0.5"}`} />
            </button>
          </div>
          {ch.state.enabled && (
            <div className="flex items-center gap-2">
              <input
                type={ch.type}
                value={ch.state.value}
                onChange={(e) => ch.setState((prev) => ({ ...prev, value: e.target.value }))}
                placeholder={ch.placeholder}
                className={`flex-1 text-xs ${inner} border ${border} rounded-lg px-3 py-2 ${textPrimary}`}
              />
              <button onClick={() => flashSaved(ch.key)} className={`text-[10px] font-semibold px-3 py-2 rounded-lg ${accentBg} ${accentTextOn}`}>
                Save
              </button>
            </div>
          )}
          <SavedBadge show={savedFlash === ch.key} />
        </div>
      ))}

      <div className={`${cardBg} border ${border} rounded-2xl p-4`}>
        <div className="flex items-center justify-between">
          <div>
            <p className={`text-xs font-semibold ${textPrimary}`}>Push notifications (optional)</p>
            <p className={`text-[10px] ${textMuted} mt-0.5`}>Requires device setup</p>
          </div>
          <button
            onClick={() => setPush(true)}
            className={`text-[10px] font-semibold px-3 py-2 rounded-lg border ${border} ${textPrimary}`}
          >
            {push ? "Configured ✓" : "Set up push"}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ---------- Section 4: GPS & Logging ---------- */

function GpsLoggingSettings({ cardBg, border, textMuted, textPrimary, inner, accentBg, accentTextOn, flashSaved, savedFlash }) {
  const [logs, setLogs] = useState({
    detections: true,
    sprayEvents: true,
    telemetry: true,
    alerts: true,
  });

  const items = [
    ["detections", "Log all detections"],
    ["sprayEvents", "Log spray events"],
    ["telemetry", "Log telemetry"],
    ["alerts", "Log alerts"],
  ];

  return (
    <div className={`${cardBg} border ${border} rounded-2xl p-4`}>
      <p className={`text-xs font-semibold ${textPrimary} mb-3`}>Logging preferences</p>
      <div className="flex flex-col gap-2 mb-4">
        {items.map(([key, label]) => (
          <label key={key} className={`flex items-center justify-between ${inner} rounded-lg p-3 cursor-pointer`}>
            <span className={`text-xs ${textPrimary}`}>{label}</span>
            <input
              type="checkbox"
              checked={logs[key]}
              onChange={() => setLogs((prev) => ({ ...prev, [key]: !prev[key] }))}
            />
          </label>
        ))}
      </div>
      <button
        onClick={() => flashSaved("gps")}
        className={`text-xs font-semibold px-4 py-2 rounded-lg ${accentBg} ${accentTextOn}`}
      >
        Save settings
      </button>
      <SavedBadge show={savedFlash === "gps"} />
    </div>
  );
}

/* ---------- Section 5: System Information ---------- */

function SystemInfo({ cardBg, border, textMuted, textPrimary, inner }) {
  return (
    <div className={`${cardBg} border ${border} rounded-2xl p-4`}>
      <p className={`text-xs font-semibold ${textPrimary} mb-3`}>System information</p>
      <div className="grid grid-cols-2 gap-3 mb-4">
        {[
          ["Model version", "yolo-tea-v3.2"],
          ["Dashboard version", "1.0.0-prototype"],
          ["Database type", "Local mock data"],
          ["Last updated", "2026-08-31 14:32"],
        ].map(([label, value]) => (
          <div key={label} className={`${inner} rounded-lg p-2.5`}>
            <p className={`text-[10px] ${textMuted}`}>{label}</p>
            <p className={`text-xs font-semibold ${textPrimary}`}>{value}</p>
          </div>
        ))}
      </div>
      <div className="flex flex-wrap gap-2">
        <button onClick={() => alert("Checking for updates...")} className={`text-xs font-semibold px-4 py-2 rounded-lg border ${border} ${textPrimary}`}>
          Check for updates
        </button>
        <button onClick={() => alert("Would open system logs")} className={`text-xs font-semibold px-4 py-2 rounded-lg border ${border} ${textPrimary}`}>
          System logs
        </button>
        <button onClick={() => alert("TeaDrone — AI-Driven Precision Spraying, Component 1")} className={`text-xs font-semibold px-4 py-2 rounded-lg border ${border} ${textPrimary}`}>
          About
        </button>
      </div>
    </div>
  );
}