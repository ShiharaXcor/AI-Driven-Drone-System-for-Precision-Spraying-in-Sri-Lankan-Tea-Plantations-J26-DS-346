import { useEffect, useState } from "react";
import useC4Styles from "./useC4Styles";
import { LEVELS, MATURITY_LABEL, getConfig, saveConfig } from "../api/c4";

// Real, saved settings for Component 4 (maturity -> spray rules). Stored in
// component4_maturity_engine/configs/spray_mapping.yaml via the API.
function SprayRules({ cardBg, border, textMuted, textPrimary, inner, accentBg, isDark }) {
  const [cfg, setCfg] = useState(null);
  const [saved, setSaved] = useState(null);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    getConfig().then((c) => { setCfg(c); setSaved(c); }).catch((e) => setMsg(e.message));
  }, []);

  const dirty = cfg && JSON.stringify(cfg) !== JSON.stringify(saved);
  const set = (patch) => { setCfg({ ...cfg, ...patch }); setMsg(""); };

  async function save() {
    try {
      const c = await saveConfig({
        mapping: cfg.mapping,
        confidence_threshold: Number(cfg.confidence_threshold),
        low_confidence_level: cfg.low_confidence_level,
        rate_multiplier: Object.fromEntries(Object.entries(cfg.rate_multiplier).map(([k, v]) => [k, Number(v)])),
        normal_flow_l_min: Number(cfg.normal_flow_l_min),
      });
      setCfg(c); setSaved(c); setMsg("Saved — new missions use these rules.");
    } catch (e) {
      setMsg(e.message);
    }
  }

  const select = `${inner} border ${border} rounded-lg px-2 py-1.5 text-xs ${textPrimary} outline-none`;

  return (
    <div className={`${cardBg} border ${border} rounded-2xl p-4 lg:col-span-2`}>
      <div className="flex items-center justify-between mb-1">
        <p className={`text-xs font-semibold ${textPrimary}`}>Maturity → spray rules</p>
        <span className={`text-[9px] font-semibold rounded-full px-2 py-1 ${isDark ? "bg-accent/15 text-accent" : "bg-light-primary/10 text-light-primary"}`}>LIVE · SAVED TO ENGINE</span>
      </div>
      <p className={`text-[10px] ${textMuted} mb-3`}>
        Initial mapping from the proposal. Rates and flow are placeholders until validated with TRI.
      </p>
      {!cfg ? (
        <p className={`text-xs ${msg ? "text-red-500" : textMuted}`}>{msg || "Loading…"}</p>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mb-3">
            {Object.keys(cfg.mapping).map((m) => (
              <div key={m} className={`${inner} rounded-lg p-2.5 flex items-center justify-between gap-2`}>
                <span className={`text-xs ${textPrimary}`}>{MATURITY_LABEL[m] || m}</span>
                <select aria-label={`Spray level for ${m}`} className={select} value={cfg.mapping[m]}
                  onChange={(e) => set({ mapping: { ...cfg.mapping, [m]: e.target.value } })}>
                  {Object.entries(LEVELS).map(([k, l]) => <option key={k} value={k}>{l.label}</option>)}
                </select>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-3">
            {Object.entries(LEVELS).map(([k, l]) => (
              <div key={k} className={`${inner} rounded-lg p-2.5`}>
                <p className="text-[9px] uppercase" style={{ color: l.color }}>{l.label} rate ×</p>
                <input type="number" step="0.05" min="0" value={cfg.rate_multiplier[k]}
                  onChange={(e) => set({ rate_multiplier: { ...cfg.rate_multiplier, [k]: e.target.value } })}
                  className={`w-full bg-transparent text-sm font-semibold ${textPrimary} outline-none`} />
              </div>
            ))}
            <div className={`${inner} rounded-lg p-2.5`}>
              <p className={`text-[9px] ${textMuted} uppercase`}>Normal flow L/min</p>
              <input type="number" step="0.1" min="0" value={cfg.normal_flow_l_min}
                onChange={(e) => set({ normal_flow_l_min: e.target.value })}
                className={`w-full bg-transparent text-sm font-semibold ${textPrimary} outline-none`} />
            </div>
          </div>

          <div className={`${inner} rounded-lg p-3 mb-3`}>
            <div className="flex justify-between mb-1">
              <p className={`text-xs ${textPrimary}`}>Confidence threshold</p>
              <p className={`text-xs font-semibold ${textPrimary}`}>{Math.round(cfg.confidence_threshold * 100)}%</p>
            </div>
            <input type="range" min="0" max="1" step="0.05" value={cfg.confidence_threshold}
              onChange={(e) => set({ confidence_threshold: Number(e.target.value) })}
              className="w-full accent-current" style={{ color: isDark ? "#C6F135" : "#2F5233" }} />
            <div className="flex items-center justify-between gap-2 mt-2">
              <p className={`text-[10px] ${textMuted}`}>Below the threshold, regions are flagged for review and sprayed at</p>
              <select aria-label="Fallback level" className={select} value={cfg.low_confidence_level}
                onChange={(e) => set({ low_confidence_level: e.target.value })}>
                {Object.entries(LEVELS).map(([k, l]) => <option key={k} value={k}>{l.label}</option>)}
              </select>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button disabled={!dirty} onClick={save}
              className={`text-xs font-semibold px-4 py-2 rounded-full ${accentBg} ${isDark ? "text-ink" : "text-white"} disabled:opacity-40`}>
              Save rules
            </button>
            {dirty && <button onClick={() => { setCfg(saved); setMsg(""); }} className={`text-xs ${textMuted}`}>Discard</button>}
            {msg && <p className={`text-[11px] ${msg.startsWith("Saved") ? (isDark ? "text-accent" : "text-light-primary") : "text-red-500"}`}>{msg}</p>}
          </div>
        </>
      )}
    </div>
  );
}

export default function Settings() {
  const s = useC4Styles();
  return (
    <div className="flex flex-col gap-4">
      <div>
        <p className={`text-[10px] ${s.textMuted} uppercase tracking-wider`}>Function 2 · decision engine</p>
        <h1 className={`text-xl font-bold ${s.textPrimary}`}>Settings</h1>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <SprayRules {...s} />
      </div>
    </div>
  );
}
