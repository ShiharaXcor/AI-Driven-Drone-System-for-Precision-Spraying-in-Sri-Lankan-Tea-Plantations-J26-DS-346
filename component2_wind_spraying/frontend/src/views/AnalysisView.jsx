import { useEffect, useState } from "react";
import { getRecommendation, getDriftCurve, getWeather } from "../api.js";
import TopView from "../components/TopView.jsx";
import DriftChart from "../components/DriftChart.jsx";

const DROPLETS = ["VF-F", "F-M", "M-C", "C-VC"];
const REGIONS = ["Nuwara Eliya", "Badulla", "Kandy", "Ratnapura"];

const START = {
  wind_ms: 2.0, wind_dir_deg: 90, heading_deg: 0, temp_c: 28, rh_pct: 70,
  height_m: 2.5, swath_m: 5.5, droplet_class: "F-M", max_drift_m: 20,
};

// One labelled slider
function Slider({ label, value, min, max, step = 1, unit = "", onChange }) {
  return (
    <label className="field">
      <span className="field-row">
        <span>{label}</span>
        <strong>{value}{unit}</strong>
      </span>
      <input type="range" min={min} max={max} step={step} value={value}
             onChange={(e) => onChange(Number(e.target.value))} />
    </label>
  );
}

// Coloured banner for the decision (icon + label, never colour alone)
function Banner({ r }) {
  if (r.mode === "STRONG_WIND")
    return <div className="banner critical">⛔ <b>STRONG WIND</b> – {r.reason} A decision from the flight/mission side is needed.</div>;
  if (r.mode === "NO_CORRECTION")
    return <div className="banner good">✅ <b>NO CORRECTION NEEDED</b> – {r.reason}</div>;
  return <div className="banner info">🔧 <b>CORRECTION</b> – {r.reason}</div>;
}

function Metric({ label, value }) {
  return (
    <div className="metric">
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value}</div>
    </div>
  );
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
  const side = (s) => (s ? ` (${s})` : "");

  return (
    <div className="layout">
      {/* ---------------- left: inputs ---------------- */}
      <aside className="sidebar">
        <h2>1. Weather</h2>
        <label className="field">
          <span>Tea region (for live weather)</span>
          <select value={region} onChange={(e) => setRegion(e.target.value)}>
            {REGIONS.map((x) => <option key={x}>{x}</option>)}
          </select>
        </label>
        <button onClick={loadWeather}>Get live weather (Open-Meteo)</button>
        {note && <p className="note">{note}</p>}
        <Slider label="Wind speed at 2 m" unit=" m/s" value={inp.wind_ms} min={0} max={7} step={0.1} onChange={set("wind_ms")} />
        <Slider label="Wind comes FROM (0 = N, 90 = E)" unit="°" value={inp.wind_dir_deg} min={0} max={359} onChange={set("wind_dir_deg")} />
        <Slider label="Temperature" unit=" °C" value={inp.temp_c} min={8} max={36} step={0.5} onChange={set("temp_c")} />
        <Slider label="Relative humidity" unit=" %" value={inp.rh_pct} min={20} max={100} onChange={set("rh_pct")} />

        <h2>2. Drone settings</h2>
        <Slider label="Flight heading (direction it flies TO)" unit="°" value={inp.heading_deg} min={0} max={359} onChange={set("heading_deg")} />
        <Slider label="Flight height" unit=" m" value={inp.height_m} min={2} max={3.5} step={0.1} onChange={set("height_m")} />
        <Slider label="Swath width" unit=" m" value={inp.swath_m} min={4.8} max={6.4} step={0.1} onChange={set("swath_m")} />
        <label className="field">
          <span>Droplet class (fine → coarse)</span>
          <select value={inp.droplet_class} onChange={(e) => set("droplet_class")(e.target.value)}>
            {DROPLETS.map((d) => <option key={d}>{d}</option>)}
          </select>
        </label>

        <h2>3. Safety limit</h2>
        <Slider label="Max acceptable drift" unit=" m" value={inp.max_drift_m} min={5} max={40} onChange={set("max_drift_m")} />
      </aside>

      {/* ---------------- right: results ---------------- */}
      <main className="main">
        <header>
          <h1>Analysis – one moment, one flight line</h1>
          <p className="sub">Component 2 · drift prediction (XGBoost trained on AgDRIFT) + physics-based correction</p>
        </header>

        {error && <div className="banner critical">⚠️ {error}</div>}

        {r && (
          <>
            <Banner r={r} />
            {r.drift_risk === "HIGH" && (
              <div className="banner warning">
                ⚠️ <b>HIGH DRIFT</b> – predicted {r.drift_m} m is above the {inp.max_drift_m} m limit.{" "}
                {r.droplet_advice ? <>Switch to <b>{r.droplet_advice}</b> droplets.</>
                                  : <>No droplet class brings it under the limit – consider not spraying now.</>}
              </div>
            )}
            {r.height_advice && <div className="banner warning">⚠️ Fly at {r.height_advice} m or lower to reduce drift.</div>}

            <section className="metrics">
              <Metric label="Predicted drift distance" value={r.drift_m == null ? "–" : `${r.drift_m} m`} />
              <Metric label={`Crosswind (from ${r.wind_from_side})`} value={`${r.crosswind_ms} m/s`} />
              <Metric label="Spray lands off target" value={`${r.spray_shift_m} m`} />
              <Metric label={`Nozzle tilt${side(r.nozzle_tilt_side)}`} value={`${r.nozzle_tilt_deg}°`} />
              <Metric label={`Path offset${side(r.path_offset_side)}`} value={`${r.path_offset_m} m`} />
            </section>

            <section className="card">
              <h3>Top view (relative to the drone)</h3>
              <TopView r={r} wind={inp.wind_ms} windDir={inp.wind_dir_deg} heading={inp.heading_deg} swath={inp.swath_m} />
            </section>

            <section className="card">
              <h3>Predicted drift vs crosswind</h3>
              <p className="sub">Height {inp.height_m} m · {inp.temp_c} °C · {inp.rh_pct} % RH. Coarser droplets drift much less at the same wind.</p>
              <DriftChart rows={curve} limit={inp.max_drift_m} current={r} droplet={inp.droplet_class} />
            </section>

            <details className="card">
              <summary>Full output (what the shared frontend will receive)</summary>
              <pre>{JSON.stringify(r, null, 2)}</pre>
            </details>

            <section className="card">
              <h3>Validation</h3>
              <p>Model: XGBoost, test R² 0.99, MAE 0.8 m (5,000 AgDRIFT runs driven by real Sri Lankan weather).
                 Real flights (Suleco, 564): 89.2 % inside the training ranges; coarse droplets removed all worst-case drift above 30 m.</p>
              <p className="sub">Limitations: no measured drift in Suleco data; AgDRIFT uses a manned-helicopter proxy (conservative);
                 nozzle-tilt and downwash values are assumptions to be calibrated in a field trial.</p>
            </section>
          </>
        )}
      </main>
    </div>
  );
}
