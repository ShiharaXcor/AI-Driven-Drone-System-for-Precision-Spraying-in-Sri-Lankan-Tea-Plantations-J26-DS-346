import { useState } from "react";
import { useTheme } from "../../context/ThemeContext";

export default function MissionPlanner() {
  const { isDark } = useTheme();
  const [payload, setPayload] = useState(20);
  const [flowRate, setFlowRate] = useState(2.5);

  const cardBg = isDark ? "bg-surface" : "bg-light-surface";
  const border = isDark ? "border-border" : "border-light-border";
  const textMuted = isDark ? "text-muted" : "text-light-muted";
  const textPrimary = isDark ? "text-white" : "text-light-text";
  const inner = isDark ? "bg-ink" : "bg-light-bg";
  const accent = isDark ? "#C6F135" : "#2F5233";
  const accentText = isDark ? "text-accent" : "text-light-primary";

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-4">
      {/* Left panel */}
      <div className="flex flex-col gap-3">
        <div>
          <h1 className={`text-lg font-bold ${textPrimary}`}>Mission Planner</h1>
          <p className={`text-[11px] ${textMuted}`}>Upload your estate map and configure the drone before launching a new spray mission.</p>
        </div>

        <div className={`${cardBg} border-2 border-dashed ${isDark ? "border-accent" : "border-light-primary"} rounded-2xl p-4 text-center`}>
          <p className="text-xl mb-2">🗺️</p>
          <p className={`text-xs font-semibold ${textPrimary} mb-1`}>Estate terrain map</p>
          <p className={`text-[9px] ${textMuted} mb-2`}>TIFF format — provided by estate or from survey drone</p>
          <span className={`text-[10px] font-semibold ${accentText}`}>✓ Ouvahkelle_Estate.tif loaded</span>
        </div>

        <div className={`${cardBg} border ${border} rounded-2xl p-4 text-center`}>
          <p className="text-xl mb-2">📍</p>
          <p className={`text-xs font-semibold ${textPrimary} mb-1`}>Estate boundary</p>
          <p className={`text-[9px] ${textMuted} mb-2`}>KML format — defines the spray zone perimeter</p>
          <button className={`text-[10px] font-semibold px-3 py-1.5 rounded-lg ${inner} ${textMuted}`}>Click to upload</button>
        </div>

        <div className={`${cardBg} border ${border} rounded-2xl p-4`}>
          <p className={`text-xs font-semibold ${textPrimary} mb-3`}>Drone Configuration</p>
          <div className="mb-4">
            <div className="flex justify-between mb-1">
              <span className={`text-[10px] ${textMuted}`}>Liquid payload capacity</span>
              <span className={`text-[10px] font-semibold ${textPrimary}`}>{payload} L</span>
            </div>
            <input type="range" min="5" max="30" value={payload} onChange={(e) => setPayload(e.target.value)} className="w-full" />
          </div>
          <div>
            <div className="flex justify-between mb-1">
              <span className={`text-[10px] ${textMuted}`}>Target spray flow rate</span>
              <span className={`text-[10px] font-semibold ${textPrimary}`}>{flowRate} L/min</span>
            </div>
            <input type="range" min="0.5" max="5" step="0.1" value={flowRate} onChange={(e) => setFlowRate(e.target.value)} className="w-full" />
          </div>
        </div>

        <div className="grid grid-cols-3 gap-2">
          <div className={`${cardBg} border ${border} rounded-xl p-2 text-center`}>
            <p className={`text-sm font-bold ${accentText}`}>42 min</p>
            <p className={`text-[8px] ${textMuted}`}>EST. FLIGHT TIME</p>
          </div>
          <div className={`${cardBg} border ${border} rounded-xl p-2 text-center`}>
            <p className={`text-sm font-bold ${accentText}`}>1.1 ha</p>
            <p className={`text-[8px] ${textMuted}`}>AREA TO COVER</p>
          </div>
          <div className={`${cardBg} border ${border} rounded-xl p-2 text-center`}>
            <p className={`text-sm font-bold ${accentText}`}>2 packs</p>
            <p className={`text-[8px] ${textMuted}`}>BATTERY SWAPS</p>
          </div>
        </div>
      </div>

      {/* Map */}
      <div className={`${cardBg} border ${border} rounded-2xl p-3`}>
        <div className={`${inner} border ${border} rounded-lg p-2.5 w-fit mb-2 flex gap-3 text-[10px]`}>
          <span className="flex items-center gap-1"><span className="w-3 h-0.5" style={{ background: accent }} /> <span className={textMuted}>Terrain contour</span></span>
          <span className="flex items-center gap-1"><span className={`w-2 h-2 rounded-full ${isDark ? "bg-accent" : "bg-light-primary"}`} /> <span className={textMuted}>Planned flight path</span></span>
          <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 bg-amber-500 rounded-sm" /> <span className={textMuted}>Steep slope — watch zone</span></span>
        </div>

        <div className={`relative ${inner} rounded-xl overflow-hidden min-h-[460px]`}>
          <svg viewBox="0 0 100 70" className="absolute inset-0 w-full h-full">
            {[10, 22, 34, 46, 58].map((y, i) => (
              <path key={i} d={`M0,${y} Q25,${y - 4} 50,${y} T100,${y - 2}`} stroke={accent} strokeWidth="0.3" fill="none" opacity="0.5" />
            ))}
            {[15, 32, 50, 68, 85].map((x, i) => (
              <line key={i} x1={x} y1="0" x2={x} y2="70" stroke={accent} strokeWidth="0.3" opacity="0.35" />
            ))}
            {/* watch zones */}
            <polygon points="68,28 78,20 82,32" fill="#f59e0b" fillOpacity="0.25" stroke="#f59e0b" strokeWidth="0.4" />
            <polygon points="86,18 94,12 96,22" fill="#f59e0b" fillOpacity="0.25" stroke="#f59e0b" strokeWidth="0.4" />
            {/* planned path (dotted) */}
            <path d="M8,58 Q30,50 45,44 T75,32 Q85,42 92,50" stroke={accent} strokeWidth="1" strokeDasharray="0.2,2" strokeLinecap="round" fill="none" />
            {/* drone start marker */}
            <circle cx="8" cy="58" r="2.5" fill="none" stroke={accent} strokeWidth="0.5" />
            <circle cx="8" cy="58" r="0.8" fill={accent} />
          </svg>
        </div>
      </div>
    </div>
  );
}