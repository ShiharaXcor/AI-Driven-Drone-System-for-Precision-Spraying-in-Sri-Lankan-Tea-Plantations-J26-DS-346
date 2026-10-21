import { useTheme } from "../../context/ThemeContext";

export default function SprayCompensation() {
  const { isDark } = useTheme();
  const cardBg = isDark ? "bg-surface" : "bg-light-surface";
  const border = isDark ? "border-border" : "border-light-border";
  const textMuted = isDark ? "text-muted" : "text-light-muted";
  const textPrimary = isDark ? "text-white" : "text-light-text";
  const inner = isDark ? "bg-ink" : "bg-light-bg";
  const accent = isDark ? "#C6F135" : "#2F5233";
  const accentText = isDark ? "text-accent" : "text-light-primary";

  const rows = [
    ["Predicted drift", "1.24 m", "0.38 m"],
    ["Off-target deposition", "18%", "6%"],
    ["Nozzle angle", "0°", "+8.6°"],
    ["Target deposition", "82%", "94%"],
  ];

  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <div className={`${cardBg} border ${border} rounded-2xl p-4`}>
          <p className="text-xs font-semibold text-red-500 mb-2">Without compensation</p>
          <div className={`${inner} rounded-xl h-48`}>
            <svg viewBox="0 0 100 60" className="w-full h-full">
              <line x1="8" y1="8" x2="30" y2="8" stroke="#3b82f6" strokeWidth="0.8" />
              <polygon points="30,8 27,6.3 27,9.7" fill="#3b82f6" />
              <circle cx="45" cy="12" r="2" fill={isDark ? "#F5F6F5" : "#1E4620"} />
              <line x1="45" y1="14" x2="45" y2="34" stroke={isDark ? "#9497A0" : "#7A81A0"} strokeWidth="0.6" />
              <line x1="45" y1="34" x2="66" y2="52" stroke="#ef4444" strokeWidth="0.8" strokeDasharray="1,1" />
              <text x="60" y="55" fontSize="4" fill="#ef4444">✕</text>
              <text x="20" y="46" fontSize="3" fill={isDark ? "#9497A0" : "#7A81A0"}>OFF TARGET</text>
            </svg>
          </div>
        </div>

        <div className={`${cardBg} border ${border} rounded-2xl p-4`}>
          <p className={`text-xs font-semibold ${accentText} mb-2`}>With compensation</p>
          <div className={`${inner} rounded-xl h-48`}>
            <svg viewBox="0 0 100 60" className="w-full h-full">
              <line x1="8" y1="8" x2="30" y2="8" stroke="#3b82f6" strokeWidth="0.8" />
              <polygon points="30,8 27,6.3 27,9.7" fill="#3b82f6" />
              <circle cx="45" cy="12" r="2" fill={isDark ? "#F5F6F5" : "#1E4620"} />
              <line x1="45" y1="14" x2="38" y2="34" stroke={accent} strokeWidth="0.8" />
              <line x1="38" y1="34" x2="34" y2="50" stroke={accent} strokeWidth="0.8" />
              <circle cx="34" cy="52" r="1.6" fill="none" stroke={accent} strokeWidth="0.6" />
              <text x="26" y="46" fontSize="4" fill={accent}>✓</text>
              <text x="20" y="57" fontSize="3" fill={isDark ? "#9497A0" : "#7A81A0"}>ON TARGET</text>
            </svg>
          </div>
        </div>
      </div>

      <div className={`${cardBg} border ${border} rounded-2xl p-4`}>
        <table className="w-full text-xs">
          <thead>
            <tr className={`border-b ${border}`}>
              <th className={`p-2 text-left font-semibold ${textMuted}`}>Metric</th>
              <th className={`p-2 text-right font-semibold ${textMuted}`}>Without compensation</th>
              <th className={`p-2 text-right font-semibold ${accentText}`}>With compensation</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([m, a, b]) => (
              <tr key={m} className={`border-b ${border} last:border-0`}>
                <td className={`p-2 ${textPrimary}`}>{m}</td>
                <td className={`p-2 text-right ${textPrimary}`}>{a}</td>
                <td className={`p-2 text-right font-semibold ${accentText}`}>{b}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className={`text-[9px] ${textMuted} mt-2`}>All values simulated / projected</p>
      </div>

      <div className={`${isDark ? "bg-accent/10 border-accent/30" : "bg-light-primary/10 border-light-primary/30"} border rounded-2xl p-4`}>
        <p className={`text-xs ${accentText}`}>
          The drone maintains the flight path received from the Path Optimization component. Wind compensation is achieved by adjusting the spray and nozzle direction rather than modifying the drone's route.
        </p>
      </div>
    </div>
  );
}