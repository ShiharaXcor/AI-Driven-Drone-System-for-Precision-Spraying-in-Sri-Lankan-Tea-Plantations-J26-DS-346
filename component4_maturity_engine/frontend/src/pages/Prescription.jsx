import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { AlertTriangle, Download, Loader2, MapPin, Upload } from "lucide-react";
import useC4Styles from "./useC4Styles";
import {
  LEVELS, MATURITY_LABEL, createPrescription, downloadFile, getMission,
  imageUrl, listMissions, prescriptionCsv,
} from "../api/c4";

function NewMapping({ s, onDone }) {
  const [files, setFiles] = useState([]);
  const [field, setField] = useState("Nuwara Estate — Block 7");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function run() {
    setBusy(true);
    setError("");
    try {
      const p = await createPrescription(files, field);
      onDone(p);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={`${s.cardBg} border ${s.border} rounded-2xl p-4 max-w-2xl`}>
      <p className={`text-xs font-semibold ${s.textPrimary} mb-1`}>Pass 1 — Mapping & maturity classification</p>
      <p className={`text-[11px] ${s.textMuted} mb-4`}>
        Upload the mapping-flight photos. Each photo is one region: the model classifies its maturity
        and the engine sets the spray level.
      </p>

      <label className={`text-[10px] ${s.textMuted} uppercase`}>Field / block</label>
      <input
        value={field}
        onChange={(e) => setField(e.target.value)}
        className={`w-full mt-1 mb-3 ${s.inner} border ${s.border} rounded-lg px-3 py-2 text-xs ${s.textPrimary} outline-none`}
      />

      <label
        className={`flex flex-col items-center justify-center gap-2 ${s.inner} border border-dashed ${s.border} rounded-xl py-8 cursor-pointer`}
      >
        <Upload className={`w-5 h-5 ${s.accentText}`} />
        <span className={`text-xs ${s.textPrimary}`}>
          {files.length ? `${files.length} photo${files.length > 1 ? "s" : ""} selected` : "Choose field photos"}
        </span>
        <span className={`text-[10px] ${s.textMuted}`}>JPG / PNG · original photos keep their GPS location</span>
        <input type="file" accept="image/*" multiple className="hidden"
          onChange={(e) => setFiles([...e.target.files])} />
      </label>

      {error && (
        <p className="text-[11px] text-red-500 mt-3 flex items-start gap-1.5">
          <AlertTriangle className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" /> {error}
        </p>
      )}

      <button
        disabled={!files.length || busy}
        onClick={run}
        className={`w-full mt-4 py-3 rounded-full font-semibold text-sm ${s.accentBg} ${s.accentTextOn} disabled:opacity-40 flex items-center justify-center gap-2`}
      >
        {busy && <Loader2 className="w-4 h-4 animate-spin" />}
        {busy ? "CLASSIFYING…" : "RUN MATURITY CLASSIFICATION"}
      </button>
    </div>
  );
}

function Stat({ s, label, value }) {
  return (
    <div className={`${s.inner} rounded-lg p-2.5`}>
      <p className={`text-[9px] ${s.textMuted} uppercase`}>{label}</p>
      <p className={`text-sm font-semibold ${s.textPrimary}`}>{value}</p>
    </div>
  );
}

function RegionDetail({ s, p, r }) {
  const lvl = LEVELS[r.spray_level];
  return (
    <div>
      <img src={imageUrl(p.mission_id, r.region_id)} alt={r.image}
        className={`w-full rounded-lg mb-3 border ${s.border}`} />
      <div className="flex items-center justify-between mb-3">
        <div className="min-w-0">
          <p className={`text-sm font-semibold ${s.textPrimary}`}>Region {r.region_id}</p>
          <p className={`text-[10px] ${s.textMuted} truncate`}>{r.image}</p>
        </div>
        <span className="text-[10px] font-bold px-2 py-1 rounded-full text-white" style={{ background: lvl.color }}>
          {lvl.label.toUpperCase()}
        </span>
      </div>

      {r.needs_review && (
        <p className="text-[11px] text-amber-500 bg-amber-500/10 rounded-lg p-2 mb-3 flex gap-1.5">
          <AlertTriangle className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
          Needs review — safe fallback level used
        </p>
      )}

      <div className="grid grid-cols-2 gap-3 mb-3">
        <Stat s={s} label="Maturity" value={MATURITY_LABEL[r.maturity] || r.maturity} />
        <Stat s={s} label="Confidence" value={`${Math.round(r.confidence * 100)}%`} />
        <Stat s={s} label="Rate" value={`×${r.rate_multiplier} of normal`} />
        <Stat s={s} label="Est. flow" value={`${r.flow_l_min ?? "—"} L/min`} />
      </div>

      {r.probs && Object.keys(r.probs).length > 0 && (
        <div className={`${s.inner} rounded-lg p-2.5 mb-3`}>
          <p className={`text-[9px] ${s.textMuted} uppercase mb-2`}>Class probabilities</p>
          {Object.entries(r.probs).map(([c, v]) => (
            <div key={c} className="flex items-center gap-2 mb-1">
              <span className={`text-[10px] w-14 ${s.textMuted}`}>{MATURITY_LABEL[c] || c}</span>
              <div className={`flex-1 h-1.5 rounded-full ${s.isDark ? "bg-border" : "bg-light-border"}`}>
                <div className={`h-1.5 rounded-full ${s.accentBg}`} style={{ width: `${v * 100}%` }} />
              </div>
              <span className={`text-[10px] w-9 text-right ${s.textPrimary}`}>{Math.round(v * 100)}%</span>
            </div>
          ))}
        </div>
      )}

      <div className={`${s.inner} rounded-lg p-2.5 mb-3`}>
        <p className={`text-[9px] ${s.textMuted} uppercase mb-1`}>Reason</p>
        <p className={`text-xs ${s.textPrimary}`}>{r.reason}</p>
      </div>

      <p className={`text-[10px] ${s.textMuted} flex items-center gap-1`}>
        <MapPin className="w-3 h-3" />
        {r.lat != null ? `${r.lat.toFixed(6)}, ${r.lon.toFixed(6)}` : "No GPS in photo — location will come from the navigation component"}
      </p>
    </div>
  );
}

export default function Prescription() {
  const s = useC4Styles();
  const [params, setParams] = useSearchParams();
  const missionId = params.get("mission");
  // Loaded mission and selection are keyed by mission id, so switching missions
  // shows "loading" / clears the selection without resetting state in an effect.
  const [loaded, setLoaded] = useState({ id: null, p: null, error: "" });
  const [sel, setSel] = useState({ mission: null, region: null });
  const [missions, setMissions] = useState([]);

  const current = loaded.id === missionId ? loaded : { p: null, error: "" };
  const p = current.p;
  const error = current.error;
  const selected = sel.mission === missionId ? sel.region : null;
  const setSelected = (region) => setSel({ mission: missionId, region });

  useEffect(() => {
    listMissions().then(setMissions).catch(() => {});
  }, [loaded.id]);

  useEffect(() => {
    if (!missionId) return;
    let cancelled = false;
    getMission(missionId)
      .then((m) => !cancelled && setLoaded({ id: missionId, p: m, error: "" }))
      .catch((e) => !cancelled && setLoaded({ id: missionId, p: null, error: e.message }));
    return () => { cancelled = true; };
  }, [missionId]);

  const counts = useMemo(() => p?.summary.by_level || {}, [p]);
  const cols = p ? Math.min(12, Math.max(6, Math.ceil(Math.sqrt(p.regions.length * 4)))) : 0;

  const header = (
    <div className="flex items-center justify-between flex-wrap gap-3">
      <div>
        <p className={`text-[10px] ${s.textMuted} uppercase tracking-wider`}>Pass 2 input — spray level per region</p>
        <h1 className={`text-xl font-bold ${s.textPrimary}`}>Prescription Map</h1>
      </div>
      <div className="flex gap-2 items-center">
        {missions.length > 0 && (
          <select
            value={missionId || ""}
            onChange={(e) => setParams(e.target.value ? { mission: e.target.value } : {})}
            className={`text-xs ${s.cardBg} border ${s.border} ${s.textPrimary} rounded-full px-3 py-2 outline-none`}
          >
            <option value="">+ New mapping</option>
            {missions.map((m) => (
              <option key={m.mission_id} value={m.mission_id}>{m.mission_id} · {m.field}</option>
            ))}
          </select>
        )}
      </div>
    </div>
  );

  if (!missionId) {
    return (
      <div className="flex flex-col gap-4">
        {header}
        <NewMapping s={s} onDone={(res) => { setLoaded({ id: res.mission_id, p: res, error: "" }); setParams({ mission: res.mission_id }); }} />
      </div>
    );
  }

  if (error || !p) {
    return (
      <div className="flex flex-col gap-4">
        {header}
        <p className={`text-xs ${error ? "text-red-500" : s.textMuted}`}>{error || "Loading prescription…"}</p>
      </div>
    );
  }

  const total = p.summary.regions;
  return (
    <div className="flex flex-col gap-4">
      {header}

      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex gap-3 flex-wrap">
          {Object.entries(LEVELS).map(([k, l]) => (
            <span key={k} className="flex items-center gap-1.5 text-[10px]">
              <span className="w-2 h-2 rounded-full" style={{ background: l.color }} />
              <span className={s.textMuted}>{l.label.toUpperCase()} {Math.round(((counts[k] || 0) / total) * 100)}%</span>
            </span>
          ))}
          <span className="flex items-center gap-1.5 text-[10px]">
            <span className="w-3 h-3 rounded-full bg-[#0D0E10] text-white text-[8px] font-bold flex items-center justify-center ring-1 ring-white">!</span>
            <span className={s.textMuted}>NEEDS REVIEW</span>
          </span>
        </div>
        <p className={`text-[10px] ${s.textMuted}`}>{p.mission_id} · {p.field} · {p.generated_at.replace("T", " ")}</p>
      </div>

      {p.rejected?.length > 0 && (
        <p className="text-[11px] text-amber-500 bg-amber-500/10 rounded-lg p-2 flex gap-1.5">
          <AlertTriangle className="w-3.5 h-3.5 mt-0.5" />
          Skipped {p.rejected.map((x) => `${x.image} (${x.reason})`).join(", ")}
        </p>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Stat s={s} label="Regions" value={total} />
        <Stat s={s} label="Needs review" value={p.summary.needs_review} />
        <Stat s={s} label="Chemical vs fixed rate" value={`×${p.summary.relative_chemical_use.toFixed(2)}`} />
        <Stat s={s} label="Inference" value={p.avg_processing_ms != null ? `${p.avg_processing_ms} ms/photo` : "—"} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className={`lg:col-span-2 self-start ${s.cardBg} border ${s.border} rounded-2xl p-4`}>
          <div className={`grid gap-1.5 ${s.inner} rounded-xl p-3`} style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}>
            {p.regions.map((r) => (
              <button
                key={r.region_id}
                onClick={() => setSelected(r)}
                title={`Region ${r.region_id} · ${MATURITY_LABEL[r.maturity] || r.maturity} · ${Math.round(r.confidence * 100)}%${r.needs_review ? " · needs review" : ""}`}
                className={`relative aspect-square rounded-sm flex flex-col items-center justify-center text-white transition ${
                  selected?.region_id === r.region_id ? "ring-2 ring-white" : "hover:opacity-80"
                }`}
                style={{ background: LEVELS[r.spray_level].color }}
              >
                <span className="text-[10px] font-bold">{LEVELS[r.spray_level].short}</span>
                <span className="text-[8px] opacity-80">{r.region_id}</span>
                {r.needs_review && (
                  <span className="absolute -top-1 -right-1 w-3.5 h-3.5 rounded-full bg-[#0D0E10] text-white text-[8px] font-bold flex items-center justify-center ring-1 ring-white">!</span>
                )}
              </button>
            ))}
          </div>
          <p className={`text-[10px] ${s.textMuted} mt-2`}>
            One cell per mapped photo, in flight order. Rates are relative to the estate's normal dose (placeholder values until validated with TRI).
          </p>
        </div>

        <div className={`${s.cardBg} border ${s.border} rounded-2xl p-4`}>
          {!selected ? (
            <p className={`text-xs ${s.textMuted}`}>Click a region to view its prescription.</p>
          ) : (
            <RegionDetail s={s} p={p} r={selected} />
          )}

          <div className="flex gap-2 mt-4 mb-2">
            <button onClick={() => downloadFile(`${p.mission_id}_prescription.json`, JSON.stringify(p, null, 2), "application/json")}
              className={`flex-1 py-2 rounded-full text-xs font-semibold border ${s.border} ${s.textPrimary} flex items-center justify-center gap-1`}>
              <Download className="w-3 h-3" /> JSON
            </button>
            <button onClick={() => downloadFile(`${p.mission_id}_prescription.csv`, prescriptionCsv(p), "text/csv")}
              className={`flex-1 py-2 rounded-full text-xs font-semibold border ${s.border} ${s.textPrimary} flex items-center justify-center gap-1`}>
              <Download className="w-3 h-3" /> CSV
            </button>
          </div>
          <Link to="/prescription"
            className={`block text-center w-full py-2.5 rounded-full text-xs font-semibold ${s.accentBg} ${s.accentTextOn}`}>
            New mapping
          </Link>
          <p className={`text-[10px] ${s.textMuted} mt-3`}>
            The spray flight (Pass 2) uses this prescription after system integration.
          </p>
        </div>
      </div>
    </div>
  );
}
