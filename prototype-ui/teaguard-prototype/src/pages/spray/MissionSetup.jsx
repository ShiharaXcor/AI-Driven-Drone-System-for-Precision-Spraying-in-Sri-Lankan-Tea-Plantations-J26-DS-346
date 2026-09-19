import { useTheme } from "../../context/ThemeContext";

function TopBar({ isDark, cardBg, border, textMuted, textPrimary }) {
  return (
    <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
      <div className="flex gap-4 flex-wrap">
        {[["MISSION", "Tea Estate Block A"], ["DRONE", "UAV-01"], ["MODE", "Wind Compensation"]].map(([l, v]) => (
          <span key={l} className={`text-[10px] ${textMuted}`}>
            {l} <span className={`font-semibold ${textPrimary}`}>{v}</span>
          </span>
        ))}
        <span className={`text-[10px] ${textMuted}`}>
          STATUS <span className={`font-semibold ${isDark ? "text-accent" : "text-light-primary"}`}>Simulated</span>
        </span>
      </div>
      <span className="text-[9px] font-semibold px-2.5 py-1 rounded-full bg-amber-500/15 text-amber-500">
        SIMULATION MODE — Projected Output
      </span>
    </div>
  );
}

export default function MissionSetup() {
  const { isDark } = useTheme();
  const cardBg = isDark ? "bg-surface" : "bg-light-surface";
  const border = isDark ? "border-border" : "border-light-border";
  const textMuted = isDark ? "text-muted" : "text-light-muted";
  const textPrimary = isDark ? "text-white" : "text-light-text";
  const inner = isDark ? "bg-ink" : "bg-light-bg";
  const accent = isDark ? "#C6F135" : "#2F5233";
  const accentBg = isDark ? "bg-accent" : "bg-light-primary";
  const accentTextOn = isDark ? "text-ink" : "text-white";

  return (
    <div className="flex flex-col gap-3">
      <TopBar isDark={isDark} cardBg={cardBg} border={border} textMuted={textMuted} textPrimary={textPrimary} />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        <div className={`lg:col-span-2 ${cardBg} border ${border} rounded-2xl p-4`}>
          <p className={`text-[10px] ${textMuted} mb-2`}>Optimized Flight Path — Input from Path Optimization Component</p>
          <div className={`${inner} rounded-xl h-64`}>
            <svg viewBox="0 0 100 60" className="w-full h-full">
              <path
                d="M14,16 L80,16 L80,30 L14,30 L14,44 L80,44"
                fill="none"
                stroke={accent}
                strokeWidth="1"
              />
              {[[14, 16], [80, 16], [14, 30], [80, 30], [14, 44]].map(([x, y]) => (
                <circle key={`${x}-${y}`} cx={x} cy={y} r="1.6" fill={accent} />
              ))}
            </svg>
          </div>
          <button className={`w-full mt-3 py-3 rounded-full text-sm font-semibold ${accentBg} ${accentTextOn}`}>
            START WIND COMPENSATION
          </button>
        </div>

        <div className="flex flex-col gap-3">
          <div className={`${cardBg} border ${border} rounded-2xl p-4`}>
            <p className={`text-xs font-semibold ${textPrimary} mb-2`}>Wind conditions</p>
            {[["Wind speed", "4.2 m/s"], ["Direction", "72°"], ["Gust", "5.1 m/s"]].map(([l, v]) => (
              <div key={l} className="flex justify-between py-1">
                <span className={`text-[11px] ${textMuted}`}>{l}</span>
                <span className={`text-[11px] font-semibold ${textPrimary}`}>{v}</span>
              </div>
            ))}
            <div className="flex justify-between py-1">
              <span className={`text-[11px] ${textMuted}`}>Condition</span>
              <span className="text-[11px] font-semibold text-amber-500">Moderate</span>
            </div>
          </div>

          <div className={`${cardBg} border ${border} rounded-2xl p-4`}>
            <p className={`text-xs font-semibold ${textPrimary} mb-2`}>Drone telemetry</p>
            <div className="grid grid-cols-2 gap-2">
              {[["Altitude", "3.0 m"], ["Speed", "4.5 m/s"], ["Battery", "82%"], ["Payload", "68%"]].map(([l, v]) => (
                <div key={l} className={`${inner} rounded-lg p-2`}>
                  <p className={`text-[9px] ${textMuted}`}>{l}</p>
                  <p className={`text-sm font-semibold ${textPrimary}`}>{v}</p>
                </div>
              ))}
            </div>
            <div className={`flex justify-between mt-2 pt-2 border-t ${border}`}>
              <span className={`text-[10px] ${textMuted}`}>Spray status</span>
              <span className={`text-[10px] font-semibold ${isDark ? "text-accent" : "text-light-primary"}`}>ACTIVE</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}