import { useState } from "react";
import { useTheme } from "../../context/ThemeContext";

function Toggle({ value, onChange, disabled, accent, offBg }) {
  return (
    <button
      onClick={() => !disabled && onChange(!value)}
      disabled={disabled}
      className={`w-10 h-5 rounded-full relative transition disabled:opacity-70 ${value ? accent : offBg}`}
    >
      <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all ${value ? "left-5" : "left-0.5"}`} />
    </button>
  );
}

export default function Settings() {
  const { isDark } = useTheme();
  const [precharge, setPrecharge] = useState(true);
  const [feathering, setFeathering] = useState(true);
  const [autoResume, setAutoResume] = useState(false);

  const cardBg = isDark ? "bg-surface" : "bg-light-surface";
  const border = isDark ? "border-border" : "border-light-border";
  const textMuted = isDark ? "text-muted" : "text-light-muted";
  const textPrimary = isDark ? "text-white" : "text-light-text";
  const inner = isDark ? "bg-ink" : "bg-light-bg";
  const accentBg = isDark ? "bg-accent" : "bg-light-primary";

  return (
    <div className="flex flex-col gap-4">
      <div>
        <p className={`text-[10px] ${textMuted} uppercase tracking-wider`}>Simulation & control parameters</p>
        <h1 className={`text-xl font-bold ${textPrimary}`}>Settings</h1>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className={`${cardBg} border ${border} rounded-2xl p-4`}>
          <p className={`text-xs font-semibold ${textPrimary} mb-3`}>PWM-style spray control</p>
          <div className="grid grid-cols-3 gap-2 mb-4">
            <div className={`${inner} rounded-lg p-2.5`}>
              <p className={`text-[9px] ${textMuted}`}>LOW DUTY</p>
              <p className="text-sm font-semibold" style={{ color: "#4ADE80" }}>35%</p>
            </div>
            <div className={`${inner} rounded-lg p-2.5`}>
              <p className={`text-[9px] ${textMuted}`}>NORMAL DUTY</p>
              <p className="text-sm font-semibold" style={{ color: "#FBBF24" }}>65%</p>
            </div>
            <div className={`${inner} rounded-lg p-2.5`}>
              <p className={`text-[9px] ${textMuted}`}>HIGH DUTY</p>
              <p className="text-sm font-semibold" style={{ color: "#F87171" }}>95%</p>
            </div>
          </div>
          <div className={`flex items-center justify-between ${inner} rounded-lg p-3 mb-2`}>
            <div>
              <p className={`text-xs ${textPrimary}`}>Nozzle pre-charge</p>
              <p className={`text-[10px] ${textMuted}`}>Spin pump up 0.4s before entering a sprayed zone</p>
            </div>
            <Toggle value={precharge} onChange={setPrecharge} accent={accentBg} offBg="bg-gray-500" />
          </div>
          <div className={`flex items-center justify-between ${inner} rounded-lg p-3`}>
            <div>
              <p className={`text-xs ${textPrimary}`}>Zone edge feathering</p>
              <p className={`text-[10px] ${textMuted}`}>Ramp duty across row segment boundaries</p>
            </div>
            <Toggle value={feathering} onChange={setFeathering} accent={accentBg} offBg="bg-gray-500" />
          </div>
        </div>

        <div className={`${cardBg} border ${border} rounded-2xl p-4`}>
          <p className={`text-xs font-semibold ${textPrimary} mb-1`}>Live Safety Override</p>
          <p className={`text-[10px] ${textMuted} mb-3`}>Safety detection always has priority over the prescription map and cannot be disabled.</p>

          <div className={`flex items-center justify-between ${inner} rounded-lg p-3 mb-2`}>
            <div>
              <p className={`text-xs ${textPrimary}`}>Human detection</p>
              <p className={`text-[10px] ${textMuted}`}>Highest priority — pump OFF immediately</p>
            </div>
            <Toggle value={true} onChange={() => {}} disabled accent={accentBg} offBg="bg-gray-500" />
          </div>
          <div className={`flex items-center justify-between ${inner} rounded-lg p-3 mb-2`}>
            <div>
              <p className={`text-xs ${textPrimary}`}>Animal detection</p>
              <p className={`text-[10px] ${textMuted}`}>Pump OFF and hold position</p>
            </div>
            <Toggle value={true} onChange={() => {}} disabled accent={accentBg} offBg="bg-gray-500" />
          </div>
          <div className={`flex items-center justify-between ${inner} rounded-lg p-3`}>
            <div>
              <p className={`text-xs ${textPrimary}`}>Auto-resume after clear</p>
              <p className={`text-[10px] ${textMuted}`}>Requires operator confirmation</p>
            </div>
            <Toggle value={autoResume} onChange={setAutoResume} accent={accentBg} offBg="bg-gray-500" />
          </div>
        </div>

        <div className={`${cardBg} border ${border} rounded-2xl p-4`}>
          <p className={`text-xs font-semibold ${textPrimary} mb-3`}>Positioning</p>
          <div className="grid grid-cols-2 gap-2">
            <div className={`${inner} rounded-lg p-2.5`}>
              <p className={`text-[9px] ${textMuted}`}>Source</p>
              <p className={`text-sm font-semibold ${textPrimary}`}>RTK-GPS</p>
            </div>
            <div className={`${inner} rounded-lg p-2.5`}>
              <p className={`text-[9px] ${textMuted}`}>Base station</p>
              <p className={`text-sm font-semibold ${isDark ? "text-accent" : "text-light-primary"}`}>Online</p>
            </div>
            <div className={`${inner} rounded-lg p-2.5`}>
              <p className={`text-[9px] ${textMuted}`}>Accuracy</p>
              <p className={`text-sm font-semibold ${textPrimary}`}>1.4 cm</p>
            </div>
            <div className={`${inner} rounded-lg p-2.5`}>
              <p className={`text-[9px] ${textMuted}`}>Satellites</p>
              <p className={`text-sm font-semibold ${textPrimary}`}>22</p>
            </div>
          </div>
        </div>

        <div className={`${cardBg} border ${border} rounded-2xl p-4`}>
          <p className={`text-xs font-semibold ${textPrimary} mb-3`}>Flight profile</p>
          <div className="grid grid-cols-2 gap-2">
            <div className={`${inner} rounded-lg p-2.5`}>
              <p className={`text-[9px] ${textMuted}`}>Pass 1 altitude</p>
              <p className={`text-sm font-semibold ${textPrimary}`}>12 m</p>
            </div>
            <div className={`${inner} rounded-lg p-2.5`}>
              <p className={`text-[9px] ${textMuted}`}>Pass 2 altitude</p>
              <p className={`text-sm font-semibold ${textPrimary}`}>2.5 m</p>
            </div>
            <div className={`${inner} rounded-lg p-2.5`}>
              <p className={`text-[9px] ${textMuted}`}>Cruise speed</p>
              <p className={`text-sm font-semibold ${textPrimary}`}>4.5 m/s</p>
            </div>
            <div className={`${inner} rounded-lg p-2.5`}>
              <p className={`text-[9px] ${textMuted}`}>Spray speed</p>
              <p className={`text-sm font-semibold ${textPrimary}`}>3.6 m/s</p>
            </div>
          </div>
        </div>
      </div>

      <p className={`text-[10px] ${textMuted}`}>Prototype build — all telemetry is simulated for research demonstration. No drone hardware is connected.</p>
    </div>
  );
}