import { useEffect, useMemo, useState } from "react";
import { simulateMission, getWeather } from "../api.js";
import MissionMap from "../components/MissionMap.jsx";
import WindTimeline from "../components/WindTimeline.jsx";
import DecisionLog from "../components/DecisionLog.jsx";

const DROPLETS = ["VF-F", "F-M", "M-C", "C-VC"];
const REGIONS = ["Nuwara Eliya", "Badulla", "Kandy", "Ratnapura"];
const SPEEDS = [1, 5, 20];

const START = {
  center_lat: 6.955, center_lon: 80.775, length_m: 100, width_m: 60, row_bearing_deg: 0,
  swath_m: 5.5, height_m: 2.5, droplet_class: "F-M", speed_ms: 4, temp_c: 28, rh_pct: 70,
  wind_ms: 2.5, wind_dir_deg: 90, scenario: "gusty", max_drift_m: 20,
};

function Num({ label, value, min, max, step = 1, unit = "", onChange }) {
  return (
    <label className="field">
      <span className="field-row"><span>{label}</span><strong>{value}{unit}</strong></span>
      <input type="range" min={min} max={max} step={step} value={value} onChange={(e) => onChange(Number(e.target.value))} />
    </label>
  );
}

const mmss = (t) => `${String(Math.floor(t / 60)).padStart(2, "0")}:${String(Math.floor(t % 60)).padStart(2, "0")}`;

function StatusChip({ step }) {
  if (!step) return null;
  if (step.status === "HOLD") return <span className="chip critical">⏸ HOLD – strong wind</span>;
  if (step.mode === "CORRECT") return <span className="chip info">🔧 SPRAYING – correcting</span>;
  return <span className="chip good">✅ SPRAYING – no correction needed</span>;
}

export default function MissionView() {
  const [inp, setInp] = useState(START);
  const [mission, setMission] = useState(null);
  const [idx, setIdx] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(5);
  const [error, setError] = useState("");
  const [region, setRegion] = useState(REGIONS[0]);
  const [note, setNote] = useState("");

  const set = (k) => (v) => setInp((o) => ({ ...o, [k]: v }));

  const run = () => {
    setPlaying(false);
    setError("");
    simulateMission(inp)
      .then((m) => { setMission(m); setIdx(0); setPlaying(true); })
      .catch((e) => setError(`Backend not reachable: ${e.message}. Is the API running on port 8000?`));
  };

  // plan + simulate once when the page opens
  useEffect(() => { run(); }, []);   // eslint-disable-line react-hooks/exhaustive-deps

  // playback: one simulated second per tick, ticks faster at higher speed
  useEffect(() => {
    if (!playing || !mission) return;
    const timer = setInterval(() => {
      setIdx((i) => {
        if (i >= mission.steps.length - 1) { setPlaying(false); return i; }
        return i + 1;
      });
    }, 1000 / speed);
    return () => clearInterval(timer);
  }, [playing, speed, mission]);

  const loadWeather = () => {
    setNote("Loading live weather…");
    getWeather(region)
      .then((w) => {
        setInp((o) => ({ ...o, wind_ms: Math.min(w.wind_ms, 7), wind_dir_deg: Math.round(w.wind_dir_deg) % 360,
                         temp_c: w.temp_c, rh_pct: Math.round(w.rh_pct), scenario: "steady" }));
        setNote(`Live weather for ${w.region} (${w.time}) – press "Plan & simulate"`);
      })
      .catch((e) => setNote(`Could not load live weather: ${e.message}`));
  };

  const step = mission?.steps[idx];
  const t = step?.t ?? 0;
  const eventsSoFar = useMemo(() => (mission ? mission.events.filter((e) => e.t <= t) : []), [mission, t]);
  const done = mission && idx >= mission.steps.length - 1;
  const side = (s) => (s ? ` ${s}` : "");

  return (
    <div className="layout">
      {/* ---------------- left: mission set-up ---------------- */}
      <aside className="sidebar">
        <h2>1. Field</h2>
        <Num label="Field length (along rows)" unit=" m" value={inp.length_m} min={30} max={300} step={10} onChange={set("length_m")} />
        <Num label="Field width" unit=" m" value={inp.width_m} min={10} max={150} step={5} onChange={set("width_m")} />
        <Num label="Row direction" unit="°" value={inp.row_bearing_deg} min={0} max={179} onChange={set("row_bearing_deg")} />

        <h2>2. Drone</h2>
        <Num label="Flight height" unit=" m" value={inp.height_m} min={2} max={3.5} step={0.1} onChange={set("height_m")} />
        <Num label="Swath width" unit=" m" value={inp.swath_m} min={4.8} max={6.4} step={0.1} onChange={set("swath_m")} />
        <Num label="Flight speed" unit=" m/s" value={inp.speed_ms} min={1} max={7} step={0.5} onChange={set("speed_ms")} />
        <label className="field">
          <span>Droplet class (fine → coarse)</span>
          <select value={inp.droplet_class} onChange={(e) => set("droplet_class")(e.target.value)}>
            {DROPLETS.map((d) => <option key={d}>{d}</option>)}
          </select>
        </label>

        <h2>3. Weather</h2>
        <label className="field">
          <span>Wind scenario</span>
          <select value={inp.scenario} onChange={(e) => set("scenario")(e.target.value)}>
            <option value="gusty">Gusty (rising wind + one strong gust)</option>
            <option value="steady">Steady wind</option>
            <option value="calm">Calm</option>
          </select>
        </label>
        <label className="field">
          <span>Tea region (live weather)</span>
          <select value={region} onChange={(e) => setRegion(e.target.value)}>
            {REGIONS.map((x) => <option key={x}>{x}</option>)}
          </select>
        </label>
        <button onClick={loadWeather}>Use live weather (Open-Meteo)</button>
        {note && <p className="note">{note}</p>}
        <Num label="Base wind at 2 m" unit=" m/s" value={inp.wind_ms} min={0} max={6} step={0.1} onChange={set("wind_ms")} />
        <Num label="Wind comes FROM" unit="°" value={inp.wind_dir_deg} min={0} max={359} onChange={set("wind_dir_deg")} />
        <Num label="Temperature" unit=" °C" value={inp.temp_c} min={8} max={36} step={0.5} onChange={set("temp_c")} />
        <Num label="Relative humidity" unit=" %" value={inp.rh_pct} min={20} max={100} onChange={set("rh_pct")} />
        <Num label="Max acceptable drift" unit=" m" value={inp.max_drift_m} min={5} max={40} onChange={set("max_drift_m")} />

        <button className="primary" onClick={run}>▶ Plan &amp; simulate mission</button>
      </aside>

      {/* ---------------- right: mission ---------------- */}
      <main className="main wide">
        {error && <div className="banner critical">⚠️ {error}</div>}
        {mission && step && (
          <>
            <div className="playbar">
              <button className="icon" onClick={() => (done ? (setIdx(0), setPlaying(true)) : setPlaying((p) => !p))}>
                {playing ? "⏸ Pause" : done ? "↻ Replay" : "▶ Play"}
              </button>
              <div className="speeds">
                {SPEEDS.map((s) => (
                  <button key={s} className={speed === s ? "icon active" : "icon"} onClick={() => setSpeed(s)}>×{s}</button>
                ))}
              </div>
              <input type="range" className="scrub" min={0} max={mission.steps.length - 1} value={idx}
                     onChange={(e) => { setPlaying(false); setIdx(Number(e.target.value)); }} aria-label="Mission time" />
              <span className="clock">{mmss(t)} / {mmss(mission.summary.duration_s)}</span>
            </div>

            <div className="mission-grid">
              <section className="card map-card">
                <MissionMap mission={mission} idx={idx} />
              </section>

              <section className="card live">
                <div className="live-head">
                  <StatusChip step={step} />
                  <span className="sub">Line {step.line}/{mission.summary.lines} · heading {step.heading_deg}°</span>
                </div>
                <div className="live-grid">
                  <div><span>Wind</span><b>{step.wind_ms} m/s from {step.wind_dir_deg}°</b></div>
                  <div><span>Crosswind used for the decision</span><b>{step.crosswind_ms} m/s from {step.wind_from_side}</b></div>
                  <div><span>Predicted drift</span><b>{step.drift_m == null ? "–" : `${step.drift_m} m`}{step.drift_risk === "HIGH" ? " ⚠️" : ""}</b></div>
                  <div><span>Nozzle tilt</span><b>{step.nozzle_tilt_deg}°{side(step.nozzle_tilt_side)}</b></div>
                  <div><span>Path offset</span><b>{step.path_offset_m} m{side(step.path_offset_side)}</b></div>
                  <div><span>Spray off target</span>
                    <b>{step.status === "HOLD" ? "– (paused)" : `${step.miss_uncorrected_m} m → ${step.miss_corrected_m} m`}</b></div>
                </div>
                {step.droplet_advice && step.status !== "HOLD" && (
                  <p className="advice">⚠️ Advice: switch to <b>{step.droplet_advice}</b> droplets</p>
                )}
                {step.height_advice && <p className="advice">⚠️ Advice: fly at {step.height_advice} m or lower</p>}
              </section>

              <section className="card">
                <h3>Wind during the mission</h3>
                <WindTimeline steps={mission.steps} t={t} limit={mission.strong_wind_ms} />
              </section>

              <section className="card">
                <h3>Decision log</h3>
                <DecisionLog events={eventsSoFar} />
              </section>
            </div>

            {done && (
              <section className="card summary">
                <h3>Mission summary</h3>
                <div className="summary-grid">
                  <div><span>Lines sprayed</span><b>{mission.summary.lines_completed}/{mission.summary.lines}</b></div>
                  <div><span>Duration</span><b>{mmss(mission.summary.duration_s)}</b></div>
                  <div><span>Time on hold (strong wind)</span><b>{mission.summary.hold_s} s</b></div>
                  <div><span>Spray time with correction</span><b>{mission.summary.corrected_share_pct} %</b></div>
                  <div><span>Average spray miss</span>
                    <b>{mission.summary.mean_miss_uncorrected_m} m → {mission.summary.mean_miss_corrected_m} m</b></div>
                  <div><span>Time with high drift risk</span><b>{mission.summary.high_drift_share_pct} %</b></div>
                </div>
                <p className="sub">"Spray miss" = how far the spray lands from its target line, without → with correction
                  (simple physics model). This simulates the decision system, not the spray itself.</p>
              </section>
            )}
          </>
        )}
      </main>
    </div>
  );
}
