import { useState, useEffect } from "react";
import { useTheme } from "../../context/ThemeContext";

export default function LiveMission() {
  const { isDark } = useTheme();
  const [battery, setBattery] = useState(20);
  const [tank, setTank] = useState(0);
  const [elapsed, setElapsed] = useState(157 * 60 + 12);

  useEffect(() => {
    const t = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(t);
  }, []);

  const cardBg = isDark ? "bg-surface" : "bg-light-surface";
  const border = isDark ? "border-border" : "border-light-border";
  const textMuted = isDark ? "text-muted" : "text-light-muted";
  const textPrimary = isDark ? "text-white" : "text-light-text";
  const inner = isDark ? "bg-ink" : "bg-light-bg";
  const accent = isDark ? "#C6F135" : "#2F5233";
  const accentText = isDark ? "text-accent" : "text-light-primary";
  const accentBg = isDark ? "bg-accent" : "bg-light-primary";
  const accentTextOn = isDark ? "text-ink" : "text-white";

  const mm = String(Math.floor(elapsed / 60)).padStart(2, "0");
  const ss = String(elapsed % 60).padStart(2, "0");

  return (
    <div className="flex flex-col gap-3">
      {/* Alert + live status strip */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <span className="text-[10px] font-semibold px-3 py-1.5 rounded-full border border-amber-500/40 bg-amber-500/10 text-amber-500">
          ⚠ Terrain rising ahead
        </span>
        <div className="flex items-center gap-3">
          <span className={`text-[10px] ${accentText} flex items-center gap-1`}>
            <span className={`w-1.5 h-1.5 rounded-full ${accentBg}`} /> Live
          </span>
          <span className={`text-[10px] font-mono ${textMuted}`}>11:37:46</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[220px_1fr_260px] gap-3">
        {/* Left panel */}
        <div className="flex flex-col gap-3">
          <div className={`${cardBg} border ${border} rounded-2xl p-3`}>
            <p className={`text-[9px] font-semibold ${textMuted} uppercase mb-1`}>Battery</p>
            <p className={`text-[10px] ${textMuted}`}>Remaining charge</p>
            <p className="text-2xl font-bold text-red-500">{battery}%</p>
            <p className={`text-[9px] ${textMuted} mb-1`}>Approx. 4 min remaining</p>
            <div className={`h-1.5 ${inner} rounded-full mb-3`}>
              <div className="h-full rounded-full bg-red-500" style={{ width: `${battery}%` }} />
            </div>
            <p className={`text-[10px] ${textMuted}`}>Spray tank</p>
            <p className={`text-xl font-bold ${textPrimary}`}>{tank.toFixed(1)} L</p>
            <p className={`text-[9px] ${textMuted}`}>0.0 kg payload remaining</p>
          </div>

          <div className={`${cardBg} border ${border} rounded-2xl p-3`}>
            <p className={`text-[9px] font-semibold ${textMuted} uppercase mb-2`}>Flight status</p>
            {[["Area covered", "1.10 ha"], ["Area remaining", "0.69 ha"], ["Mission time", `${mm}:${ss}`], ["Altitude", "5.2 m"], ["Speed", "6.3 km/h"]].map(([l, v]) => (
              <div key={l} className="flex justify-between py-1">
                <span className={`text-[10px] ${textMuted}`}>{l}</span>
                <span className={`text-[10px] font-semibold ${textPrimary}`}>{v}</span>
              </div>
            ))}
            <div className="flex justify-between py-1">
              <span className={`text-[10px] ${textMuted}`}>Obstacles avoided</span>
              <span className={`text-[10px] font-semibold ${accentText}`}>3</span>
            </div>
          </div>

          <div className={`${cardBg} border ${border} rounded-2xl p-3`}>
            <p className={`text-[9px] font-semibold ${textMuted} uppercase mb-2`}>Smart routing</p>
            <div className={`${isDark ? "bg-accent/10 border-accent/30" : "bg-light-primary/10 border-light-primary/30"} border rounded-lg p-2.5 mb-2`}>
              <p className={`text-[9px] font-semibold ${accentText} uppercase mb-0.5`}>Current decision</p>
              <p className={`text-[10px] ${textPrimary}`}>Tank nearly empty — tackling all remaining steep sections</p>
            </div>
            <div className="border border-amber-500/40 bg-amber-500/10 rounded-lg p-2.5">
              <p className="text-[9px] font-semibold text-amber-500 uppercase mb-0.5">⚠ Terrain rising ahead</p>
              <p className={`text-[10px] ${textPrimary}`}>Ground rising +0.4 m over next 6m. System will gain altitude automatically.</p>
            </div>
          </div>

          <div className={`${cardBg} border ${border} rounded-2xl p-3`}>
            <p className={`text-[9px] font-semibold ${textMuted} uppercase mb-2`}>Sensors</p>
            <div className="flex justify-between py-1">
              <span className={`text-[10px] ${textMuted}`}>Nearest obstacle</span>
              <span className="text-[10px] font-semibold text-amber-500">4.8 m</span>
            </div>
            <div className="flex justify-between py-1">
              <span className={`text-[10px] ${textMuted}`}>Height above ground</span>
              <span className={`text-[10px] font-semibold ${accentText}`}>5.2 m</span>
            </div>
            <div className="flex justify-between py-1">
              <span className={`text-[10px] ${textMuted}`}>Space above drone</span>
              <span className={`text-[10px] font-semibold ${textPrimary}`}>3.1 m</span>
            </div>
          </div>
        </div>

        {/* Map */}
        <div className={`${cardBg} border ${border} rounded-2xl p-3 relative flex flex-col`}>
          <div className={`${inner} border ${border} rounded-lg px-3 py-2 w-fit mb-2 z-10`}>
            <p className={`text-xs font-semibold ${textPrimary}`}>Ouvahkelle Estate — Hatton Plantation</p>
            <p className={`text-[9px] ${textMuted}`}>6.887°N 80.769°E</p>
          </div>

          <div className={`relative flex-1 ${inner} rounded-xl overflow-hidden min-h-[420px]`}>
            <svg viewBox="0 0 100 70" className="absolute inset-0 w-full h-full">
              {/* completed route */}
              <path d="M30,64 L34,50 L40,32" stroke={accent} strokeWidth="1" fill="none" />
              {/* planned route */}
              <path d="M40,32 L58,28 L72,42 L76,58" stroke="#3b82f6" strokeWidth="0.5" strokeDasharray="1,1" fill="none" opacity="0.6" />
              {/* energy detour */}
              <path d="M40,32 L54,26 L60,20" stroke="#f59e0b" strokeWidth="0.6" strokeDasharray="1.2,1" fill="none" />
              {/* shade tree obstacle */}
              <circle cx="60" cy="18" r="7" fill="none" stroke="#f59e0b" strokeWidth="0.3" strokeDasharray="0.6,0.6" opacity="0.7" />
              <text x="60" y="18" textAnchor="middle" fontSize="2.2" fill={isDark ? "#f59e0b" : "#b45309"}>shade tree</text>
              {/* canopy obstacle */}
              <circle cx="76" cy="42" r="8" fill="none" stroke="#ef4444" strokeWidth="0.3" strokeDasharray="0.6,0.6" opacity="0.7" />
              <text x="76" y="42" textAnchor="middle" fontSize="2.2" fill="#ef4444">⚠ canopy</text>
              {/* drone marker */}
              <circle cx="40" cy="32" r="1.8" fill={accent} />
              <text x="30" y="30" fontSize="2" fill={accent}>routed around steep hill</text>
              <text x="24" y="60" fontSize="2" fill={accent}>Sprayed area</text>
            </svg>
          </div>

          <div className="flex items-center justify-between mt-2 flex-wrap gap-2">
            <div className="flex gap-1.5">
              {["Satellite", "Route only", "Energy map"].map((label, i) => (
                <button key={label} className={`text-[10px] font-semibold px-2.5 py-1.5 rounded-lg ${i === 0 ? `${accentBg} ${accentTextOn}` : `${inner} ${textMuted}`}`}>
                  {label}
                </button>
              ))}
            </div>
            <div className={`${inner} border ${border} rounded-lg p-2 flex gap-3 text-[9px] flex-wrap`}>
              <span className="flex items-center gap-1"><span className="w-2 h-0.5" style={{ background: accent }} /> <span className={textMuted}>Completed route</span></span>
              <span className="flex items-center gap-1"><span className="w-2 h-0.5 bg-blue-500" /> <span className={textMuted}>Planned route</span></span>
              <span className="flex items-center gap-1"><span className="w-2 h-0.5 bg-amber-500" /> <span className={textMuted}>Energy detour</span></span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full border border-red-500" /> <span className={textMuted}>Obstacle detected</span></span>
            </div>
          </div>
        </div>

        {/* Right panel */}
        <div className="flex flex-col gap-3">
          <div className={`${cardBg} border ${border} rounded-2xl p-3`}>
            <p className={`text-[9px] font-semibold ${textMuted} uppercase mb-2`}>Mission overview</p>
            <div className="flex justify-between py-1"><span className={`text-[10px] ${textMuted}`}>Status</span><span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${accentBg} ${accentTextOn}`}>Active</span></div>
            <div className="flex justify-between py-1"><span className={`text-[10px] ${textMuted}`}>Waypoints</span><span className={`text-[10px] font-semibold ${textPrimary}`}>14 / 28</span></div>
            <div className="flex justify-between py-1"><span className={`text-[10px] ${textMuted}`}>GPS</span><span className={`text-[10px] font-semibold ${accentText}`}>RTK Fixed</span></div>
            <div className="flex justify-between py-1"><span className={`text-[10px] ${textMuted}`}>Depth sensor</span><span className={`text-[10px] font-semibold ${accentText}`}>Active</span></div>
            <div className="flex justify-between py-1"><span className={`text-[10px] ${textMuted}`}>Smart routing</span><span className={`text-[10px] font-semibold ${accentText}`}>DRL Active</span></div>
          </div>

          <div className={`${cardBg} border ${border} rounded-2xl p-3`}>
            <p className={`text-[9px] font-semibold ${textMuted} uppercase mb-2`}>Obstacle radar</p>
            <div className={`relative ${inner} rounded-xl h-32 mb-2 overflow-hidden`}>
              <svg viewBox="0 0 100 60" className="absolute inset-0 w-full h-full">
                <circle cx="50" cy="55" r="15" fill="none" stroke={border === "border-border" ? "#2A3830" : "#DCE3D5"} strokeWidth="0.5" />
                <circle cx="50" cy="55" r="30" fill="none" stroke={border === "border-border" ? "#2A3830" : "#DCE3D5"} strokeWidth="0.5" />
                <circle cx="50" cy="55" r="45" fill="none" stroke={border === "border-border" ? "#2A3830" : "#DCE3D5"} strokeWidth="0.5" />
                <polygon points="50,50 47,58 53,58" fill={accent} />
                <circle cx="38" cy="30" r="2" fill="#ef4444" />
                <circle cx="66" cy="24" r="2" fill="#f59e0b" />
              </svg>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <p className={`text-[9px] ${textMuted}`}>Nearest obstacle</p>
                <p className="text-sm font-bold text-amber-500">4.8 m</p>
                <p className={`text-[8px] ${textMuted}`}>Shade tree · right</p>
              </div>
              <div>
                <p className={`text-[9px] ${textMuted}`}>Ground distance</p>
                <p className={`text-sm font-bold ${accentText}`}>5.2 m</p>
                <p className={`text-[8px] ${textMuted}`}>Within target range</p>
              </div>
            </div>
          </div>

          <div className={`${cardBg} border ${border} rounded-2xl p-3 flex-1`}>
            <p className={`text-[9px] font-semibold ${textMuted} uppercase mb-2`}>Event log</p>
            {[
              { c: accent, t: "Shade tree avoided", d: "Climbed 2m to clear canopy", time: "12:31" },
              { c: "#f59e0b", t: "Route adjusted — steep hill", d: "Deferred until tank lighter", time: "12:24" },
              { c: accent, t: "Terrain rise — altitude corrected", d: "+1.2m over ridge", time: "12:18" },
            ].map((e) => (
              <div key={e.t} className="flex gap-2 py-1.5">
                <span className="w-1.5 h-1.5 rounded-full mt-1 flex-shrink-0" style={{ background: e.c }} />
                <div className="flex-1">
                  <div className="flex justify-between">
                    <p className={`text-[10px] font-semibold ${textPrimary}`}>{e.t}</p>
                    <p className={`text-[9px] ${textMuted}`}>{e.time}</p>
                  </div>
                  <p className={`text-[9px] ${textMuted}`}>{e.d}</p>
                </div>
              </div>
            ))}
          </div>

          <div className="flex gap-2">
            <button className={`flex-1 py-2.5 rounded-full text-xs font-semibold border ${border} ${textPrimary}`}>⏸ Pause</button>
            <button className="flex-1 py-2.5 rounded-full text-xs font-semibold bg-red-500 text-white">↩ Return Home</button>
          </div>
        </div>
      </div>
    </div>
  );
}