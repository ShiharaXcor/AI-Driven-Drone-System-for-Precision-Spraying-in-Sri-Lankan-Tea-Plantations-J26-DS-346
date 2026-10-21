import { useState, useMemo } from "react";
import { useTheme } from "../../context/ThemeContext";

const LEVELS = {
  L: { label: "Low", maturity: "Young", color: "#4ADE80" },
  N: { label: "Normal", maturity: "Medium", color: "#FBBF24" },
  H: { label: "High", maturity: "Old", color: "#F87171" },
  O: { label: "Off", maturity: "No tea", color: "#9CA3AF" },
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

const FLIGHT_PATH_D = "M6,10 L94,10 L94,24 L6,24 L6,38 L94,38 L94,52 L6,52";

export default function Flight() {
  const { isDark } = useTheme();
  const [spraying, setSpraying] = useState(true);
  const grid = useMemo(() => generateGrid(7, 12), []);
  const current = LEVELS.N;

  const cardBg = isDark ? "bg-surface" : "bg-light-surface";
  const border = isDark ? "border-border" : "border-light-border";
  const textMuted = isDark ? "text-muted" : "text-light-muted";
  const textPrimary = isDark ? "text-white" : "text-light-text";
  const inner = isDark ? "bg-ink" : "bg-light-bg";
  const accent = isDark ? "#C6F135" : "#2F5233";

  return (
    <div className={`${cardBg} border ${border} rounded-2xl p-4 relative overflow-hidden`}>
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <div>
          <p className={`text-[10px] ${textMuted}`}>Pass 2 · Prescription-guided</p>
          <p className={`text-sm font-semibold ${textPrimary}`}>TeaDrone</p>
        </div>
        <div className="flex items-center gap-4">
          {[["Altitude", "2.5 m"], ["Speed", "3.4 m/s"], ["Distance", "115 m"], ["Battery", "85%"], ["Tank", "92%"], ["Heading", "90°"]].map(([l, v]) => (
            <div key={l} className="text-right">
              <p className={`text-[9px] ${textMuted} uppercase`}>{l}</p>
              <p className={`text-xs font-semibold ${textPrimary}`}>{v}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="relative">
        <div className={`grid grid-cols-12 gap-1.5 ${inner} rounded-xl p-3`}>
          {grid.map((zone) => (
            <div key={zone.id} className="aspect-square rounded-sm" style={{ background: LEVELS[zone.key].color }} />
          ))}
        </div>

        <svg viewBox="0 0 100 60" preserveAspectRatio="none" className="absolute inset-0 w-full h-full pointer-events-none">
          <path d={FLIGHT_PATH_D} fill="none" stroke={accent} strokeWidth="0.6" strokeDasharray="1.5,1.5" opacity="0.9" />
          <polygon points="0,-1.6 2.6,1.6 0,0.6 -2.6,1.6" fill={accent}>
            <animateMotion dur="10s" repeatCount="indefinite" rotate="auto">
              <mpath href="#flight-path-mat" />
            </animateMotion>
          </polygon>
          <path id="flight-path-mat" d={FLIGHT_PATH_D} fill="none" opacity="0" />
        </svg>

        <div className={`absolute bottom-0 right-0 ${cardBg} border ${border} rounded-xl p-2.5 flex flex-col gap-1.5 m-2`}>
          {Object.values(LEVELS).map((l) => (
            <div key={l.maturity} className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full" style={{ background: l.color }} />
              <span className={`text-[10px] ${textMuted}`}>{l.label.toUpperCase()} — {l.maturity.toUpperCase()}</span>
            </div>
          ))}
        </div>

        <div className={`absolute top-2 left-2 w-64 ${cardBg} border ${border} rounded-xl p-4`}>
          <div className="flex items-center justify-between mb-2">
            <p className={`text-[10px] ${textMuted}`}>Current zone</p>
            <span className={`text-[9px] ${inner} rounded-full px-2 py-1 ${textMuted}`}>Row segment</span>
          </div>
          <p className={`text-lg font-semibold ${textPrimary} mb-2`}>Zone A-7</p>

          <div className="grid grid-cols-2 gap-2 mb-3">
            <div>
              <p className={`text-[9px] ${textMuted}`}>Maturity</p>
              <p className={`text-xs font-semibold ${textPrimary}`}>{current.maturity}</p>
            </div>
            <div>
              <p className={`text-[9px] ${textMuted}`}>Spray level</p>
              <p className="text-xs font-semibold" style={{ color: current.color }}>{current.label.toUpperCase()}</p>
            </div>
            <div>
              <p className={`text-[9px] ${textMuted}`}>Flow rate</p>
              <p className={`text-xs font-semibold ${textPrimary}`}>1.63 L/min</p>
            </div>
            <div>
              <p className={`text-[9px] ${textMuted}`}>Pump (PWM)</p>
              <p className="text-xs font-semibold" style={{ color: accent }}>{spraying ? "ON · 65%" : "OFF"}</p>
            </div>
          </div>

          <div className="flex justify-between mb-1">
            <span className={`text-[9px] ${textMuted}`}>Coverage</span>
            <span className={`text-[9px] font-semibold ${textPrimary}`}>6%</span>
          </div>
          <div className={`h-1.5 ${inner} rounded-full mb-3`}>
            <div className="h-full rounded-full" style={{ width: "6%", background: current.color }} />
          </div>

          <div className="flex gap-2">
            <button onClick={() => setSpraying(true)} className={`flex-1 py-2 rounded-full text-xs font-semibold border ${border} ${textPrimary}`}>Hold</button>
            <button onClick={() => setSpraying(false)} className="flex-1 py-2 rounded-full text-xs font-semibold bg-red-500 text-white">Stop Spray</button>
          </div>
        </div>
      </div>
    </div>
  );
}