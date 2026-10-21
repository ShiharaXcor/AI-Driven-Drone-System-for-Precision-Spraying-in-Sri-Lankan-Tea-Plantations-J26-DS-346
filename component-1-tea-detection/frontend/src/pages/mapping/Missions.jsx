import { useTheme } from "../../context/ThemeContext";

const MISSIONS = [
  { date: "2026-08-24", id: "MSN-0231", field: "Nuwara Estate — Block 7", pass1: "COMPLETE", pass2: "COMPLETE", area: "4.6 ha", chemical: "18.4 L", safety: 1 },
  { date: "2026-08-19", id: "MSN-0228", field: "Nuwara Estate — Block 4", pass1: "COMPLETE", pass2: "ABORTED", area: "2.1 ha", chemical: "6.2 L", safety: 3 },
  { date: "2026-08-11", id: "MSN-0224", field: "Hantana Division — Block 2", pass1: "COMPLETE", pass2: "COMPLETE", area: "5.8 ha", chemical: "22.7 L", safety: 0 },
  { date: "2026-08-02", id: "MSN-0219", field: "Nuwara Estate — Block 7", pass1: "PARTIAL", pass2: "PENDING", area: "1.4 ha", chemical: "0.0 L", safety: 0 },
];

const STATUS_COLOR = {
  COMPLETE: { dark: "text-accent", light: "text-light-primary" },
  ABORTED: { dark: "text-red-400", light: "text-red-500" },
  PARTIAL: { dark: "text-amber-400", light: "text-amber-500" },
  PENDING: { dark: "text-amber-400", light: "text-amber-500" },
};

export default function Missions() {
  const { isDark } = useTheme();
  const cardBg = isDark ? "bg-surface" : "bg-light-surface";
  const border = isDark ? "border-border" : "border-light-border";
  const textMuted = isDark ? "text-muted" : "text-light-muted";
  const textPrimary = isDark ? "text-white" : "text-light-text";
  const accentBg = isDark ? "bg-accent" : "bg-light-primary";
  const accentTextOn = isDark ? "text-ink" : "text-white";

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <p className={`text-[10px] ${textMuted} uppercase tracking-wider`}>Two-pass spray records</p>
          <h1 className={`text-xl font-bold ${textPrimary}`}>Mission History</h1>
        </div>
        <button className={`text-xs font-semibold px-4 py-2 rounded-full ${accentBg} ${accentTextOn}`}>New mission</button>
      </div>

      <div className={`${cardBg} border ${border} rounded-2xl p-4 overflow-x-auto`}>
        <table className="w-full text-xs">
          <thead>
            <tr className={`border-b ${border}`}>
              {["Date", "Mission", "Field", "Pass 1 mapping", "Pass 2 spray", "Area", "Chemical", "Safety events"].map((h) => (
                <th key={h} className={`p-2 text-left font-semibold ${textMuted}`}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {MISSIONS.map((m) => (
              <tr key={m.id} className={`border-b ${border} last:border-0`}>
                <td className={`p-2 font-mono ${textMuted}`}>{m.date}</td>
                <td className={`p-2 font-semibold ${textPrimary}`}>{m.id}</td>
                <td className={`p-2 ${textPrimary}`}>{m.field}</td>
                <td className={`p-2 font-semibold ${isDark ? STATUS_COLOR[m.pass1].dark : STATUS_COLOR[m.pass1].light}`}>{m.pass1}</td>
                <td className={`p-2 font-semibold ${isDark ? STATUS_COLOR[m.pass2].dark : STATUS_COLOR[m.pass2].light}`}>{m.pass2}</td>
                <td className={`p-2 ${textPrimary}`}>{m.area}</td>
                <td className={`p-2 ${textPrimary}`}>{m.chemical}</td>
                <td className={`p-2 ${m.safety > 0 ? "text-red-500" : textPrimary} font-semibold`}>{m.safety}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex gap-2">
        <button className={`text-xs font-semibold px-4 py-2 rounded-full border ${border} ${textPrimary}`}>Open prescription map</button>
        <button className={`text-xs font-semibold px-4 py-2 rounded-full border ${border} ${textPrimary}`}>Latest mission report</button>
      </div>
    </div>
  );
}