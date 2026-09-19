import { useState, useMemo } from "react";
import { useTheme } from "../../context/ThemeContext";

const STATUS_META = {
  spray: { label: "Spray events", dark: "bg-accent", light: "bg-light-primary", dot: "#C6F135" },
  no_spray: { label: "No-spray events", dark: "bg-red-500", light: "bg-red-500", dot: "#ef4444" },
  uncertain: { label: "Uncertain events", dark: "bg-amber-400", light: "bg-amber-500", dot: "#f59e0b" },
  no_tea: { label: "No tea", dark: "bg-gray-600", light: "bg-gray-300", dot: "#6b7280" },
};

function generateSegments(rows, cols) {
  const statuses = ["spray", "spray", "spray", "no_spray", "uncertain", "no_tea"];
  const segments = [];
  let id = 1;
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const status = statuses[Math.floor(Math.random() * statuses.length)];
      segments.push({
        id: `SEG-${String(id).padStart(3, "0")}`,
        row: r,
        col: c,
        status,
        confidence: (0.6 + Math.random() * 0.39).toFixed(2),
        timestamp: `14:${String(10 + id).padStart(2, "0")}`,
        altitude: (2 + Math.random()).toFixed(1),
        lat: (7.2906 + r * 0.0004).toFixed(6),
        lng: (80.6337 + c * 0.0004).toFixed(6),
        reason:
          status === "no_spray"
            ? "Person detected in frame"
            : status === "uncertain"
            ? "Confidence below threshold"
            : status === "no_tea"
            ? "No tea plant detected"
            : "Tea confirmed, zone clear",
      });
      id++;
    }
  }
  return segments;
}

const FLIGHT_PATH_D = "M6,10 L94,10 L94,24 L6,24 L6,38 L94,38 L94,52 L6,52";

export default function DetectionMap() {
  const { isDark } = useTheme();
  const [selected, setSelected] = useState(null);
  const [spraying, setSpraying] = useState(true);
  const [filters, setFilters] = useState({
    spray: true,
    no_spray: true,
    uncertain: true,
    showPath: true,
  });
  const [dateFrom, setDateFrom] = useState("2026-08-24");
  const [dateTo, setDateTo] = useState("2026-08-31");

  const segments = useMemo(() => generateSegments(6, 10), []);

  const counts = useMemo(() => {
    return segments.reduce(
      (acc, s) => {
        acc[s.status] = (acc[s.status] || 0) + 1;
        return acc;
      },
      { spray: 0, no_spray: 0, uncertain: 0, no_tea: 0 }
    );
  }, [segments]);

  const cardBg = isDark ? "bg-surface" : "bg-light-surface";
  const border = isDark ? "border-border" : "border-light-border";
  const textMuted = isDark ? "text-muted" : "text-light-muted";
  const textPrimary = isDark ? "text-white" : "text-light-text";
  const inner = isDark ? "bg-ink" : "bg-light-bg";
  const accent = isDark ? "text-accent" : "text-light-primary";
  const accentBg = isDark ? "bg-accent" : "bg-light-primary";
  const accentTextOn = isDark ? "text-ink" : "text-white";

  function toggleFilter(key) {
    setFilters((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  function isDimmed(status) {
    if (status === "no_tea") return false;
    return !filters[status];
  }

  return (
    <div className="flex flex-col lg:flex-row gap-4">
      {/* Page-specific filters panel */}
      <div className={`lg:w-56 flex-shrink-0 ${cardBg} border ${border} rounded-2xl p-4 h-fit`}>
        <p className={`text-xs font-semibold ${textPrimary} mb-3`}>Map filters</p>

        <div className="mb-4">
          <p className={`text-[10px] ${textMuted} mb-1`}>From</p>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className={`w-full text-xs ${inner} border ${border} rounded-lg px-2 py-1.5 ${textPrimary} mb-2`}
          />
          <p className={`text-[10px] ${textMuted} mb-1`}>To</p>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className={`w-full text-xs ${inner} border ${border} rounded-lg px-2 py-1.5 ${textPrimary}`}
          />
        </div>

        <p className={`text-[10px] ${textMuted} mb-2`}>Event types</p>
        <div className="flex flex-col gap-2 mb-4">
          {["spray", "no_spray", "uncertain"].map((key) => (
            <label key={key} className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={filters[key]}
                onChange={() => toggleFilter(key)}
                className="accent-current"
                style={{ color: STATUS_META[key].dot }}
              />
              <span className="w-2 h-2 rounded-full" style={{ background: STATUS_META[key].dot }} />
              <span className={`text-xs ${textPrimary}`}>{STATUS_META[key].label}</span>
            </label>
          ))}
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={filters.showPath}
              onChange={() => toggleFilter("showPath")}
            />
            <span className="w-2 h-2 rounded-full bg-cyan-400" />
            <span className={`text-xs ${textPrimary}`}>Flight path</span>
          </label>
        </div>

        <p className={`text-[10px] ${textMuted} mb-2`}>Export</p>
        <div className="flex flex-col gap-2">
          <button
            onClick={() => alert("Exporting KML — hook up to real data later")}
            className={`text-xs py-2 rounded-lg border ${border} ${textPrimary} hover:opacity-80 transition`}
          >
            Download KML
          </button>
          <button
            onClick={() => alert("Exporting GeoJSON — hook up to real data later")}
            className={`text-xs py-2 rounded-lg border ${border} ${textPrimary} hover:opacity-80 transition`}
          >
            Download GeoJSON
          </button>
        </div>
      </div>

      {/* Main map area */}
      <div className="flex-1 min-w-0 flex flex-col gap-4">
        <div className={`${cardBg} border ${border} rounded-2xl p-4 relative overflow-hidden`}>
          {/* Telemetry bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
            <div>
              <p className={`text-[10px] ${textMuted}`}>Pass 2 · Prescription-guided</p>
              <p className={`text-sm font-semibold ${textPrimary}`}>TeaDrone</p>
            </div>
            <div className="flex items-center gap-4 text-right">
              {[
                ["Altitude", "2.4 m"],
                ["Speed", "3.4 m/s"],
                ["Distance", "489 m"],
                ["Battery", "76%"],
                ["Tank", "80%"],
                ["Heading", "90°"],
              ].map(([label, value]) => (
                <div key={label}>
                  <p className={`text-[9px] ${textMuted} uppercase`}>{label}</p>
                  <p className={`text-xs font-semibold ${textPrimary}`}>{value}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Grid + animated flight path */}
          <div className="relative">
            <div className={`grid grid-cols-10 gap-1.5 ${inner} rounded-xl p-3`}>
              {segments.map((seg) => {
                const meta = STATUS_META[seg.status];
                const isSelected = selected?.id === seg.id;
                return (
                  <button
                    key={seg.id}
                    onClick={() => setSelected(seg)}
                    className={`aspect-square rounded-md transition ${isDark ? meta.dark : meta.light} ${
                      isDimmed(seg.status) ? "opacity-15" : "opacity-100"
                    } ${isSelected ? "ring-2 ring-white ring-offset-1 ring-offset-transparent" : "hover:opacity-80"}`}
                    aria-label={`${seg.id} — ${meta.label}`}
                  />
                );
              })}
            </div>

            {filters.showPath && (
              <svg
                viewBox="0 0 100 60"
                preserveAspectRatio="none"
                className="absolute inset-0 w-full h-full pointer-events-none"
              >
                <path
                  d={FLIGHT_PATH_D}
                  fill="none"
                  stroke="#2FE0D8"
                  strokeWidth="0.6"
                  strokeDasharray="1.5,1.5"
                  opacity="0.8"
                />
                <polygon points="0,-1.6 2.6,1.6 0,0.6 -2.6,1.6" fill="#2FE0D8">
                  <animateMotion dur="10s" repeatCount="indefinite" rotate="auto">
                    <mpath href={`#flight-path-ref`} />
                  </animateMotion>
                </polygon>
                <path id="flight-path-ref" d={FLIGHT_PATH_D} fill="none" opacity="0" />
              </svg>
            )}
          </div>

          {/* Legend */}
          <div className={`absolute top-16 right-6 ${cardBg} border ${border} rounded-xl p-2.5 flex flex-col gap-1.5`}>
            {Object.entries(STATUS_META).map(([key, meta]) => (
              <div key={key} className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full" style={{ background: meta.dot }} />
                <span className={`text-[10px] ${textMuted}`}>{meta.label}</span>
              </div>
            ))}
          </div>

          {/* Current zone popup */}
          {selected && (
            <div className={`absolute bottom-6 left-6 w-64 ${cardBg} border ${border} rounded-xl p-4`}>
              <div className="flex items-center justify-between mb-2">
                <p className={`text-[10px] ${textMuted}`}>Current zone</p>
                <button onClick={() => setSelected(null)} className={`text-xs ${textMuted} hover:${textPrimary}`}>
                  ✕
                </button>
              </div>
              <p className={`text-lg font-semibold ${textPrimary} mb-2`}>{selected.id}</p>

              <div className="grid grid-cols-2 gap-2 mb-2">
                <div>
                  <p className={`text-[9px] ${textMuted}`}>Confidence</p>
                  <p className={`text-xs font-semibold ${textPrimary}`}>{selected.confidence}</p>
                </div>
                <div>
                  <p className={`text-[9px] ${textMuted}`}>Time</p>
                  <p className={`text-xs font-semibold ${textPrimary}`}>{selected.timestamp}</p>
                </div>
                <div>
                  <p className={`text-[9px] ${textMuted}`}>Altitude</p>
                  <p className={`text-xs font-semibold ${textPrimary}`}>{selected.altitude} m</p>
                </div>
                <div>
                  <p className={`text-[9px] ${textMuted}`}>Decision</p>
                  <p className={`text-xs font-semibold ${accent}`}>{STATUS_META[selected.status].label}</p>
                </div>
              </div>

              <p className={`text-[9px] ${textMuted} mb-3`}>GPS: {selected.lat}, {selected.lng}</p>
              <p className={`text-xs ${textPrimary} mb-3`}>{selected.reason}</p>

              <div className="flex gap-2 mb-2">
                <button
                  onClick={() => setSpraying(true)}
                  className={`flex-1 py-2 rounded-full text-xs font-semibold border ${border} ${textPrimary}`}
                >
                  Hold
                </button>
                <button
                  onClick={() => setSpraying(false)}
                  className="flex-1 py-2 rounded-full text-xs font-semibold bg-red-500 text-white"
                >
                  Stop spray
                </button>
              </div>
              <button
                onClick={() => alert("Would open the detection frame image")}
                className={`w-full py-2 rounded-full text-xs font-semibold ${accentBg} ${accentTextOn}`}
              >
                View image
              </button>
            </div>
          )}
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {[
            ["Spray events", counts.spray],
            ["No-spray events", counts.no_spray],
            ["Uncertain events", counts.uncertain],
            ["Flight distance", "0.49 km"],
            ["Area covered", "1.2 ha"],
          ].map(([label, value]) => (
            <div key={label} className={`${cardBg} border ${border} rounded-xl p-3`}>
              <p className={`text-[10px] ${textMuted}`}>{label}</p>
              <p className={`text-base font-semibold ${textPrimary}`}>{value}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}