import { useEffect, useState } from "react";
import useC4Styles from "./useC4Styles";
import { MATURITY_LABEL, getMetrics } from "../api/c4";

const pct = (v) => (v == null ? "—" : `${(v * 100).toFixed(1)}%`);
const NAMES = { efficientnet_b0: "EfficientNet-B0", mobilenetv3_large_100: "MobileNetV3-Large" };

function ConfusionMatrix({ s, model }) {
  const cm = model.confusion_matrix;
  const classes = Object.keys(model.per_class);
  const max = Math.max(...cm.flat());
  return (
    <div>
      <div className="grid gap-1" style={{ gridTemplateColumns: `72px repeat(${classes.length}, 1fr)` }}>
        <span />
        {classes.map((c) => (
          <span key={c} className={`text-[9px] ${s.textMuted} text-center uppercase`}>{MATURITY_LABEL[c] || c}</span>
        ))}
        {cm.map((row, i) => (
          <div key={i} className="contents">
            <span className={`text-[9px] ${s.textMuted} uppercase self-center`}>{MATURITY_LABEL[classes[i]] || classes[i]}</span>
            {row.map((v, j) => {
              const a = max ? v / max : 0;
              return (
                <div key={j} className="h-11 rounded-md flex items-center justify-center text-xs font-semibold"
                  style={{
                    background: i === j ? `rgba(74,222,128,${0.15 + a * 0.75})` : v ? `rgba(248,113,113,${0.15 + a * 0.6})` : "transparent",
                    color: a > 0.55 ? "#0D0E10" : undefined,
                  }}>
                  <span className={a > 0.55 ? "" : s.textPrimary}>{v}</span>
                </div>
              );
            })}
          </div>
        ))}
      </div>
      <p className={`text-[9px] ${s.textMuted} mt-2`}>Rows = actual class · columns = predicted · test set (unseen photos)</p>
    </div>
  );
}

function Bar({ s, label, r }) {
  const parts = [
    ["correct_pct", "Correct", "#4ADE80"],
    ["over_spray_pct", "Over-spray", "#F87171"],
    ["under_spray_pct", "Under-spray", "#FBBF24"],
  ];
  return (
    <div className="mb-3">
      <div className="flex justify-between mb-1">
        <p className={`text-xs ${s.textPrimary}`}>{label}</p>
        <p className={`text-[10px] ${s.textMuted}`}>chemical ×{Number(r.relative_chemical_use).toFixed(2)}</p>
      </div>
      <div className="flex h-6 rounded-md overflow-hidden">
        {parts.map(([k, name, c]) => (
          <div key={k} title={`${name} ${r[k]}%`} style={{ width: `${r[k]}%`, background: c }}
            className="flex items-center justify-center text-[10px] font-semibold text-[#0D0E10]">
            {r[k] >= 8 ? `${Math.round(r[k])}%` : ""}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function Model() {
  const s = useC4Styles();
  const [m, setM] = useState(null);
  const [error, setError] = useState("");
  const [pick, setPick] = useState(0);

  useEffect(() => {
    getMetrics().then(setM).catch((e) => setError(e.message));
  }, []);

  const header = (
    <div>
      <p className={`text-[10px] ${s.textMuted} uppercase tracking-wider`}>Function 1 & 2 evaluation · test set</p>
      <h1 className={`text-xl font-bold ${s.textPrimary}`}>Model Performance</h1>
    </div>
  );

  if (error || !m) {
    return <div className="flex flex-col gap-4">{header}
      <p className={`text-xs ${error ? "text-red-500" : s.textMuted}`}>{error || "Loading…"}</p></div>;
  }
  if (!m.models.length) {
    return <div className="flex flex-col gap-4">{header}
      <p className={`text-xs ${s.textMuted}`}>No training results found. Copy the <code>runs/</code> folder from Google Drive
        (<code>C4_data/runs</code>) into <code>component4_maturity_engine/runs/</code>.</p></div>;
  }

  const models = [...m.models].sort((a, b) => b.macro_f1 - a.macro_f1);
  const sel = models[Math.min(pick, models.length - 1)];
  const cmp = m.baseline_comparison;

  return (
    <div className="flex flex-col gap-4">
      {header}

      <div className={`${s.cardBg} border ${s.border} rounded-2xl p-4 overflow-x-auto`}>
        <p className={`text-xs font-semibold ${s.textPrimary} mb-3`}>Model comparison</p>
        <table className="w-full text-xs">
          <thead>
            <tr className={`border-b ${s.border}`}>
              {["Model", "Accuracy", "Precision", "Recall", "Macro-F1", "Young recall", "Latency", "Test photos"].map((h) => (
                <th key={h} className={`p-2 text-left font-semibold ${s.textMuted}`}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {models.map((r, i) => (
              <tr key={r.run} onClick={() => setPick(i)}
                className={`border-b ${s.border} last:border-0 cursor-pointer ${i === pick ? s.inner : ""}`}>
                <td className={`p-2 font-semibold ${s.textPrimary}`}>
                  {NAMES[r.model] || r.model} {i === 0 && <span className={`text-[9px] ml-1 ${s.accentText}`}>BEST</span>}
                </td>
                <td className={`p-2 ${s.textPrimary}`}>{pct(r.accuracy)}</td>
                <td className={`p-2 ${s.textPrimary}`}>{pct(r.macro_precision)}</td>
                <td className={`p-2 ${s.textPrimary}`}>{pct(r.macro_recall)}</td>
                <td className={`p-2 font-semibold ${s.textPrimary}`}>{pct(r.macro_f1)}</td>
                <td className={`p-2 ${s.textPrimary}`}>{pct(r.per_class?.young?.recall)}</td>
                <td className={`p-2 ${s.textPrimary}`}>{r.latency_ms_per_tile} ms</td>
                <td className={`p-2 ${s.textMuted}`}>{r.test_tiles}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className={`text-[10px] ${s.textMuted} mt-2`}>Latency measured on {models[0].device}. Click a row to see its confusion matrix.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className={`${s.cardBg} border ${s.border} rounded-2xl p-4`}>
          <p className={`text-xs font-semibold ${s.textPrimary} mb-3`}>Confusion matrix — {NAMES[sel.model] || sel.model}</p>
          <ConfusionMatrix s={s} model={sel} />
          <div className="grid grid-cols-3 gap-2 mt-3">
            {Object.entries(sel.per_class).map(([c, v]) => (
              <div key={c} className={`${s.inner} rounded-lg p-2.5`}>
                <p className={`text-[9px] ${s.textMuted} uppercase`}>{MATURITY_LABEL[c] || c} F1</p>
                <p className={`text-sm font-semibold ${s.textPrimary}`}>{pct(v.f1)}</p>
                <p className={`text-[9px] ${s.textMuted}`}>{v.support} photos</p>
              </div>
            ))}
          </div>
        </div>

        <div className={`${s.cardBg} border ${s.border} rounded-2xl p-4`}>
          <p className={`text-xs font-semibold ${s.textPrimary} mb-1`}>Adaptive engine vs fixed-rate spraying</p>
          <p className={`text-[10px] ${s.textMuted} mb-4`}>
            Spray level applied to each test photo compared with the level its true maturity needs.
          </p>
          {cmp ? (
            <>
              <Bar s={s} label="Fixed-rate (conventional)" r={cmp.fixed_rate_baseline} />
              <Bar s={s} label="Adaptive (Component 4)" r={cmp.adaptive_engine} />
              <div className="flex gap-3 flex-wrap mt-1 mb-3">
                {[["Correct", "#4ADE80"], ["Over-spray", "#F87171"], ["Under-spray", "#FBBF24"]].map(([n, c]) => (
                  <span key={n} className="flex items-center gap-1.5 text-[10px]">
                    <span className="w-2 h-2 rounded-full" style={{ background: c }} /><span className={s.textMuted}>{n}</span>
                  </span>
                ))}
              </div>
              <p className={`text-[10px] ${s.textMuted}`}>
                {cmp.flagged_for_review} photos below the {Math.round(cmp.confidence_threshold * 100)}% confidence threshold
                were flagged for review. Chemical use relies on placeholder rates.
              </p>
            </>
          ) : (
            <p className={`text-xs ${s.textMuted}`}>Run notebook section 8 and copy <code>baseline_comparison/</code> into the run folder.</p>
          )}
        </div>
      </div>
    </div>
  );
}
