import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Brain, Grid3x3, Upload } from "lucide-react";
import useC4Styles from "./useC4Styles";
import { LEVELS, MATURITY_LABEL, getConfig, getHealth, getMetrics, listMissions } from "../api/c4";

const pct = (v) => (v == null ? "—" : `${(v * 100).toFixed(1)}%`);

export default function Home() {
  const s = useC4Styles();
  const [health, setHealth] = useState(null); // null = checking, false = API offline
  const [missions, setMissions] = useState([]);
  const [cfg, setCfg] = useState(null);
  const [best, setBest] = useState(null);

  useEffect(() => {
    getHealth().then(setHealth).catch(() => setHealth(false));
    listMissions().then(setMissions).catch(() => {});
    getConfig().then(setCfg).catch(() => {});
    getMetrics()
      .then((m) => setBest([...m.models].sort((a, b) => b.macro_f1 - a.macro_f1)[0] || null))
      .catch(() => {});
  }, []);

  const status =
    health === null ? ["bg-gray-500", "Checking…", ""]
    : health === false ? ["bg-red-500", "API offline", "Start it with: uvicorn api.server:app --port 8000"]
    : health.model_loaded ? [s.accentBg, "Model online", ""]
    : ["bg-amber-500", "Model not loaded", health.error];

  const regions = missions.reduce((n, m) => n + m.regions, 0);
  const toReview = missions.reduce((n, m) => n + m.needs_review, 0);

  const steps = [
    [Upload, "1 · Capture", "Upload the mapping-flight photos of a field block."],
    [Brain, "2 · Classify", "EfficientNet-B0 labels each photo Young, Medium or Mature."],
    [Grid3x3, "3 · Prescribe", "Rules turn maturity into Low / Normal / High spray levels."],
  ];

  return (
    <div className="flex flex-col gap-4">
      <div>
        <p className={`text-[10px] ${s.textMuted} uppercase tracking-wider`}>Component 4 · Maturity-driven variable-rate spraying</p>
        <h1 className={`text-2xl font-bold ${s.textPrimary}`}>Maturity & Spray Prescription</h1>
      </div>

      <div className="flex flex-wrap gap-2">
        <span title={status[2] || ""}
          className={`text-[10px] ${s.cardBg} border ${s.border} rounded-full px-3 py-1.5 flex items-center gap-1.5`}>
          <span className={`w-1.5 h-1.5 rounded-full ${status[0]}`} />
          <span className={s.textMuted}>{status[1].toUpperCase()}</span>
        </span>
        {best && (
          <span className={`text-[10px] ${s.cardBg} border ${s.border} rounded-full px-3 py-1.5 ${s.textMuted}`}>
            {best.model.toUpperCase()} · TEST F1 {pct(best.macro_f1)}
          </span>
        )}
      </div>
      {status[2] && <p className="text-[11px] text-amber-500">{status[2]}</p>}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className={`lg:col-span-2 ${s.cardBg} border ${s.border} rounded-2xl p-4`}>
          <p className={`text-xs font-semibold ${s.textPrimary} mb-3`}>How it works</p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
            {steps.map(([Icon, t, d]) => (
              <div key={t} className={`${s.inner} rounded-xl p-3`}>
                <Icon className={`w-4 h-4 mb-2 ${s.accentText}`} />
                <p className={`text-xs font-semibold ${s.textPrimary}`}>{t}</p>
                <p className={`text-[11px] ${s.textMuted}`}>{d}</p>
              </div>
            ))}
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[["Missions", missions.length], ["Regions mapped", regions], ["Needs review", toReview],
              ["Best accuracy", best ? pct(best.accuracy) : "—"]].map(([l, v]) => (
              <div key={l} className={`${s.inner} rounded-lg p-2.5`}>
                <p className={`text-[9px] ${s.textMuted} uppercase`}>{l}</p>
                <p className={`text-sm font-semibold ${s.textPrimary}`}>{v}</p>
              </div>
            ))}
          </div>
        </div>

        <div className={`${s.cardBg} border ${s.border} rounded-2xl p-4 flex flex-col`}>
          <p className={`text-xs font-semibold ${s.textPrimary} mb-3`}>Active spray rules</p>
          {cfg ? (
            <div className="flex flex-col gap-2 mb-3">
              {Object.entries(cfg.mapping).map(([m, lvl]) => (
                <div key={m} className={`${s.inner} rounded-lg px-3 py-2 flex items-center justify-between`}>
                  <span className={`text-xs ${s.textPrimary}`}>{MATURITY_LABEL[m] || m}</span>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full text-white" style={{ background: LEVELS[lvl].color }}>
                    {LEVELS[lvl].label.toUpperCase()} ×{cfg.rate_multiplier[lvl]}
                  </span>
                </div>
              ))}
              <p className={`text-[10px] ${s.textMuted}`}>
                Below {Math.round(cfg.confidence_threshold * 100)}% confidence → {LEVELS[cfg.low_confidence_level].label} + review
              </p>
            </div>
          ) : (
            <p className={`text-xs ${s.textMuted} mb-3`}>—</p>
          )}
          <div className="mt-auto flex flex-col gap-2">
            <Link to="/prescription" className={`w-full py-3 rounded-full font-semibold text-sm text-center ${s.accentBg} ${s.accentTextOn}`}>
              START MAPPING
            </Link>
            <Link to="/settings" className={`w-full py-2.5 rounded-full font-semibold text-xs text-center border ${s.border} ${s.textPrimary}`}>
              Edit rules
            </Link>
          </div>
        </div>
      </div>

      <div className={`${s.cardBg} border ${s.border} rounded-2xl p-4`}>
        <div className="flex items-center justify-between mb-3">
          <p className={`text-xs font-semibold ${s.textPrimary}`}>Recent missions</p>
          <Link to="/missions" className={`text-xs ${s.accentText} flex items-center gap-1`}>View all <ArrowRight className="w-3 h-3" /></Link>
        </div>
        {missions.length === 0 && <p className={`text-[11px] ${s.textMuted}`}>No missions yet — start one with <b>Start mapping</b>.</p>}
        {missions.slice(0, 4).map((m) => (
          <Link key={m.mission_id} to={`/prescription?mission=${m.mission_id}`}
            className={`flex justify-between items-center py-2 border-b ${s.border} last:border-0`}>
            <div>
              <p className={`text-xs font-mono ${s.textPrimary}`}>{m.mission_id}</p>
              <p className={`text-[10px] ${s.textMuted}`}>{m.generated_at.slice(0, 10)} · {m.field} · {m.regions} regions</p>
            </div>
            <div className="flex items-center gap-3">
              <div className="hidden sm:flex h-1.5 w-28 rounded-full overflow-hidden">
                {Object.entries(LEVELS).map(([k, l]) => (
                  <div key={k} style={{ width: `${(m.by_level[k] / m.regions) * 100}%`, background: l.color }} />
                ))}
              </div>
              <span className={`text-[10px] font-semibold ${m.needs_review ? "text-amber-500" : s.accentText}`}>
                {m.needs_review ? `${m.needs_review} TO REVIEW` : "COMPLETE"}
              </span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
