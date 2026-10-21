import { useState, useMemo } from "react";
import { useTheme } from "../../context/ThemeContext";

const LEVELS = {
  L: { label: "Low", maturity: "Young", reason: "Young tea plant", flow: "0.9 L/min", pwm: "35%", color: "#4ADE80", swatch: "LOW — YOUNG" },
  N: { label: "Normal", maturity: "Medium", reason: "Medium maturity canopy — standard dosage", flow: "1.6 L/min", pwm: "65%", color: "#FBBF24", swatch: "NORMAL — MEDIUM" },
  H: { label: "High", maturity: "Old", reason: "Old tea plant — dense canopy", flow: "2.3 L/min", pwm: "95%", color: "#F87171", swatch: "HIGH — OLD" },
  O: { label: "Off", maturity: "No tea", reason: "No tea detected in this segment", flow: "0.0 L/min", pwm: "0%", color: "#9CA3AF", swatch: "OFF — NO TEA" },
};

function generateGrid(rows, cols) {
  const keys = ["L", "N", "N", "H", "O"];
  const grid = [];
  let id = 1;
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      grid.push({ id: `Zone A-${id}`, key: keys[Math.floor(Math.random() * keys.length)] });
      id++;
    }
  }
  return grid;
}

export default function Prescription() {
  const { isDark } = useTheme();
  const [selected, setSelected] = useState(null);
  const grid = useMemo(() => generateGrid(7, 12), []);

  const counts = useMemo(() => {
    const c = { L: 0, N: 0, H: 0, O: 0 };
    grid.forEach((z) => c[z.key]++);
    return c;
  }, [grid]);

  const cardBg = isDark ? "bg-surface" : "bg-light-surface";
  const border = isDark ? "border-border" : "border-light-border";
  const textMuted = isDark ? "text-muted" : "text-light-muted";
  const textPrimary = isDark ? "text-white" : "text-light-text";
  const inner = isDark ? "bg-ink" : "bg-light-bg";
  const accentBg = isDark ? "bg-accent" : "bg-light-primary";
  const accentTextOn = isDark ? "text-ink" : "text-white";

  const total = grid.length;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <p className={`text-[10px] ${textMuted} uppercase tracking-wider`}>Pass 2 input — spray level per row segment</p>
          <h1 className={`text-xl font-bold ${textPrimary}`}>Prescription Map</h1>
        </div>
        <div className="flex gap-2">
          {["L", "N", "H", "O"].map((k) => (
            <span key={k} className={`text-[10px] ${inner} rounded-full px-3 py-1.5 ${textMuted}`}>
              {LEVELS[k].maturity.toUpperCase()} {Math.round((counts[k] / total) * 100)}%
            </span>
          ))}
        </div>
      </div>

      <div className="flex gap-3 flex-wrap">
        {Object.values(LEVELS).map((l) => (
          <span key={l.swatch} className="flex items-center gap-1.5 text-[10px]">
            <span className="w-2 h-2 rounded-full" style={{ background: l.color }} /> <span className={textMuted}>{l.swatch}</span>
          </span>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className={`lg:col-span-2 ${cardBg} border ${border} rounded-2xl p-4`}>
          <div className={`grid grid-cols-12 gap-1.5 ${inner} rounded-xl p-3`}>
            {grid.map((zone) => (
              <button
                key={zone.id}
                onClick={() => setSelected(zone)}
                className={`aspect-square rounded-sm flex items-center justify-center text-[9px] font-bold text-white transition ${
                  selected?.id === zone.id ? "ring-2 ring-white" : "hover:opacity-80"
                }`}
                style={{ background: LEVELS[zone.key].color }}
              >
                {zone.key}
              </button>
            ))}
          </div>
        </div>

        <div className={`${cardBg} border ${border} rounded-2xl p-4`}>
          {!selected ? (
            <p className={`text-xs ${textMuted}`}>Click a row segment to view its prescription.</p>
          ) : (
            <div>
              <div className="flex items-center justify-between mb-3">
                <p className={`text-sm font-semibold ${textPrimary}`}>{selected.id}</p>
                <span className="text-[10px] font-bold px-2 py-1 rounded-full text-white" style={{ background: LEVELS[selected.key].color }}>
                  {LEVELS[selected.key].label.toUpperCase()}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-3 mb-3">
                <div className={`${inner} rounded-lg p-2.5`}>
                  <p className={`text-[9px] ${textMuted}`}>Maturity</p>
                  <p className={`text-sm font-semibold ${textPrimary}`}>{LEVELS[selected.key].maturity}</p>
                </div>
                <div className={`${inner} rounded-lg p-2.5`}>
                  <p className={`text-[9px] ${textMuted}`}>Spray level</p>
                  <p className="text-sm font-semibold" style={{ color: LEVELS[selected.key].color }}>{LEVELS[selected.key].label.toUpperCase()}</p>
                </div>
                <div className={`${inner} rounded-lg p-2.5`}>
                  <p className={`text-[9px] ${textMuted}`}>Estimated flow</p>
                  <p className={`text-sm font-semibold ${textPrimary}`}>{LEVELS[selected.key].flow}</p>
                </div>
                <div className={`${inner} rounded-lg p-2.5`}>
                  <p className={`text-[9px] ${textMuted}`}>PWM duty</p>
                  <p className={`text-sm font-semibold ${textPrimary}`}>{LEVELS[selected.key].pwm}</p>
                </div>
              </div>

              <div className={`${inner} rounded-lg p-2.5 mb-3`}>
                <p className={`text-[9px] ${textMuted} mb-1`}>Reason</p>
                <p className={`text-xs ${textPrimary}`}>{LEVELS[selected.key].reason}</p>
              </div>

              <div className="flex gap-2 mb-3">
                <button className={`flex-1 py-2 rounded-full text-xs font-semibold border ${border} ${textPrimary}`}>Review Map</button>
                <button className={`flex-1 py-2 rounded-full text-xs font-semibold border ${border} ${textPrimary}`}>Edit Zone</button>
              </div>

              <button className={`w-full py-2.5 rounded-full text-xs font-semibold border ${border} ${textPrimary} mb-2`}>Confirm Prescription</button>
              <button className={`w-full py-2.5 rounded-full text-xs font-semibold ${accentBg} ${accentTextOn}`}>START SPRAY FLIGHT</button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}