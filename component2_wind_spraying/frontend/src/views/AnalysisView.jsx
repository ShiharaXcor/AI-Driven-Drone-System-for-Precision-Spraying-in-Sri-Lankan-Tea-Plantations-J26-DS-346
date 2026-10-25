import { useEffect, useState } from "react";
import { getRecommendation, getDriftCurve, getWeather } from "../api.js";
import TopView from "../components/TopView.jsx";
import DriftChart from "../components/DriftChart.jsx";
import { Stat, Num, DecisionCard } from "../components/ui.jsx";

const DROPLETS = ["VF-F", "F-M", "M-C", "C-VC"];
const REGIONS = ["Nuwara Eliya", "Badulla", "Kandy", "Ratnapura"];

const START = {
  wind_ms: 2.0, wind_dir_deg: 90, heading_deg: 0, temp_c: 28, rh_pct: 70,
  height_m: 2.5, swath_m: 5.5, droplet_class: "F-M", max_drift_m: 20,
};

function decisionOf(r) {
  if (r.mode === "STRONG_WIND") return { tone: "danger", label: "HOLD", text: "Wind too strong – do not spray now." };
  if (r.mode === "NO_CORRECTION") return { tone: "good", label: "SPRAY", text: "Wind is along the line – no correction needed." };
  const side = r.nozzle_tilt_side ? ` ${r.nozzle_tilt_side}` : "";
  return { tone: "accent", label: "SPRAY · CORRECTED",
           text: `Tilt nozzle ${r.nozzle_tilt_deg}°${side}` + (r.path_offset_m ? ` · move path ${r.path_offset_m} m${side}` : "") };
}

export default function AnalysisView() {
  const [inp, setInp] = useState(START);
  const [region, setRegion] = useState(REGIONS[0]);
  const [result, setResult] = useState(null);
  const [curve, setCurve] = useState([]);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");

  const set = (key) => (value) => setInp((old) => ({ ...old, [key]: value }));

  // Ask the backend for a new recommendation whenever an input changes (small delay = fewer calls)
  useEffect(() => {
    const t = setTimeout(() => {
      getRecommendation(inp).then((r) => { setResult(r); setError(""); })
                            .catch((e) => setError(`Backend not reachable: ${e.message}. Is the API running on port 8000?`));
    }, 150);
    return () => clearTimeout(t);
  }, [inp]);

  // The drift curves only depend on height, swath, temperature and humidity
  useEffect(() => {
    const t = setTimeout(() => {
      getDriftCurve({ height_m: inp.height_m, swath_m: inp.swath_m, temp_c: inp.temp_c, rh_pct: inp.rh_pct })
        .then((c) => setCurve(c.rows)).catch(() => {});
    }, 250);
    return () => clearTimeout(t);
  }, [inp.height_m, inp.swath_m, inp.temp_c, inp.rh_pct]);

  const loadWeather = () => {
    setNote("Loading live weather…");
    getWeather(region)
      .then((w) => {
        setInp((old) => ({ ...old, wind_ms: Math.min(w.wind_ms, 7), wind_dir_deg: Math.round(w.wind_dir_deg) % 360,
                           temp_c: w.temp_c, rh_pct: Math.round(w.rh_pct) }));
        setNote(`Live weather for ${w.region} (${w.time})`);
      })
      .catch((e) => setNote(`Could not load live weather: ${e.message}`));
  };

  const r = result;
  const side = (s) => (s ? ` ${s}` : "");
  const dec = r && decisionOf(r);

  return (
    <>
      {/* ---------------- top stats ---------------- */}
      <section className="stats five">
        <Stat label="Predicted drift" value={r ? (r.drift_m == null ? "–" : `${r.drift_m} m`) : "–"} />
        <Stat label="Crosswind" value={r ? `${r.crosswind_ms} m/s${r.wind_from_side ? ` from ${r.wind_from_side}` : ""}` : "–"} />
        <Stat label="Spray lands off target" value={r ? `${r.spray_shift_m} m` : "–"} />
        <Stat label="Nozzle tilt" value={r ? `${r.nozzle_tilt_deg}°${side(r.nozzle_tilt_side)}` : "–"} />
        <Stat label="Path offset" value={r ? `${r.path_offset_m} m${side(r.path_offset_side)}` : "–"} />
      </section>

      {error && <div className="notice danger">{error}</div>}
      {r?.drift_risk === "HIGH" && (
        <div className="notice warn">
          High drift: predicted {r.drift_m} m is above the {inp.max_drift_m} m limit.{" "}
          {r.droplet_advice ? `Switch to ${r.droplet_advice} droplets.` : "No droplet class brings it under the limit – consider not spraying now."}
        </div>
      )}
      {r?.height_advice && <div className="notice warn">Fly at {r.height_advice} m or lower to reduce drift.</div>}

      {/* ---------------- settings ---------------- */}
      <section className="card">
        <h3 className="card-title">Conditions — one moment, one flight line</h3>
        <div className="setup-grid">
          <fieldset>
            <legend>Live weather</legend>
            <label className="field">
              <span>Tea region</span>
              <select value={region} onChange={(e) => setRegion(e.target.value)}>
                {REGIONS.map((x) => <option key={x}>{x}</option>)}
              </select>
            </label>
            <button className="btn primary" onClick={loadWeather}>Get live weather</button>
            {note && <p className="hint">{note}</p>}
          </fieldset>
          <fieldset>
            <legend>Weather</legend>
            <Num label="Wind speed at 2 m" unit=" m/s" value={inp.wind_ms} min={0} max={7} step={0.1} onChange={set("wind_ms")} />
            <Num label="Wind comes FROM" unit="°" value={inp.wind_dir_deg} min={0} max={359} onChange={set("wind_dir_deg")} />
            <Num label="Temperature" unit=" °C" value={inp.temp_c} min={8} max={36} step={0.5} onChange={set("temp_c")} />
            <Num label="Relative humidity" unit=" %" value={inp.rh_pct} min={20} max={100} onChange={set("rh_pct")} />
          </fieldset>
          <fieldset>
            <legend>Drone</legend>
            <Num label="Flight heading (flies TO)" unit="°" value={inp.heading_deg} min={0} max={359} onChange={set("heading_deg")} />
            <Num label="Flight height" unit=" m" value={inp.height_m} min={2} max={3.5} step={0.1} onChange={set("height_m")} />
            <Num label="Swath width" unit=" m" value={inp.swath_m} min={4.8} max={6.4} step={0.1} onChange={set("swath_m")} />
            <label className="field">
              <span>Droplet class (fine → coarse)</span>
              <select value={inp.droplet_class} onChange={(e) => set("droplet_class")(e.target.value)}>
                {DROPLETS.map((d) => <option key={d}>{d}</option>)}
              </select>
            </label>
          </fieldset>
          <fieldset>
            <legend>Safety limit</legend>
            <Num label="Max acceptable drift" unit=" m" value={inp.max_drift_m} min={5} max={40} onChange={set("max_drift_m")} />
          </fieldset>
        </div>
      </section>

      {r && (
        <>
          {/* ---------------- top view + decision ---------------- */}
          <div className="row-main">
            <section className="card">
              <div className="card-head"><h3>Top view — spray correction</h3></div>
              <TopView r={r} wind={inp.wind_ms} windDir={inp.wind_dir_deg} heading={inp.heading_deg} swath={inp.swath_m} />
            </section>
            <DecisionCard tone={dec.tone} label={dec.label} text={dec.text}>
              <p className="decision-text small">{r.reason}</p>
            </DecisionCard>
          </div>

          {/* ---------------- drift chart ---------------- */}
          <section className="card">
            <h3 className="card-title">Predicted drift vs crosswind</h3>
            <p className="caption">Height {inp.height_m} m · {inp.temp_c} °C · {inp.rh_pct} % RH. Coarser droplets drift much less at the same wind.</p>
            <DriftChart rows={curve} limit={inp.max_drift_m} current={r} droplet={inp.droplet_class} />
          </section>
        </>
      )}
    </>
  );
}
