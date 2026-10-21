import { useState, useMemo } from "react";
import { useTheme } from "../../context/ThemeContext";

const CLASSES = ["tea_plant", "person", "animal", "road", "bare_soil"];
const DECISIONS = ["SPRAY", "NO_SPRAY", "UNCERTAIN"];

function generateDetections(count) {
  const rows = [];
  for (let i = 1; i <= count; i++) {
    const cls = CLASSES[Math.floor(Math.random() * CLASSES.length)];
    const decision = DECISIONS[Math.floor(Math.random() * DECISIONS.length)];
    const hour = String(8 + Math.floor(Math.random() * 9)).padStart(2, "0");
    const min = String(Math.floor(Math.random() * 60)).padStart(2, "0");
    rows.push({
      id: `DET-${String(1000 + i)}`,
      timestamp: `2026-08-${String(20 + (i % 8)).padStart(2, "0")} ${hour}:${min}`,
      hour: parseInt(hour),
      class: cls,
      confidence: +(0.55 + Math.random() * 0.44).toFixed(2),
      lat: (7.2906 + Math.random() * 0.01).toFixed(6),
      lng: (80.6337 + Math.random() * 0.01).toFixed(6),
      altitude: +(2 + Math.random() * 1.5).toFixed(1),
      decision,
      sprayStatus: decision === "SPRAY" ? "ON" : "OFF",
      imagePath: `/frames/${1000 + i}.jpg`,
    });
  }
  return rows;
}

const DECISION_STYLE = {
  SPRAY: { dark: "bg-accent/10 border-l-4 border-accent", light: "bg-light-primary/10 border-l-4 border-light-primary", text: "text-accent-dark" },
  NO_SPRAY: { dark: "bg-red-500/10 border-l-4 border-red-500", light: "bg-red-50 border-l-4 border-red-500", text: "text-red-500" },
  UNCERTAIN: { dark: "bg-amber-500/10 border-l-4 border-amber-500", light: "bg-amber-50 border-l-4 border-amber-500", text: "text-amber-500" },
};

export default function Logs() {
  const { isDark } = useTheme();
  const [tab, setTab] = useState("history"); // "history" | "reports"

  const cardBg = isDark ? "bg-surface" : "bg-light-surface";
  const border = isDark ? "border-border" : "border-light-border";
  const textMuted = isDark ? "text-muted" : "text-light-muted";
  const textPrimary = isDark ? "text-white" : "text-light-text";
  const inner = isDark ? "bg-ink" : "bg-light-bg";
  const accentBg = isDark ? "bg-accent" : "bg-light-primary";
  const accentTextOn = isDark ? "text-ink" : "text-white";

  return (
    <div className="flex flex-col gap-4">
      <div className={`flex gap-2 ${cardBg} border ${border} rounded-full p-1 w-fit`}>
        <button
          onClick={() => setTab("history")}
          className={`text-xs font-semibold px-4 py-2 rounded-full transition ${
            tab === "history" ? `${accentBg} ${accentTextOn}` : textMuted
          }`}
        >
          Detection history
        </button>
        <button
          onClick={() => setTab("reports")}
          className={`text-xs font-semibold px-4 py-2 rounded-full transition ${
            tab === "reports" ? `${accentBg} ${accentTextOn}` : textMuted
          }`}
        >
          Spray reports
        </button>
      </div>

      {tab === "history" ? <DetectionHistory isDark={isDark} /> : <SprayReports isDark={isDark} />}
    </div>
  );
}

/* ============================= TAB 1: DETECTION HISTORY ============================= */

function DetectionHistory({ isDark }) {
  const allRows = useMemo(() => generateDetections(87), []);

  const [draft, setDraft] = useState({
    dateFrom: "2026-08-20",
    dateTo: "2026-08-28",
    class: "all",
    decision: "all",
    minConfidence: 0,
  });
  const [applied, setApplied] = useState(draft);
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState("timestamp");
  const [sortDir, setSortDir] = useState("desc");
  const [page, setPage] = useState(1);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [expandedId, setExpandedId] = useState(null);
  const [selectedIds, setSelectedIds] = useState(new Set());

  const cardBg = isDark ? "bg-surface" : "bg-light-surface";
  const border = isDark ? "border-border" : "border-light-border";
  const textMuted = isDark ? "text-muted" : "text-light-muted";
  const textPrimary = isDark ? "text-white" : "text-light-text";
  const inner = isDark ? "bg-ink" : "bg-light-bg";
  const accentBg = isDark ? "bg-accent" : "bg-light-primary";
  const accentTextOn = isDark ? "text-ink" : "text-white";

  const filtered = useMemo(() => {
    let rows = allRows.filter((r) => {
      if (applied.class !== "all" && r.class !== applied.class) return false;
      if (applied.decision !== "all" && r.decision !== applied.decision) return false;
      if (r.confidence < applied.minConfidence) return false;
      return true;
    });
    if (search.trim()) {
      const q = search.toLowerCase();
      rows = rows.filter(
        (r) =>
          r.class.toLowerCase().includes(q) ||
          r.timestamp.toLowerCase().includes(q) ||
          r.lat.includes(q) ||
          r.lng.includes(q) ||
          r.id.toLowerCase().includes(q)
      );
    }
    rows = [...rows].sort((a, b) => {
      const dir = sortDir === "asc" ? 1 : -1;
      if (a[sortKey] < b[sortKey]) return -1 * dir;
      if (a[sortKey] > b[sortKey]) return 1 * dir;
      return 0;
    });
    return rows;
  }, [allRows, applied, search, sortKey, sortDir]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / rowsPerPage));
  const pageRows = filtered.slice((page - 1) * rowsPerPage, page * rowsPerPage);

  function toggleSort(key) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  }

  function toggleSelectAll() {
    const pageIds = pageRows.map((r) => r.id);
    const allSelected = pageIds.every((id) => selectedIds.has(id));
    const next = new Set(selectedIds);
    pageIds.forEach((id) => (allSelected ? next.delete(id) : next.add(id)));
    setSelectedIds(next);
  }

  function toggleSelectRow(id) {
    const next = new Set(selectedIds);
    next.has(id) ? next.delete(id) : next.add(id);
    setSelectedIds(next);
  }

  function applyFilters() {
    setApplied(draft);
    setPage(1);
  }

  function resetFilters() {
    const reset = { dateFrom: "2026-08-20", dateTo: "2026-08-28", class: "all", decision: "all", minConfidence: 0 };
    setDraft(reset);
    setApplied(reset);
    setPage(1);
  }

  const stats = useMemo(() => {
    const byClass = {};
    let confSum = 0;
    filtered.forEach((r) => {
      byClass[r.class] = (byClass[r.class] || 0) + 1;
      confSum += r.confidence;
    });
    return {
      total: filtered.length,
      byClass,
      avgConfidence: filtered.length ? (confSum / filtered.length).toFixed(2) : "0.00",
    };
  }, [filtered]);

  const columns = [
    { key: "timestamp", label: "Timestamp" },
    { key: "class", label: "Class" },
    { key: "confidence", label: "Confidence" },
    { key: "gps", label: "GPS" },
    { key: "altitude", label: "Altitude" },
    { key: "decision", label: "Decision" },
    { key: "sprayStatus", label: "Spray" },
    { key: "image", label: "Image" },
  ];

  return (
    <div className="flex flex-col lg:flex-row gap-4">
      {/* Filters sidebar */}
      <div className={`lg:w-56 flex-shrink-0 ${cardBg} border ${border} rounded-2xl p-4 h-fit`}>
        <p className={`text-xs font-semibold ${textPrimary} mb-3`}>Filters</p>

        <p className={`text-[10px] ${textMuted} mb-1`}>From</p>
        <input
          type="date"
          value={draft.dateFrom}
          onChange={(e) => setDraft({ ...draft, dateFrom: e.target.value })}
          className={`w-full text-xs ${inner} border ${border} rounded-lg px-2 py-1.5 ${textPrimary} mb-2`}
        />
        <p className={`text-[10px] ${textMuted} mb-1`}>To</p>
        <input
          type="date"
          value={draft.dateTo}
          onChange={(e) => setDraft({ ...draft, dateTo: e.target.value })}
          className={`w-full text-xs ${inner} border ${border} rounded-lg px-2 py-1.5 ${textPrimary} mb-3`}
        />

        <p className={`text-[10px] ${textMuted} mb-1`}>Class</p>
        <select
          value={draft.class}
          onChange={(e) => setDraft({ ...draft, class: e.target.value })}
          className={`w-full text-xs ${inner} border ${border} rounded-lg px-2 py-1.5 ${textPrimary} mb-3`}
        >
          <option value="all">All classes</option>
          {CLASSES.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>

        <p className={`text-[10px] ${textMuted} mb-1`}>Spray decision</p>
        <select
          value={draft.decision}
          onChange={(e) => setDraft({ ...draft, decision: e.target.value })}
          className={`w-full text-xs ${inner} border ${border} rounded-lg px-2 py-1.5 ${textPrimary} mb-3`}
        >
          <option value="all">All decisions</option>
          {DECISIONS.map((d) => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>

        <p className={`text-[10px] ${textMuted} mb-1`}>
          Min confidence: {draft.minConfidence.toFixed(2)}
        </p>
        <input
          type="range"
          min="0"
          max="1"
          step="0.01"
          value={draft.minConfidence}
          onChange={(e) => setDraft({ ...draft, minConfidence: parseFloat(e.target.value) })}
          className="w-full mb-4"
        />

        <div className="flex flex-col gap-2">
          <button
            onClick={applyFilters}
            className={`text-xs font-semibold py-2 rounded-lg ${accentBg} ${accentTextOn}`}
          >
            Apply filters
          </button>
          <button
            onClick={resetFilters}
            className={`text-xs font-semibold py-2 rounded-lg border ${border} ${textPrimary}`}
          >
            Reset filters
          </button>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 min-w-0 flex flex-col gap-4">
        {/* Summary stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className={`${cardBg} border ${border} rounded-xl p-3`}>
            <p className={`text-[10px] ${textMuted}`}>Total detections</p>
            <p className={`text-base font-semibold ${textPrimary}`}>{stats.total}</p>
          </div>
          <div className={`${cardBg} border ${border} rounded-xl p-3`}>
            <p className={`text-[10px] ${textMuted}`}>Tea</p>
            <p className={`text-base font-semibold ${textPrimary}`}>{stats.byClass.tea_plant || 0}</p>
          </div>
          <div className={`${cardBg} border ${border} rounded-xl p-3`}>
            <p className={`text-[10px] ${textMuted}`}>Person / Animal</p>
            <p className={`text-base font-semibold ${textPrimary}`}>
              {(stats.byClass.person || 0) + (stats.byClass.animal || 0)}
            </p>
          </div>
          <div className={`${cardBg} border ${border} rounded-xl p-3`}>
            <p className={`text-[10px] ${textMuted}`}>Avg confidence</p>
            <p className={`text-base font-semibold ${textPrimary}`}>{stats.avgConfidence}</p>
          </div>
        </div>

        {/* Table card */}
        <div className={`${cardBg} border ${border} rounded-2xl p-4`}>
          <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
            <input
              type="text"
              placeholder="Search class, GPS, timestamp..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className={`text-xs ${inner} border ${border} rounded-lg px-3 py-2 ${textPrimary} w-64`}
            />
            <div className="flex items-center gap-3">
              <span className={`text-xs ${textMuted}`}>{selectedIds.size} selected</span>
              <select
                value={rowsPerPage}
                onChange={(e) => { setRowsPerPage(parseInt(e.target.value)); setPage(1); }}
                className={`text-xs ${inner} border ${border} rounded-lg px-2 py-1.5 ${textPrimary}`}
              >
                {[10, 25, 50, 100].map((n) => (
                  <option key={n} value={n}>{n} / page</option>
                ))}
              </select>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className={`border-b ${border}`}>
                  <th className="p-2 text-left">
                    <input
                      type="checkbox"
                      checked={pageRows.length > 0 && pageRows.every((r) => selectedIds.has(r.id))}
                      onChange={toggleSelectAll}
                    />
                  </th>
                  {columns.map((col) => (
                    <th
                      key={col.key}
                      onClick={() => col.key !== "gps" && col.key !== "image" && toggleSort(col.key)}
                      className={`p-2 text-left font-semibold ${textMuted} ${
                        col.key !== "gps" && col.key !== "image" ? "cursor-pointer hover:opacity-80" : ""
                      }`}
                    >
                      {col.label} {sortKey === col.key && (sortDir === "asc" ? "↑" : "↓")}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {pageRows.map((row) => {
                  const style = DECISION_STYLE[row.decision];
                  const expanded = expandedId === row.id;
                  return (
                    <>
                      <tr
                        key={row.id}
                        onClick={() => setExpandedId(expanded ? null : row.id)}
                        className={`${isDark ? style.dark : style.light} cursor-pointer`}
                      >
                        <td className="p-2" onClick={(e) => e.stopPropagation()}>
                          <input
                            type="checkbox"
                            checked={selectedIds.has(row.id)}
                            onChange={() => toggleSelectRow(row.id)}
                          />
                        </td>
                        <td className={`p-2 font-mono ${textPrimary}`}>{row.timestamp}</td>
                        <td className={`p-2 ${textPrimary}`}>{row.class}</td>
                        <td className={`p-2 ${textPrimary}`}>{row.confidence}</td>
                        <td className={`p-2 font-mono ${textMuted}`}>{row.lat}, {row.lng}</td>
                        <td className={`p-2 ${textPrimary}`}>{row.altitude} m</td>
                        <td className={`p-2 font-semibold ${style.text}`}>{row.decision}</td>
                        <td className={`p-2 ${textPrimary}`}>{row.sprayStatus}</td>
                        <td className="p-2">
                          <button
                            onClick={(e) => { e.stopPropagation(); alert(`Would open ${row.imagePath}`); }}
                            className="text-cyan-500 underline"
                          >
                            View
                          </button>
                        </td>
                      </tr>
                      {expanded && (
                        <tr key={`${row.id}-detail`}>
                          <td colSpan={9} className={`p-3 ${inner}`}>
                            <p className={`text-xs ${textPrimary}`}>
                              Full detail for <span className="font-mono">{row.id}</span> — reason:{" "}
                              {row.decision === "SPRAY" ? "Tea confirmed, zone clear" : row.decision === "NO_SPRAY" ? "Safety class detected in frame" : "Confidence below threshold"}
                            </p>
                          </td>
                        </tr>
                      )}
                    </>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between mt-3">
            <p className={`text-xs ${textMuted}`}>
              Page {page} of {totalPages} · {filtered.length} results
            </p>
            <div className="flex gap-2">
              <button
                disabled={page === 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className={`text-xs px-3 py-1.5 rounded-lg border ${border} ${textPrimary} disabled:opacity-40`}
              >
                Prev
              </button>
              <button
                disabled={page === totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                className={`text-xs px-3 py-1.5 rounded-lg border ${border} ${textPrimary} disabled:opacity-40`}
              >
                Next
              </button>
            </div>
          </div>
        </div>

        {/* Export */}
        <div className={`${cardBg} border ${border} rounded-2xl p-4 flex flex-wrap gap-2`}>
          <button onClick={() => alert("Exporting CSV")} className={`text-xs font-semibold px-4 py-2 rounded-lg border ${border} ${textPrimary}`}>Download CSV</button>
          <button onClick={() => alert("Exporting Excel")} className={`text-xs font-semibold px-4 py-2 rounded-lg border ${border} ${textPrimary}`}>Download Excel</button>
          <button onClick={() => alert("Exporting PDF")} className={`text-xs font-semibold px-4 py-2 rounded-lg border ${border} ${textPrimary}`}>Download PDF</button>
        </div>
      </div>
    </div>
  );
}

/* ============================= TAB 2: SPRAY REPORTS ============================= */

function SprayReports({ isDark }) {
  const [dateFrom, setDateFrom] = useState("2026-08-20");
  const [dateTo, setDateTo] = useState("2026-08-28");
  const [field, setField] = useState("all");
  const [generated, setGenerated] = useState(true);

  const cardBg = isDark ? "bg-surface" : "bg-light-surface";
  const border = isDark ? "border-border" : "border-light-border";
  const textMuted = isDark ? "text-muted" : "text-light-muted";
  const textPrimary = isDark ? "text-white" : "text-light-text";
  const inner = isDark ? "bg-ink" : "bg-light-bg";
  const accentBg = isDark ? "bg-accent" : "bg-light-primary";
  const accentTextOn = isDark ? "text-ink" : "text-white";
  const accentDot = isDark ? "#C6F135" : "#2F5233";

  const hourlyData = useMemo(
    () => Array.from({ length: 24 }, (_, h) => (h >= 7 && h <= 17 ? Math.floor(Math.random() * 20) + 2 : Math.floor(Math.random() * 3))),
    []
  );
  const maxHourly = Math.max(...hourlyData);

  const classBreakdown = [
    { label: "Tea", pct: 62, color: accentDot },
    { label: "Weed", pct: 18, color: "#f59e0b" },
    { label: "Person", pct: 12, color: "#ef4444" },
    { label: "Animal", pct: 8, color: "#6b7280" },
  ];
  const conicStops = (() => {
    let acc = 0;
    return classBreakdown.map((c) => {
      const start = acc;
      acc += c.pct;
      return `${c.color} ${start}% ${acc}%`;
    }).join(", ");
  })();

  const coveragePoints = useMemo(() => {
    let acc = 0;
    return Array.from({ length: 8 }, (_, i) => {
      acc += Math.random() * 14;
      return Math.min(acc, 100);
    });
  }, []);

  return (
    <div className="flex flex-col lg:flex-row gap-4">
      {/* Filters sidebar */}
      <div className={`lg:w-56 flex-shrink-0 ${cardBg} border ${border} rounded-2xl p-4 h-fit`}>
        <p className={`text-xs font-semibold ${textPrimary} mb-3`}>Report filters</p>

        <p className={`text-[10px] ${textMuted} mb-1`}>From</p>
        <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)}
          className={`w-full text-xs ${inner} border ${border} rounded-lg px-2 py-1.5 ${textPrimary} mb-2`} />
        <p className={`text-[10px] ${textMuted} mb-1`}>To</p>
        <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)}
          className={`w-full text-xs ${inner} border ${border} rounded-lg px-2 py-1.5 ${textPrimary} mb-3`} />

        <p className={`text-[10px] ${textMuted} mb-1`}>Field / plantation</p>
        <select value={field} onChange={(e) => setField(e.target.value)}
          className={`w-full text-xs ${inner} border ${border} rounded-lg px-2 py-1.5 ${textPrimary} mb-4`}>
          <option value="all">All fields</option>
          <option value="block7">Nuwara Estate — Block 7</option>
          <option value="block4">Nuwara Estate — Block 4</option>
          <option value="hantana2">Hantana Division — Block 2</option>
        </select>

        <button
          onClick={() => setGenerated(true)}
          className={`w-full text-xs font-semibold py-2 rounded-lg ${accentBg} ${accentTextOn}`}
        >
          Generate report
        </button>
      </div>

      {!generated ? (
        <div className={`flex-1 ${cardBg} border ${border} rounded-2xl p-8 flex items-center justify-center`}>
          <p className={`text-xs ${textMuted}`}>Set filters and generate a report to see results.</p>
        </div>
      ) : (
        <div className="flex-1 min-w-0 flex flex-col gap-4">
          {/* Summary cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              ["Spray events", "142"],
              ["No-spray events", "31"],
              ["Uncertain events", "19"],
              ["Spray coverage", "74%"],
            ].map(([label, value]) => (
              <div key={label} className={`${cardBg} border ${border} rounded-xl p-3`}>
                <p className={`text-[10px] ${textMuted}`}>{label}</p>
                <p className={`text-lg font-semibold ${textPrimary}`}>{value}</p>
              </div>
            ))}
          </div>

          {/* Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className={`${cardBg} border ${border} rounded-2xl p-4`}>
              <p className={`text-xs ${textMuted} mb-3`}>Spray events by hour</p>
              <div className="flex items-end gap-0.5 h-24">
                {hourlyData.map((v, h) => (
                  <div
                    key={h}
                    className="flex-1 rounded-t"
                    style={{ height: `${(v / maxHourly) * 100}%`, background: accentDot, opacity: v === 0 ? 0.15 : 1 }}
                    title={`${h}:00 — ${v} events`}
                  />
                ))}
              </div>
              <div className="flex justify-between mt-1">
                <span className={`text-[9px] ${textMuted}`}>00:00</span>
                <span className={`text-[9px] ${textMuted}`}>12:00</span>
                <span className={`text-[9px] ${textMuted}`}>23:00</span>
              </div>
            </div>

            <div className={`${cardBg} border ${border} rounded-2xl p-4`}>
              <p className={`text-xs ${textMuted} mb-3`}>Detections by class</p>
              <div className="flex items-center gap-3">
                <div
                  className="w-16 h-16 rounded-full flex-shrink-0"
                  style={{ background: `conic-gradient(${conicStops})` }}
                />
                <div className="flex flex-col gap-1">
                  {classBreakdown.map((c) => (
                    <div key={c.label} className="flex items-center gap-1.5 text-[10px]">
                      <span className="w-2 h-2 rounded-full" style={{ background: c.color }} />
                      <span className={textMuted}>{c.label}</span>
                      <span className={`font-semibold ${textPrimary}`}>{c.pct}%</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className={`${cardBg} border ${border} rounded-2xl p-4`}>
              <p className={`text-xs ${textMuted} mb-3`}>Spray coverage over time</p>
              <svg viewBox="0 0 100 50" className="w-full h-24">
                <polyline
                  fill="none"
                  stroke={accentDot}
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  points={coveragePoints.map((v, i) => `${(i / (coveragePoints.length - 1)) * 100},${50 - (v / 100) * 46}`).join(" ")}
                />
              </svg>
              <p className={`text-[9px] ${textMuted} mt-1`}>Minutes elapsed →</p>
            </div>
          </div>

          {/* Detailed metrics table */}
          <div className={`${cardBg} border ${border} rounded-2xl p-4`}>
            <p className={`text-xs ${textMuted} mb-3`}>Detailed report</p>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {[
                ["Total flight time", "00:42:18"],
                ["Total distance", "0.49 km"],
                ["Area covered", "1.2 ha"],
                ["Spray events", "142"],
                ["No-spray events", "31"],
                ["Tea detections", "112"],
                ["Person detections", "9"],
                ["Animal detections", "6"],
                ["Avg spray confidence", "0.87"],
                ["Spray coverage", "74%"],
              ].map(([label, value]) => (
                <div key={label} className={`${inner} rounded-lg p-2.5`}>
                  <p className={`text-[10px] ${textMuted}`}>{label}</p>
                  <p className={`text-sm font-semibold ${textPrimary}`}>{value}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Export */}
          <div className={`${cardBg} border ${border} rounded-2xl p-4 flex flex-wrap items-center justify-between gap-3`}>
            <div className="flex flex-wrap gap-2">
              <button onClick={() => alert("Exporting PDF report")} className={`text-xs font-semibold px-4 py-2 rounded-lg ${accentBg} ${accentTextOn}`}>Download PDF report</button>
              <button onClick={() => alert("Exporting CSV data")} className={`text-xs font-semibold px-4 py-2 rounded-lg border ${border} ${textPrimary}`}>Download CSV data</button>
              <button onClick={() => window.print()} className={`text-xs font-semibold px-4 py-2 rounded-lg border ${border} ${textPrimary}`}>Print report</button>
            </div>
            <p className={`text-[10px] ${textMuted}`}>
              Generated {new Date().toLocaleString()} · Report ID RPT-{Math.floor(Math.random() * 9000 + 1000)}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}