import { useEffect, useMemo, useState } from "react";
import { simulateMission, getWeather } from "../api.js";
import MissionMap from "../components/MissionMap.jsx";
import WindTimeline from "../components/WindTimeline.jsx";
import DecisionLog from "../components/DecisionLog.jsx";
import { Stat, Tile, Num, DecisionCard } from "../components/ui.jsx";

const DROPLETS = ["VF-F", "F-M", "M-C", "C-VC"];
const REGIONS = ["Nuwara Eliya", "Badulla", "Kandy", "Ratnapura"];
const SPEEDS = [1, 5, 20];

const START = {
  center_lat: 6.955, center_lon: 80.775, length_m: 100, width_m: 60, row_bearing_deg: 0,
  swath_m: 5.5, height_m: 2.5, droplet_class: "F-M", speed_ms: 4, temp_c: 28, rh_pct: 70,
  wind_ms: 2.5, wind_dir_deg: 90, scenario: "gusty", max_drift_m: 20,
};

const mmss = (t) => `${String(Math.floor(t / 60)).padStart(2, "0")}:${String(Math.floor(t % 60)).padStart(2, "0")}`;

// What the big coloured card shows for the current moment
function decisionOf(step) {
  if (!step) return null;
  const side = step.nozzle_tilt_side ? ` ${step.nozzle_tilt_side}` : "";
  if (step.status === "HOLD")
    return { tone: "danger", label: "HOLD", text: `Wind ${step.decision_wind_ms} m/s is too strong – spraying paused` };
  if (step.mode === "CORRECT")
    return { tone: "accent", label: "SPRAY · CORRECTED",
             text: `Tilt nozzle ${step.nozzle_tilt_deg}°${side}` + (step.path_offset_m ? ` · move path ${step.path_offset_m} m${side}` : "") };
  return { tone: "good", label: "SPRAY", text: "Wind is along the line – no correction needed" };
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
        setNote(`Live weather for ${w.region} (${w.time}) loaded – press "Plan & simulate".`);
      })
      .catch((e) => setNote(`Could not load live weather: ${e.message}`));
  };

  const step = mission?.steps[idx];
  const t = step?.t ?? 0;
  const eventsSoFar = useMemo(() => (mission ? mission.events.filter((e) => e.t <= t) : []), [mission, t]);
  const alerts = eventsSoFar.filter((e) => e.kind === "critical" || e.kind === "warning").length;
  const done = mission && idx >= mission.steps.length - 1;
  const side = (s) => (s ? ` ${s}` : "");
  const dec = decisionOf(step);

  return (
    <>
      {/* ---------------- top stats ---------------- */}
      <section className="stats">
        <Stat label="Mission time" value={mission ? `${mmss(t)} / ${mmss(mission.summary.duration_s)}` : "–"} />
        <Stat label="Flight line" value={step ? `${step.line} / ${mission.summary.lines}` : "–"} />
        <Stat label="Spray status" value={step ? (step.status === "HOLD" ? "PAUSED" : "ON") : "–"} />
        <Stat label="Alert count" value={mission ? alerts : "–"} />
      </section>

      {error && <div className="notice danger">{error}</div>}

      {/* ---------------- mission setup (collapsible) ---------------- */}
      <details className="card setup">
        <summary>
          <span>Mission setup <small>field · drone · weather</small></span>
          <span className="summary-hint">click to change</span>
        </summary>
        <div className="setup-grid">
          <fieldset>
            <legend>Field</legend>
            <Num label="Field length" unit=" m" value={inp.length_m} min={30} max={300} step={10} onChange={set("length_m")} />
            <Num label="Field width" unit=" m" value={inp.width_m} min={10} max={150} step={5} onChange={set("width_m")} />
            <Num label="Row direction" unit="°" value={inp.row_bearing_deg} min={0} max={179} onChange={set("row_bearing_deg")} />
          </fieldset>
          <fieldset>
            <legend>Drone</legend>
            <Num label="Flight height" unit=" m" value={inp.height_m} min={2} max={3.5} step={0.1} onChange={set("height_m")} />
            <Num label="Swath width" unit=" m" value={inp.swath_m} min={4.8} max={6.4} step={0.1} onChange={set("swath_m")} />
            <Num label="Flight speed" unit=" m/s" value={inp.speed_ms} min={1} max={7} step={0.5} onChange={set("speed_ms")} />
            <label className="field">
              <span>Droplet class (fine → coarse)</span>
              <select value={inp.droplet_class} onChange={(e) => set("droplet_class")(e.target.value)}>
                {DROPLETS.map((d) => <option key={d}>{d}</option>)}
              </select>
            </label>
          </fieldset>
          <fieldset>
            <legend>Weather</legend>
            <label className="field">
              <span>Wind scenario</span>
              <select value={inp.scenario} onChange={(e) => set("scenario")(e.target.value)}>
                <option value="gusty">Gusty (rising wind + one strong gust)</option>
                <option value="steady">Steady wind</option>
                <option value="calm">Calm</option>
              </select>
            </label>
            <Num label="Base wind at 2 m" unit=" m/s" value={inp.wind_ms} min={0} max={6} step={0.1} onChange={set("wind_ms")} />
            <Num label="Wind comes FROM" unit="°" value={inp.wind_dir_deg} min={0} max={359} onChange={set("wind_dir_deg")} />
            <Num label="Temperature" unit=" °C" value={inp.temp_c} min={8} max={36} step={0.5} onChange={set("temp_c")} />
            <Num label="Relative humidity" unit=" %" value={inp.rh_pct} min={20} max={100} onChange={set("rh_pct")} />
          </fieldset>
          <fieldset>
            <legend>Live weather &amp; limit</legend>
            <label className="field">
              <span>Tea region</span>
              <select value={region} onChange={(e) => setRegion(e.target.value)}>
                {REGIONS.map((x) => <option key={x}>{x}</option>)}
              </select>
            </label>
            <button className="btn" onClick={loadWeather}>Use live weather</button>
            {note && <p className="hint">{note}</p>}
            <Num label="Max acceptable drift" unit=" m" value={inp.max_drift_m} min={5} max={40} onChange={set("max_drift_m")} />
          </fieldset>
        </div>
        <div className="setup-actions">
          <button className="btn primary" onClick={run}>Plan &amp; simulate mission</button>
        </div>
      </details>

      {mission && step && (
        <>
          {/* ---------------- map + decision ---------------- */}
          <div className="row-main">
            <section className="card">
              <div className="card-head">
                <h3>Live map — Field</h3>
                <div className="card-tools">
                  <span className="tag">{playing ? "Live" : done ? "Finished" : "Paused"}</span>
                  {SPEEDS.map((s) => (
                    <button key={s} className={speed === s ? "btn sm on" : "btn sm"} onClick={() => setSpeed(s)}>×{s}</button>
                  ))}
                  <button className="btn sm primary" onClick={() => (done ? (setIdx(0), setPlaying(true)) : setPlaying((p) => !p))}>
                    {playing ? "Pause" : done ? "Replay" : "Play"}
                  </button>
                </div>
              </div>
              <div className="map-box"><MissionMap mission={mission} idx={idx} /></div>
              <input type="range" className="scrub" min={0} max={mission.steps.length - 1} value={idx}
                     onChange={(e) => { setPlaying(false); setIdx(Number(e.target.value)); }} aria-label="Mission time" />
              <p className="caption">Line {step.line}/{mission.summary.lines} · heading {step.heading_deg}° ·
                wind {step.wind_ms} m/s from {step.wind_dir_deg}° · {mmss(t)}</p>
            </section>

            <DecisionCard tone={dec.tone} label={dec.label} text={dec.text} />
          </div>

          {/* ---------------- telemetry ---------------- */}
          <section className="card">
            <h3 className="card-title">Spray telemetry</h3>
            <div className="tiles">
              <Tile label="Crosswind used" value={`${step.crosswind_ms} m/s${step.wind_from_side ? ` from ${step.wind_from_side}` : ""}`} />
              <Tile label="Predicted drift" value={step.drift_m == null ? "–" : `${step.drift_m} m${step.drift_risk === "HIGH" ? " ⚠" : ""}`} />
              <Tile label="Nozzle tilt" value={`${step.nozzle_tilt_deg}°${side(step.nozzle_tilt_side)}`} />
              <Tile label="Path offset" value={`${step.path_offset_m} m${side(step.path_offset_side)}`} />
              <Tile label="Spray off target"
                    value={step.status === "HOLD" ? "– (paused)" : `${step.miss_uncorrected_m} m → ${step.miss_corrected_m} m`} />
            </div>
            {step.droplet_advice && step.status !== "HOLD" && (
              <div className="notice warn">Advice: switch to {step.droplet_advice} droplets to reduce drift.</div>
            )}
            {step.height_advice && <div className="notice warn">Advice: fly at {step.height_advice} m or lower.</div>}
          </section>

          {/* ---------------- wind + log ---------------- */}
          <div className="row-2">
            <section className="card">
              <h3 className="card-title">Wind during the mission</h3>
              <WindTimeline steps={mission.steps} t={t} limit={mission.strong_wind_ms} />
            </section>
            <section className="card">
              <h3 className="card-title">Decision log</h3>
              <DecisionLog events={eventsSoFar} />
            </section>
          </div>

          {done && (
            <section className="card">
              <h3 className="card-title">Mission summary</h3>
              <div className="tiles three">
                <Tile label="Lines sprayed" value={`${mission.summary.lines_completed}/${mission.summary.lines}`} />
                <Tile label="Duration" value={mmss(mission.summary.duration_s)} />
                <Tile label="Time on hold (strong wind)" value={`${mission.summary.hold_s} s`} />
                <Tile label="Spray time with correction" value={`${mission.summary.corrected_share_pct} %`} />
                <Tile label="Average spray miss" value={`${mission.summary.mean_miss_uncorrected_m} m → ${mission.summary.mean_miss_corrected_m} m`} />
                <Tile label="Time with high drift risk" value={`${mission.summary.high_drift_share_pct} %`} />
              </div>
              <p className="caption">Spray miss = how far the spray lands from its target line, without → with correction.</p>
            </section>
          )}
        </>
      )}
    </>
  );
}
