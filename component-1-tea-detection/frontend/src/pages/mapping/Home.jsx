import { useTheme } from "../../context/ThemeContext";

export default function MappingHome() {
  const { isDark } = useTheme();
  const cardBg = isDark ? "bg-surface" : "bg-light-surface";
  const border = isDark ? "border-border" : "border-light-border";
  const textMuted = isDark ? "text-muted" : "text-light-muted";
  const textPrimary = isDark ? "text-white" : "text-light-text";
  const inner = isDark ? "bg-ink" : "bg-light-bg";
  const accentBg = isDark ? "bg-accent" : "bg-light-primary";
  const accentTextOn = isDark ? "text-ink" : "text-white";
  const accentText = isDark ? "text-accent" : "text-light-primary";

  const missions = [
    { id: "MSN-0231", date: "2026-08-24", area: "4.6 ha", status: "COMPLETE" },
    { id: "MSN-0228", date: "2026-08-19", area: "2.1 ha", status: "ABORTED" },
    { id: "MSN-0224", date: "2026-08-11", area: "5.8 ha", status: "COMPLETE" },
    { id: "MSN-0219", date: "2026-08-02", area: "1.4 ha", status: "PENDING" },
  ];

  const statusColor = {
    COMPLETE: isDark ? "text-accent" : "text-light-primary",
    ABORTED: "text-red-500",
    PENDING: "text-amber-500",
  };

  return (
    <div className="flex flex-col gap-4">
      <div>
        <p className={`text-[10px] ${textMuted} uppercase tracking-wider`}>Component 3 — Tea Maturity Control</p>
        <h1 className={`text-2xl font-bold ${textPrimary}`}>TeaDrone</h1>
      </div>

      <div className="flex flex-wrap gap-2">
        <span className={`text-[10px] ${cardBg} border ${border} rounded-full px-3 py-1.5 flex items-center gap-1.5`}>
          <span className={`w-1.5 h-1.5 rounded-full ${accentBg}`} /> <span className={textMuted}>DRONE CONNECTED</span>
        </span>
        <span className={`text-[10px] ${cardBg} border ${border} rounded-full px-3 py-1.5 flex items-center gap-1.5`}>
          <span className={`w-1.5 h-1.5 rounded-full ${accentBg}`} /> <span className={textMuted}>RTK-GPS FIXED · 1.4 CM</span>
        </span>
        <span className={`text-[10px] ${cardBg} border ${border} rounded-full px-3 py-1.5 flex items-center gap-1.5`}>
          <span className={`w-1.5 h-1.5 rounded-full ${accentBg}`} /> <span className={textMuted}>BATTERY 92%</span>
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className={`lg:col-span-2 ${cardBg} border ${border} rounded-2xl p-4`}>
          <div className="flex items-center justify-between mb-2">
            <div>
              <p className={`text-[10px] ${textMuted}`}>Selected field</p>
              <p className={`text-sm font-semibold ${textPrimary}`}>Nuwara Estate — Block 7</p>
            </div>
            <span className={`text-[10px] ${inner} rounded-full px-3 py-1.5 ${textMuted}`}>4.6 ha · 96 row segments</span>
          </div>
          <div className={`relative ${inner} rounded-xl h-64 border border-dashed ${border} overflow-hidden`}>
            <svg viewBox="0 0 100 60" className="absolute inset-0 w-full h-full">
              <path
                d="M6,10 L94,10 L94,24 L6,24 L6,38 L94,38 L94,52 L6,52"
                fill="none"
                stroke={isDark ? "#C6F135" : "#2F5233"}
                strokeWidth="0.5"
                strokeDasharray="1.2,1.2"
                opacity="0.7"
              />
            </svg>
          </div>
          <div className="grid grid-cols-4 gap-3 mt-3">
            {[["Satellites", "21"], ["Wind", "4.2 m/s"], ["Tank level", "96%"], ["Last Pass 1", "24 Aug"]].map(([l, v]) => (
              <div key={l} className={`${inner} rounded-lg p-2.5`}>
                <p className={`text-[9px] ${textMuted} uppercase`}>{l}</p>
                <p className={`text-sm font-semibold ${textPrimary}`}>{v}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="flex flex-col gap-4">
          <div className={`${cardBg} border ${border} rounded-2xl p-4`}>
            <p className={`text-xs font-semibold ${textPrimary} mb-3`}>Two-pass workflow</p>
            <div className="flex items-start gap-2 mb-2">
              <span className={`text-[9px] font-semibold ${inner} rounded-full px-2 py-1 ${textMuted}`}>PASS 1</span>
              <p className={`text-[11px] ${textMuted}`}>Mapping & Maturity Classification — Young / Medium / Old</p>
            </div>
            <div className="flex items-start gap-2 mb-4">
              <span className={`text-[9px] font-semibold ${inner} rounded-full px-2 py-1 ${textMuted}`}>PASS 2</span>
              <p className={`text-[11px] ${textMuted}`}>Prescription-Guided Spray Flight with Live Safety Override</p>
            </div>
            <button className={`w-full py-3 rounded-full font-semibold text-sm ${accentBg} ${accentTextOn} mb-2`}>
              START MAPPING
            </button>
            <button className={`w-full py-3 rounded-full font-semibold text-sm border ${border} ${textPrimary}`}>
              VIEW PRESCRIPTION MAP
            </button>
          </div>
        </div>
      </div>

      <div className={`${cardBg} border ${border} rounded-2xl p-4`}>
        <div className="flex items-center justify-between mb-3">
          <p className={`text-xs font-semibold ${textPrimary}`}>Previous missions</p>
          <span className={`text-xs ${accentText}`}>View all</span>
        </div>
        {missions.map((m) => (
          <div key={m.id} className={`flex justify-between items-center py-2 border-b ${border} last:border-0`}>
            <div>
              <p className={`text-xs font-mono ${textPrimary}`}>{m.id}</p>
              <p className={`text-[10px] ${textMuted}`}>{m.date} · {m.area}</p>
            </div>
            <span className={`text-[10px] font-semibold ${statusColor[m.status]}`}>{m.status}</span>
          </div>
        ))}
      </div>
    </div>
  );
}