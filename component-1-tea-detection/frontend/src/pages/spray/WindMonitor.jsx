import { useState, useEffect } from "react";
import { useTheme } from "../../context/ThemeContext";

export default function WindMonitor() {
  const { isDark } = useTheme();
  const [windSpeed, setWindSpeed] = useState(4.2);
  const [windDir, setWindDir] = useState(72);
  const [altitude, setAltitude] = useState(3.0);
  const [speed, setSpeed] = useState(4.5);

  const cardBg = isDark ? "bg-surface" : "bg-light-surface";
  const border = isDark ? "border-border" : "border-light-border";
  const textMuted = isDark ? "text-muted" : "text-light-muted";
  const textPrimary = isDark ? "text-white" : "text-light-text";
  const inner = isDark ? "bg-ink" : "bg-light-bg";
  const accent = isDark ? "#C6F135" : "#2F5233";
  const accentText = isDark ? "text-accent" : "text-light-primary";

  const drift = (windSpeed * 0.28 + Math.abs(90 - windDir) * 0.002).toFixed(2);
  const nozzleAngle = (windSpeed * 2.0).toFixed(1);
  const confidence = Math.min(97, 78 + windSpeed).toFixed(0);

  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        <div className={`lg:col-span-2 ${cardBg} border ${border} rounded-2xl p-4`}>
          <p className={`text-[10px] ${textMuted} mb-2`}>Top-down drift visualization</p>
          <div className={`${inner} rounded-xl h-56 relative`}>
            <svg viewBox="0 0 100 60" className="w-full h-full">
              <line x1="10" y1="10" x2="55" y2="10" stroke="#3b82f6" strokeWidth="1" />
              <polygon points="55,10 51,7.5 51,12.5" fill="#3b82f6" />
              <text x="10" y="7" fontSize="3" fill="#3b82f6">WIND {windSpeed} m/s</text>
              <circle cx="45" cy="26" r="2.2" fill={accent} />
              <text x="49" y="27" fontSize="3" fill={isDark ? "#F5F6F5" : "#1E4620"}>UAV-01</text>
              <line x1="45" y1="28" x2="45" y2="42" stroke={isDark ? "#9497A0" : "#7A81A0"} strokeWidth="0.6" />
              <line x1="45" y1="42" x2={45 + Number(nozzleAngle) * 0.5} y2="52" stroke="#f59e0b" strokeWidth="1" strokeDasharray="1,1" />
              <text x="34" y="58" fontSize="3" fill={isDark ? "#9497A0" : "#7A81A0"}>TARGET AREA</text>
            </svg>
          </div>
        </div>

        <div className={`${cardBg} border ${border} rounded-2xl p-4`}>
          <div className="flex items-center justify-between mb-2">
            <p className={`text-xs font-semibold ${textPrimary}`}>Random Forest Drift Prediction</p>
            <span className="text-[8px] font-semibold px-2 py-1 rounded-full bg-amber-500/15 text-amber-500">SIMULATED</span>
          </div>
          <p className={`text-[10px] ${textMuted} leading-relaxed mb-2`}>
            Wind speed {windSpeed} m/s · Direction {windDir}°<br />
            Altitude {altitude} m · Speed {speed} m/s
          </p>
          <p className={`text-[9px] ${textMuted}`}>Predicted drift</p>
          <p className={`text-2xl font-bold ${accentText} mb-2`}>{drift} m</p>
          <p className={`text-[9px] ${textMuted}`}>Confidence</p>
          <p className={`text-lg font-semibold ${textPrimary}`}>{confidence}%</p>
        </div>
      </div>

      {/* Interactive controls */}
      <div className={`${cardBg} border ${border} rounded-2xl p-4`}>
        <p className={`text-xs font-semibold ${textPrimary} mb-3`}>Adjust conditions</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            ["Wind speed (m/s)", windSpeed, setWindSpeed, 0, 15, 0.1],
            ["Wind direction (°)", windDir, setWindDir, 0, 360, 1],
            ["Altitude (m)", altitude, setAltitude, 1, 10, 0.1],
            ["Drone speed (m/s)", speed, setSpeed, 1, 10, 0.1],
          ].map(([label, value, setter, min, max, step]) => (
            <div key={label}>
              <div className="flex justify-between mb-1">
                <span className={`text-[10px] ${textMuted}`}>{label}</span>
                <span className={`text-[10px] font-semibold ${textPrimary}`}>{value}</span>
              </div>
              <input type="range" min={min} max={max} step={step} value={value} onChange={(e) => setter(parseFloat(e.target.value))} className="w-full" />
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <div className={`${cardBg} border ${border} rounded-2xl p-4`}>
          <p className={`text-xs font-semibold ${textPrimary} mb-2`}>Compensation pipeline</p>
          <div className="flex flex-col gap-1">
            {["Wind conditions", "Random Forest", "Predicted drift", "Compensation calc."].map((s) => (
              <div key={s} className={`text-[10px] ${textMuted}`}>{s} <span className={textMuted}>↓</span></div>
            ))}
            <div className={`text-[10px] font-semibold ${accentText}`}>Required nozzle angle</div>
          </div>
        </div>

        <div className={`${cardBg} border ${border} rounded-2xl p-4`}>
          <p className={`text-xs font-semibold ${textPrimary} mb-2`}>Nozzle adjustment</p>
          <div className="flex justify-between mb-1">
            <span className={`text-[11px] ${textMuted}`}>Current angle</span>
            <span className={`text-[11px] ${textPrimary}`}>0°</span>
          </div>
          <div className="flex justify-between mb-3">
            <span className={`text-[11px] ${textMuted}`}>Required compensation</span>
            <span className={`text-[11px] ${textPrimary}`}>{nozzleAngle}°</span>
          </div>
          <p className={`text-[9px] ${textMuted}`}>Adjusted nozzle angle</p>
          <p className={`text-3xl font-bold ${accentText}`}>+{nozzleAngle}°</p>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        {[["Heading", "90°"], ["Battery", "82%"], ["Spray flow", "2.1 L/min"], ["Nozzle", `+${nozzleAngle}°`]].map(([l, v]) => (
          <div key={l} className={`${cardBg} border ${border} rounded-xl p-2.5`}>
            <p className={`text-[9px] ${textMuted}`}>{l}</p>
            <p className={`text-sm font-semibold ${l === "Nozzle" ? accentText : textPrimary}`}>{v}</p>
          </div>
        ))}
      </div>
    </div>
  );
}