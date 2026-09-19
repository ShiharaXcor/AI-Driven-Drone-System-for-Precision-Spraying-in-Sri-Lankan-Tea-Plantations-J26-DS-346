import { useTheme } from "../../context/ThemeContext";

export default function FlightAnalytics() {
  const { isDark } = useTheme();
  const cardBg = isDark ? "bg-surface" : "bg-light-surface";
  const border = isDark ? "border-border" : "border-light-border";
  const textMuted = isDark ? "text-muted" : "text-light-muted";
  const textPrimary = isDark ? "text-white" : "text-light-text";
  const inner = isDark ? "bg-ink" : "bg-light-bg";
  const accent = isDark ? "#C6F135" : "#2F5233";
  const accentText = isDark ? "text-accent" : "text-light-primary";

  const smartPoints = [100, 97, 95, 92, 88, 84, 78, 72, 65, 57];
  const traditionalPoints = [100, 78, 84, 62, 68, 55, 40, 22, 30, 5];

  const savings = [
    ["Flat sections sprayed first", 78, "+8.4%"],
    ["Steep climbs deferred", 65, "+4.2%"],
    ["Optimal cruise speed", 55, "+2.9%"],
    ["Fewer detours needed", 32, "+1.1%"],
  ];

  const obstacles = [
    ["🌳", "Shade tree", "Climbed 2 m over canopy", "2.1 m"],
    ["🌿", "Dense canopy", "Turned left 18°, resumed", "2.6 m"],
    ["🪵", "Branch", "Climbed 1.5 m to clear", "1.9 m"],
  ];

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className={`${cardBg} border ${border} rounded-2xl p-3`}>
          <p className={`text-[9px] ${textMuted} mb-1`}>vs traditional plan</p>
          <p className={`text-xl font-bold ${accentText}`}>&gt;15%</p>
          <p className={`text-[9px] ${textMuted}`}>Battery saved per mission</p>
        </div>
        <div className={`${cardBg} border ${border} rounded-2xl p-3`}>
          <p className={`text-[9px] ${textMuted} mb-1`}>Coverage</p>
          <p className={`text-xl font-bold ${textPrimary}`}>0.41 ha</p>
          <p className={`text-[9px] ${textMuted}`}>Area sprayed this mission</p>
        </div>
        <div className={`${cardBg} border ${border} rounded-2xl p-3`}>
          <p className={`text-[9px] ${textMuted} mb-1`}>Obstacles</p>
          <p className={`text-xl font-bold ${textPrimary}`}>3</p>
          <p className={`text-[9px] ${textMuted}`}>Avoided automatically</p>
        </div>
        <div className={`${cardBg} border ${border} rounded-2xl p-3`}>
          <p className={`text-[9px] ${textMuted} mb-1`}>Mission time</p>
          <p className={`text-xl font-bold ${textPrimary}`}>32m 45s</p>
          <p className={`text-[9px] ${textMuted}`}>Active spraying time</p>
        </div>
      </div>

      <div className={`${cardBg} border ${border} rounded-2xl p-4`}>
        <p className={`text-sm font-semibold ${textPrimary} mb-1`}>Battery consumption comparison — this mission</p>
        <p className={`text-[10px] ${textMuted} mb-3`}>How the smart routing system uses battery compared to the traditional fixed-path approach used before</p>
        <svg viewBox="0 0 100 45" className="w-full h-40">
          <polyline points={smartPoints.map((v, i) => `${(i / 9) * 100},${45 - (v / 100) * 42}`).join(" ")} fill="none" stroke={accent} strokeWidth="1" />
          <polyline points={traditionalPoints.map((v, i) => `${(i / 9) * 100},${45 - (v / 100) * 42}`).join(" ")} fill="none" stroke="#ef4444" strokeWidth="1" />
          <line x1="100" y1="0" x2="100" y2="45" stroke={accent} strokeWidth="0.3" strokeDasharray="0.5,0.5" />
        </svg>
        <div className="flex gap-4 text-[10px] mt-1">
          <span className="flex items-center gap-1"><span className="w-2 h-0.5 bg-red-500" /> <span className={textMuted}>Traditional 2D lawnmower route</span></span>
          <span className="flex items-center gap-1"><span className="w-2 h-0.5" style={{ background: accent }} /> <span className={textMuted}>Smart DRL routing — this mission</span></span>
          <span className={`ml-auto font-semibold ${accentText}`}>15% saved</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className={`${cardBg} border ${border} rounded-2xl p-4`}>
          <p className={`text-sm font-semibold ${textPrimary} mb-1`}>Obstacles avoided this mission</p>
          <p className={`text-[10px] ${textMuted} mb-3`}>Detected and avoided automatically by the depth sensor system</p>
          {obstacles.map(([icon, title, desc, dist]) => (
            <div key={title} className={`flex items-center justify-between py-2 border-b ${border} last:border-0`}>
              <div className="flex items-center gap-2">
                <span className={`w-8 h-8 rounded-lg ${inner} flex items-center justify-center text-sm`}>{icon}</span>
                <div>
                  <p className={`text-xs font-semibold ${textPrimary}`}>{title}</p>
                  <p className={`text-[9px] ${textMuted}`}>{desc}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className={`text-[10px] ${textMuted}`}>{dist}</span>
                <span className={`text-[9px] font-semibold px-2 py-0.5 rounded-full ${isDark ? "bg-accent/20 text-accent" : "bg-light-primary/15 text-light-primary"}`}>Avoided</span>
              </div>
            </div>
          ))}
        </div>

        <div className={`${cardBg} border ${border} rounded-2xl p-4`}>
          <p className={`text-sm font-semibold ${textPrimary} mb-1`}>Where the battery savings come from</p>
          <p className={`text-[10px] ${textMuted} mb-3`}>Smart routing saves energy by avoiding expensive manoeuvres</p>
          {savings.map(([label, pct, delta]) => (
            <div key={label} className="mb-2.5">
              <div className="flex justify-between mb-1">
                <span className={`text-[10px] ${textMuted}`}>{label}</span>
                <span className={`text-[10px] font-semibold ${accentText}`}>{delta}</span>
              </div>
              <div className={`h-4 ${inner} rounded-full overflow-hidden`}>
                <div className="h-full flex items-center px-2 text-[9px] font-semibold" style={{ width: `${pct}%`, background: accent, color: isDark ? "#0D0E10" : "#fff" }}>
                  {pct}%
                </div>
              </div>
            </div>
          ))}
          <div className={`${isDark ? "bg-accent/10 border-accent/30" : "bg-light-primary/10 border-light-primary/30"} border rounded-lg p-2.5 mt-3`}>
            <p className={`text-[10px] ${textPrimary}`}>
              Total <span className={`font-bold ${accentText}`}>16.6% battery saved</span> vs the traditional fixed-path approach — based on real flight records from 38 spray missions.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}