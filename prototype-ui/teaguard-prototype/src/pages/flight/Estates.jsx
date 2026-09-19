import { useState, useRef } from "react";
import { useTheme } from "../../context/ThemeContext";

export default function Estates() {
  const { isDark } = useTheme();
  const [tiff, setTiff] = useState(null);
  const [kml, setKml] = useState(null);
  const [name, setName] = useState("");
  const [region, setRegion] = useState("");

  const cardBg = isDark ? "bg-surface" : "bg-light-surface";
  const border = isDark ? "border-border" : "border-light-border";
  const textMuted = isDark ? "text-muted" : "text-light-muted";
  const textPrimary = isDark ? "text-white" : "text-light-text";
  const inner = isDark ? "bg-ink" : "bg-light-bg";
  const accent = isDark ? "#C6F135" : "#2F5233";
  const accentText = isDark ? "text-accent" : "text-light-primary";
  const accentBg = isDark ? "bg-accent" : "bg-light-primary";
  const accentTextOn = isDark ? "text-ink" : "text-white";

  const STEPS = ["Upload files", "Process map", "Load system", "Ready"];
  const bothUploaded = tiff && kml;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[300px_1fr] gap-4">
      <div className="flex flex-col gap-3">
        <div>
          <h1 className={`text-lg font-bold ${textPrimary}`}>Add a New Estate</h1>
          <p className={`text-[11px] ${textMuted}`}>Upload the estate map and boundary file. The system sets up the route automatically — no manual planning needed.</p>
        </div>

        <div className="flex items-center gap-1 flex-wrap">
          {STEPS.map((s, i) => (
            <span key={s} className="flex items-center gap-1">
              <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[9px] font-bold ${i === 0 ? `${accentBg} ${accentTextOn}` : `${inner} ${textMuted}`}`}>{i + 1}</span>
              <span className={`text-[9px] ${textMuted}`}>{s}</span>
              {i < STEPS.length - 1 && <span className={`text-[9px] ${textMuted} mx-0.5`}>—</span>}
            </span>
          ))}
        </div>

        <div className="grid grid-cols-2 gap-2">
          <label className={`${cardBg} border-2 border-dashed ${tiff ? (isDark ? "border-accent" : "border-light-primary") : border} rounded-2xl p-3 text-center cursor-pointer`}>
            <input type="file" className="hidden" onChange={(e) => setTiff(e.target.files[0])} />
            <p className="text-lg mb-1">🗺️</p>
            <p className={`text-[11px] font-semibold ${textPrimary}`}>Terrain map (TIFF)</p>
            <p className={`text-[9px] ${textMuted} mb-2`}>Aerial orthophoto of the estate</p>
            <span className={`text-[9px] font-semibold ${tiff ? accentText : textMuted}`}>{tiff ? `✓ ${tiff.name}` : "Click to upload"}</span>
          </label>
          <label className={`${cardBg} border-2 border-dashed ${kml ? (isDark ? "border-accent" : "border-light-primary") : border} rounded-2xl p-3 text-center cursor-pointer`}>
            <input type="file" className="hidden" onChange={(e) => setKml(e.target.files[0])} />
            <p className="text-lg mb-1">📍</p>
            <p className={`text-[11px] font-semibold ${textPrimary}`}>Estate boundary (KML)</p>
            <p className={`text-[9px] ${textMuted} mb-2`}>GPS boundary of the spray zone</p>
            <span className={`text-[9px] font-semibold ${kml ? accentText : textMuted}`}>{kml ? `✓ ${kml.name}` : "Click to upload"}</span>
          </label>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <div>
            <p className={`text-[9px] ${textMuted} mb-1`}>Estate name</p>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Ouvahkelle Estate" className={`w-full text-xs ${inner} border ${border} rounded-lg px-2 py-2 ${textPrimary}`} />
          </div>
          <div>
            <p className={`text-[9px] ${textMuted} mb-1`}>Region</p>
            <select value={region} onChange={(e) => setRegion(e.target.value)} className={`w-full text-xs ${inner} border ${border} rounded-lg px-2 py-2 ${textPrimary}`}>
              <option value="">Select...</option>
              <option>Hatton / Nuwara Eliya</option>
              <option>Kandy / Matale</option>
              <option>Badulla / Ella</option>
              <option>Polonnaruwa</option>
            </select>
          </div>
        </div>

        <button
          disabled={!bothUploaded}
          className={`w-full py-2.5 rounded-full text-xs font-semibold ${bothUploaded ? `${accentBg} ${accentTextOn}` : `${inner} ${textMuted} cursor-not-allowed`}`}
        >
          {bothUploaded ? "Generate cost map →" : "Upload both files to continue"}
        </button>

        <div className={`${cardBg} border ${border} rounded-2xl p-3`}>
          <p className={`text-[9px] font-semibold ${textMuted} uppercase mb-2`}>Your estates</p>
          <div className={`flex items-center justify-between py-2 border-b ${border}`}>
            <div className="flex items-center gap-2">
              <span className={`w-1.5 h-1.5 rounded-full ${accentBg}`} />
              <div>
                <p className={`text-xs font-semibold ${textPrimary}`}>Ouvahkelle Estate</p>
                <p className={`text-[9px] ${textMuted}`}>Hatton · Mountainous · 1.1 ha</p>
              </div>
            </div>
            <div className="flex gap-1.5">
              <span className={`text-[9px] font-semibold px-2 py-1 rounded-full ${isDark ? "bg-accent/20 text-accent" : "bg-light-primary/15 text-light-primary"}`}>Active</span>
              <button className={`text-[9px] font-semibold px-2 py-1 rounded-full border ${border} ${textPrimary}`}>Open</button>
            </div>
          </div>
          <div className="flex items-center justify-between py-2 opacity-60">
            <div>
              <p className={`text-xs font-semibold ${textPrimary}`}>Sungavila Estate</p>
              <p className={`text-[9px] ${textMuted}`}>Polonnaruwa · Flat · 0.8 ha</p>
            </div>
            <div className="flex gap-1.5">
              <span className={`text-[9px] px-2 py-1 rounded-full border ${border} ${textMuted}`}>Inactive</span>
              <button className={`text-[9px] font-semibold px-2 py-1 rounded-full border ${border} ${textPrimary}`}>Load</button>
            </div>
          </div>
          <button className={`w-full text-left text-[10px] ${accentText} mt-2`}>
            + Add new estate <span className={textMuted}>— Upload TIFF + KML above</span>
          </button>
        </div>
      </div>

      {/* Terrain preview */}
      <div className={`${cardBg} border ${border} rounded-2xl p-3 relative`}>
        <div className={`relative ${inner} rounded-xl overflow-hidden min-h-[500px] flex items-center justify-center`}>
          {!bothUploaded && (
            <svg viewBox="0 0 100 70" className="absolute inset-0 w-full h-full opacity-40">
              {[10, 24, 38, 52, 66].map((y, i) => (
                <path key={i} d={`M0,${y} Q30,${y - 5} 55,${y} T100,${y - 2}`} stroke={accent} strokeWidth="0.3" fill="none" />
              ))}
            </svg>
          )}
          <div className="relative z-10 text-center px-6">
            <p className={`text-sm font-semibold ${accentText}`}>Upload your estate files</p>
            <p className={`text-xs ${textMuted}`}>to see your terrain here</p>
          </div>
        </div>
      </div>
    </div>
  );
}