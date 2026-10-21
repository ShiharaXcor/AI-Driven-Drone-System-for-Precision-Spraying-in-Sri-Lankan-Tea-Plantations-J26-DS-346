import { useTheme } from "../../context/ThemeContext";

export default function Performance() {
  const { isDark } = useTheme();
  const cardBg = isDark ? "bg-surface" : "bg-light-surface";
  const border = isDark ? "border-border" : "border-light-border";
  const textMuted = isDark ? "text-muted" : "text-light-muted";
  const textPrimary = isDark ? "text-white" : "text-light-text";
  const inner = isDark ? "bg-ink" : "bg-light-bg";
  const accent = isDark ? "#C6F135" : "#2F5233";
  const accentText = isDark ? "text-accent" : "text-light-primary";
  const kpiBg = isDark ? "bg-accent/10 border-accent/30" : "bg-light-primary/10 border-light-primary/30";

  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <div className={`${cardBg} border ${border} rounded-2xl p-4`}>
          <p className={`text-xs font-semibold ${textPrimary} mb-2`}>Wind speed vs predicted drift</p>
          <svg viewBox="0 0 100 45" className="w-full h-24">
            <polyline points="5,38 25,30 45,20 65,10 85,4" fill="none" stroke="#ef4444" strokeWidth="1" />
            <polyline points="5,40 25,37 45,33 65,29 85,25" fill="none" stroke={accent} strokeWidth="1" />
          </svg>
          <div className="flex gap-3 text-[9px] mt-1">
            <span className="flex items-center gap-1"><span className="w-2 h-0.5 bg-red-500" /> <span className={textMuted}>Without</span></span>
            <span className="flex items-center gap-1"><span className="w-2 h-0.5" style={{ background: accent }} /> <span className={textMuted}>With</span></span>
          </div>
        </div>

        <div className={`${cardBg} border ${border} rounded-2xl p-4`}>
          <p className={`text-xs font-semibold ${textPrimary} mb-2`}>Wind speed vs required nozzle angle</p>
          <svg viewBox="0 0 100 45" className="w-full h-24">
            <polyline points="5,40 25,32 45,22 65,14 85,6" fill="none" stroke={accent} strokeWidth="1" />
          </svg>
          <p className={`text-[9px] ${textMuted}`}>Required angle increases with wind speed</p>
        </div>
      </div>

      <div className={`${cardBg} border ${border} rounded-2xl p-4`}>
        <p className={`text-xs font-semibold ${textPrimary} mb-3`}>Random Forest model performance</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-2">
          {["MAE", "RMSE", "R²", "Confidence"].map((m) => (
            <div key={m} className={`${inner} rounded-lg p-2.5 text-center`}>
              <p className={`text-[9px] ${textMuted}`}>{m}</p>
              <p className={`text-sm ${textMuted}`}>—</p>
            </div>
          ))}
        </div>
        <p className="text-[10px] text-amber-500">Awaiting trained model validation</p>
      </div>

      <div className={`${cardBg} border ${border} rounded-2xl p-4`}>
        <p className={`text-xs font-semibold ${textPrimary} mb-2`}>Feature importance</p>
        {[["Wind speed", 38], ["Wind direction", 26], ["Drone altitude", 18], ["Drone speed", 12], ["Drone heading", 6]].map(([f, v]) => (
          <div key={f} className="mb-2">
            <div className="flex justify-between mb-0.5">
              <span className={`text-[10px] ${textMuted}`}>{f}</span>
              <span className={`text-[10px] font-semibold ${textPrimary}`}>{v}%</span>
            </div>
            <div className={`h-1.5 ${inner} rounded-full`}>
              <div className="h-full rounded-full" style={{ width: `${v}%`, background: accent }} />
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {[["Drift reduction", "~69%"], ["Deposition improvement", "+12 pts"], ["Avg nozzle compensation", "6.4°"]].map(([l, v]) => (
          <div key={l} className={`${kpiBg} border rounded-2xl p-4 text-center`}>
            <p className={`text-[9px] font-semibold ${accentText} uppercase mb-1`}>{l}</p>
            <p className={`text-xl font-bold ${accentText}`}>{v}</p>
            <p className={`text-[9px] ${textMuted}`}>Projected</p>
          </div>
        ))}
      </div>
    </div>
  );
}