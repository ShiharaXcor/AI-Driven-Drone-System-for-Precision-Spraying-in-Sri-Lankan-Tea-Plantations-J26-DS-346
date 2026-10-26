import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { AlertTriangle, Pause, Play, RotateCcw } from "lucide-react";
import useC4Styles from "./useC4Styles";
import { LEVELS, MATURITY_LABEL, getMission, listMissions } from "../api/c4";

// Pass 2 spray-flight SIMULATION. The drone follows a lawn-mower (serpentine) path over
// the areas in flight order and sprays each one at its prescribed rate. Real flight
// paths come from navigation (C3); real nozzle control from the spraying component (C2).

const CELL = 84;               // px per area in the map
const SIM_SECONDS_PER_AREA = 10; // assumed time over one area, for litres used
const SPEEDS = [0.5, 1, 2, 4];   // areas per second of real time at 1x = 1
const SPRAY_RADIUS = { low: 26, normal: 34, high: 41 };  // bigger cloud = higher rate

function layout(n) {
  const cols = Math.min(n, Math.max(1, Math.min(10, Math.ceil(Math.sqrt(n * 2)))));
  const rows = Math.ceil(n / cols);
  // serpentine: even rows left -> right, odd rows right -> left
  const pos = Array.from({ length: n }, (_, i) => {
    const r = Math.floor(i / cols), c = i % cols;
    const col = r % 2 === 0 ? c : cols - 1 - c;
    return { x: col * CELL + CELL / 2, y: r * CELL + CELL / 2, col, row: r };
  });
  return { cols, rows, pos };
}

const flowOf = (r) => r.flow_l_min ?? Math.round(r.rate_multiplier * 1.6 * 100) / 100;

function Drone({ x, y, t, spraying, level }) {
  const color = LEVELS[level]?.color || "#ffffff";
  const R = SPRAY_RADIUS[level] || 24;
  const pulse = 0.85 + 0.15 * Math.sin(t * 9);
  // deterministic droplets around the drone
  const drops = Array.from({ length: 18 }, (_, k) => {
    const a = k * 0.349 + t * (k % 2 ? 2.2 : -1.6), d = (R * (0.45 + ((k * 37) % 10) / 18)) * pulse;
    return { cx: x + Math.cos(a) * d, cy: y + Math.sin(a) * d, r: 1.8 + (k % 3) * 0.8 };
  });
  return (
    <g>
      {spraying && (
        <g>
          <circle cx={x} cy={y} r={R * pulse} fill={color} fillOpacity="0.35" stroke={color} strokeOpacity="0.9" strokeWidth="1.5" strokeDasharray="3 3" />
          <circle cx={x} cy={y} r={R * 0.7 * pulse} fill={color} fillOpacity="0.4" />
          {drops.map((d, k) => <circle key={k} cx={d.cx} cy={d.cy} r={d.r} fill={color} fillOpacity="0.9" />)}
        </g>
      )}
      <g transform={`translate(${x} ${y})`}>
        <line x1="-13" y1="-13" x2="13" y2="13" stroke="#1F241F" strokeWidth="3" strokeLinecap="round" />
        <line x1="13" y1="-13" x2="-13" y2="13" stroke="#1F241F" strokeWidth="3" strokeLinecap="round" />
        {[[-13, -13], [13, -13], [-13, 13], [13, 13]].map(([px, py], k) => (
          <g key={k}>
            <circle cx={px} cy={py} r="7" fill="#ffffff" fillOpacity="0.85" stroke="#1F241F" strokeWidth="1.5" />
            <line x1={px - 6 * Math.cos(t * 30 + k)} y1={py - 6 * Math.sin(t * 30 + k)}
              x2={px + 6 * Math.cos(t * 30 + k)} y2={py + 6 * Math.sin(t * 30 + k)} stroke="#1F241F" strokeWidth="1.2" />
          </g>
        ))}
        <rect x="-7" y="-7" width="14" height="14" rx="3" fill="#2C5F2D" stroke="#ffffff" strokeWidth="1.5" />
      </g>
    </g>
  );
}

export default function SprayFlight() {
  const s = useC4Styles();
  const [params, setParams] = useSearchParams();
  const missionId = params.get("mission");
  const [missions, setMissions] = useState([]);
  const [loaded, setLoaded] = useState({ id: null, p: null, error: "" });

  // simulation state
  const [progress, setProgress] = useState(0);     // 0..n (areas flown)
  const [running, setRunning] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [stopOnReview, setStopOnReview] = useState(true);
  const [waiting, setWaiting] = useState(null);    // area index awaiting operator confirmation
  const confirmed = useRef(new Set());
  const clock = useRef(0);
  const [t, setT] = useState(0);

  useEffect(() => { listMissions().then(setMissions).catch(() => {}); }, []);
  useEffect(() => {
    if (!missionId) return;
    let cancelled = false;
    getMission(missionId)
      .then((m) => !cancelled && setLoaded({ id: missionId, p: m, error: "" }))
      .catch((e) => !cancelled && setLoaded({ id: missionId, p: null, error: e.message }));
    return () => { cancelled = true; };
  }, [missionId]);

  const p = loaded.id === missionId ? loaded.p : null;
  const error = loaded.id === missionId ? loaded.error : "";
  const regions = useMemo(() => p?.regions ?? [], [p]);
  const n = regions.length;
  const geo = useMemo(() => layout(Math.max(n, 1)), [n]);

  const reset = useCallback(() => {
    setRunning(false); setProgress(0); setWaiting(null); confirmed.current = new Set();
  }, []);

  // animation loop
  useEffect(() => {
    if (!running || !n) return;
    let raf, last = performance.now();
    const step = (now) => {
      const dt = Math.min(0.1, (now - last) / 1000);
      last = now;
      clock.current += dt;
      setT(clock.current);
      setProgress((prev) => {
        let next = prev + dt * speed;
        // operator confirmation before spraying a flagged area
        if (stopOnReview) {
          const idx = Math.ceil(prev - 1e-9);
          const target = Math.floor(next);
          for (let i = Math.max(idx, 0); i <= Math.min(target, n - 1); i++) {
            if (regions[i].needs_review && !confirmed.current.has(i) && next >= i) {
              setWaiting(i); setRunning(false);
              return i;
            }
          }
        }
        if (next >= n) { setRunning(false); return n; }
        return next;
      });
      raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [running, speed, n, regions, stopOnReview]);

  // derived values
  const flying = progress > 0 && progress < n;
  const cur = Math.min(n - 1, Math.max(0, Math.floor(progress)));
  const segT = progress - Math.floor(progress);
  // the drone hovers over area i for the first 70% of its slot, then flies to i+1
  const move = Math.max(0, (segT - 0.7) / 0.3);
  const a = geo.pos[cur] || { x: CELL / 2, y: CELL / 2 };
  const b = geo.pos[Math.min(cur + 1, n - 1)] || a;
  const ease = move * move * (3 - 2 * move);
  const dx = progress >= n ? (geo.pos[n - 1]?.x ?? a.x) : a.x + (b.x - a.x) * ease;
  const dy = progress >= n ? (geo.pos[n - 1]?.y ?? a.y) : a.y + (b.y - a.y) * ease;
  const spraying = flying && waiting === null && segT < 0.7;

  // litres: each area gets flow x assumed seconds over it
  const litres = (r) => (flowOf(r) * SIM_SECONDS_PER_AREA) / 60;
  const fixedFlow = 1.6 * (p?.config?.rate_multiplier?.normal ?? 1);
  let used = 0, fixed = 0;
  regions.forEach((r, i) => {
    const frac = Math.max(0, Math.min(1, (progress - i) / 0.7));
    used += litres(r) * frac;
    fixed += ((fixedFlow * SIM_SECONDS_PER_AREA) / 60) * frac;
  });
  const sprayedAreas = regions.filter((_, i) => progress - i >= 0.7).length;
  const current = regions[cur];
  const finished = n > 0 && progress >= n;

  const header = (
    <div className="flex items-center justify-between flex-wrap gap-3">
      <div>
        <p className={`text-[10px] ${s.textMuted} uppercase tracking-wider`}>Pass 2 — spray flight (simulation)</p>
        <h1 className={`text-xl font-bold ${s.textPrimary}`}>Spray Flight</h1>
      </div>
      {missions.length > 0 && (
        <select value={missionId || ""} onChange={(e) => { reset(); setParams(e.target.value ? { mission: e.target.value } : {}); }}
          className={`text-xs ${s.cardBg} border ${s.border} ${s.textPrimary} rounded-full px-3 py-2 outline-none`}>
          <option value="">Choose a mission…</option>
          {missions.map((m) => <option key={m.mission_id} value={m.mission_id}>{m.mission_id} · {m.field}</option>)}
        </select>
      )}
    </div>
  );

  if (!missionId || error || !p) {
    return (
      <div className="flex flex-col gap-4">
        {header}
        <p className={`text-xs ${error ? "text-red-500" : s.textMuted}`}>
          {error || (missionId ? "Loading prescription…" :
            missions.length ? "Choose a mission to fly." : <>No missions yet — create one on the <Link className={s.accentText} to="/prescription">Prescription</Link> page.</>)}
        </p>
      </div>
    );
  }

  const W = geo.cols * CELL, H = geo.rows * CELL;
  const pathD = geo.pos.slice(0, n).map((q, i) => `${i ? "L" : "M"}${q.x} ${q.y}`).join(" ");
  const btn = `text-xs font-semibold px-4 py-2 rounded-full flex items-center gap-1.5`;

  return (
    <div className="flex flex-col gap-4">
      {header}

      <div className="flex items-center gap-2 flex-wrap">
        {!finished ? (
          <button onClick={() => { setWaiting(null); setRunning(!running); }} disabled={waiting !== null}
            className={`${btn} ${s.accentBg} ${s.accentTextOn} disabled:opacity-40`}>
            {running ? <><Pause className="w-3.5 h-3.5" /> Pause</> : <><Play className="w-3.5 h-3.5" /> {progress > 0 ? "Resume" : "Start spray flight"}</>}
          </button>
        ) : (
          <span className={`${btn} ${s.inner} ${s.textPrimary}`}>Flight complete</span>
        )}
        <button onClick={reset} className={`${btn} border ${s.border} ${s.textPrimary}`}>
          <RotateCcw className="w-3.5 h-3.5" /> Reset
        </button>
        <div className={`flex items-center gap-1 ${s.cardBg} border ${s.border} rounded-full p-1`}>
          {SPEEDS.map((v) => (
            <button key={v} onClick={() => setSpeed(v)}
              className={`text-[11px] px-2.5 py-1 rounded-full ${speed === v ? `${s.accentBg} ${s.accentTextOn} font-semibold` : s.textMuted}`}>
              {v}×
            </button>
          ))}
        </div>
        <label className={`flex items-center gap-2 text-xs ${s.textMuted} ml-1`}>
          <input type="checkbox" checked={stopOnReview} onChange={(e) => setStopOnReview(e.target.checked)} />
          Stop at review areas for operator confirmation
        </label>
      </div>

      {waiting !== null && (
        <div className="text-xs text-amber-600 bg-amber-500/10 border border-amber-500/40 rounded-xl p-3 flex items-center gap-3 flex-wrap">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          <span className="flex-1 min-w-48">
            Area {regions[waiting].region_id} needs review ({Math.round(regions[waiting].confidence * 100)}% confidence).
            The prescription uses the safe {LEVELS[regions[waiting].spray_level].label} level.
          </span>
          <button onClick={() => { confirmed.current.add(waiting); setWaiting(null); setRunning(true); }}
            className={`${btn} ${s.accentBg} ${s.accentTextOn}`}>Confirm and spray</button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className={`lg:col-span-2 self-start ${s.cardBg} border ${s.border} rounded-2xl p-4`}>
          <div className={`${s.inner} rounded-xl p-3 overflow-x-auto`}>
            <svg viewBox={`-6 -6 ${W + 12} ${H + 12}`} className="w-full max-h-[520px]" role="img"
              aria-label="Spray flight simulation over the prescription map">
              {regions.map((r, i) => {
                const q = geo.pos[i];
                const sprayed = progress - i >= 0.7;
                const lvl = LEVELS[r.spray_level];
                return (
                  <g key={r.region_id}>
                    <rect x={q.x - CELL / 2 + 3} y={q.y - CELL / 2 + 3} width={CELL - 6} height={CELL - 6} rx="6"
                      fill={lvl.color} fillOpacity={sprayed ? 0.95 : 0.3}
                      stroke={i === cur && flying ? (s.isDark ? "#ffffff" : "#1F241F") : "none"} strokeWidth="2.5" />
                    <text x={q.x - CELL / 2 + 10} y={q.y - CELL / 2 + 20} fontSize="12" fontWeight="700"
                      fill={sprayed ? "#ffffff" : (s.isDark ? "#e5e7eb" : "#1F241F")}>{lvl.short}</text>
                    <text x={q.x - CELL / 2 + 10} y={q.y + CELL / 2 - 10} fontSize="10"
                      fill={sprayed ? "#ffffff" : (s.isDark ? "#9497A0" : "#6B7268")}>#{r.region_id}</text>
                    {r.needs_review && (
                      <g>
                        <circle cx={q.x + CELL / 2 - 13} cy={q.y - CELL / 2 + 13} r="7" fill="#0D0E10" stroke="#fff" strokeWidth="1" />
                        <text x={q.x + CELL / 2 - 13} y={q.y - CELL / 2 + 16.5} fontSize="10" fontWeight="700" textAnchor="middle" fill="#fff">!</text>
                      </g>
                    )}
                    {sprayed && (
                      <text x={q.x + CELL / 2 - 10} y={q.y + CELL / 2 - 10} fontSize="12" textAnchor="end" fill="#ffffff">✓</text>
                    )}
                  </g>
                );
              })}
              <path d={pathD} fill="none" stroke={s.isDark ? "#ffffff" : "#1F241F"} strokeOpacity="0.35"
                strokeWidth="1.5" strokeDasharray="4 5" />
              <Drone x={dx} y={dy} t={t} spraying={spraying} level={current?.spray_level} />
            </svg>
          </div>
          <div className="flex gap-4 flex-wrap mt-3">
            {Object.entries(LEVELS).map(([k, l]) => (
              <span key={k} className="flex items-center gap-1.5 text-[10px]">
                <span className="w-2.5 h-2.5 rounded-full" style={{ background: l.color }} />
                <span className={s.textMuted}>{l.label.toUpperCase()} — spray ×{p.config?.rate_multiplier?.[k] ?? "?"}</span>
              </span>
            ))}
            <span className={`text-[10px] ${s.textMuted}`}>faded = planned · solid ✓ = sprayed · dashed line = flight path</span>
          </div>
        </div>

        <div className="flex flex-col gap-4">
          <div className={`${s.cardBg} border ${s.border} rounded-2xl p-4`}>
            <p className={`text-xs font-semibold ${s.textPrimary} mb-3`}>
              {finished ? "Flight complete" : flying || waiting !== null ? `Over area ${current.region_id}` : "Ready"}
            </p>
            {current && (
              <div className="grid grid-cols-2 gap-2">
                {[
                  ["Maturity", MATURITY_LABEL[current.maturity] || current.maturity],
                  ["Spray level", LEVELS[current.spray_level].label],
                  ["Rate", `×${current.rate_multiplier}`],
                  ["Nozzle flow", spraying ? `${flowOf(current)} L/min` : "0 L/min"],
                ].map(([l, v]) => (
                  <div key={l} className={`${s.inner} rounded-lg p-2.5`}>
                    <p className={`text-[9px] ${s.textMuted} uppercase`}>{l}</p>
                    <p className={`text-sm font-semibold ${s.textPrimary}`}
                      style={l === "Spray level" ? { color: LEVELS[current.spray_level].color } : undefined}>{v}</p>
                  </div>
                ))}
              </div>
            )}
            <div className="mt-3">
              <div className="flex justify-between mb-1">
                <span className={`text-[10px] ${s.textMuted}`}>Areas sprayed</span>
                <span className={`text-[10px] font-semibold ${s.textPrimary}`}>{sprayedAreas} / {n}</span>
              </div>
              <div className={`h-1.5 rounded-full ${s.isDark ? "bg-border" : "bg-light-border"}`}>
                <div className={`h-1.5 rounded-full ${s.accentBg}`} style={{ width: `${(sprayedAreas / n) * 100}%` }} />
              </div>
            </div>
          </div>

          <div className={`${s.cardBg} border ${s.border} rounded-2xl p-4`}>
            <p className={`text-xs font-semibold ${s.textPrimary} mb-3`}>Chemical used (simulated)</p>
            <div className="grid grid-cols-2 gap-2">
              <div className={`${s.inner} rounded-lg p-2.5`}>
                <p className={`text-[9px] ${s.textMuted} uppercase`}>Adaptive (C4)</p>
                <p className={`text-lg font-bold ${s.textPrimary}`}>{used.toFixed(2)} L</p>
              </div>
              <div className={`${s.inner} rounded-lg p-2.5`}>
                <p className={`text-[9px] ${s.textMuted} uppercase`}>Fixed rate</p>
                <p className={`text-lg font-bold ${s.textPrimary}`}>{fixed.toFixed(2)} L</p>
              </div>
            </div>
            {fixed > 0 && (() => {
              const diff = ((used - fixed) / fixed) * 100;
              return (
                <p className={`text-[11px] mt-2 ${s.textPrimary}`}>
                  {Math.abs(diff) < 0.05 ? "Same as fixed-rate spraying so far" : diff < 0
                    ? <>Saved <b>{Math.abs(diff).toFixed(1)}%</b> compared with fixed-rate spraying</>
                    : <>Used <b>{diff.toFixed(1)}%</b> more than fixed rate — dense mature canopy needs more</>}
                </p>
              );
            })()}
            <p className={`text-[10px] ${s.textMuted} mt-2`}>
              Assumes {SIM_SECONDS_PER_AREA} s over each area and the placeholder rates. Simulation only: the real flight
              path comes from navigation and nozzle control from the spraying component.
            </p>
          </div>

          <Link to={`/prescription?mission=${p.mission_id}`}
            className={`text-center text-xs font-semibold py-2.5 rounded-full border ${s.border} ${s.textPrimary}`}>
            Back to prescription map
          </Link>
        </div>
      </div>
    </div>
  );
}
