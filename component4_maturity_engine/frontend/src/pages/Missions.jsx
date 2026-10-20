import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import useC4Styles from "./useC4Styles";
import { LEVELS, listMissions } from "../api/c4";

export default function Missions() {
  const s = useC4Styles();
  const [missions, setMissions] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    listMissions().then(setMissions).catch((e) => setError(e.message));
  }, []);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <p className={`text-[10px] ${s.textMuted} uppercase tracking-wider`}>Pass 1 mapping records</p>
          <h1 className={`text-xl font-bold ${s.textPrimary}`}>Mission History</h1>
        </div>
        <Link to="/prescription"
          className={`text-xs font-semibold px-4 py-2 rounded-full ${s.accentBg} ${s.accentTextOn}`}>
          New mission
        </Link>
      </div>

      <div className={`${s.cardBg} border ${s.border} rounded-2xl p-4 overflow-x-auto`}>
        {error && <p className="text-xs text-red-500">{error}</p>}
        {!error && missions === null && <p className={`text-xs ${s.textMuted}`}>Loading…</p>}
        {missions?.length === 0 && (
          <p className={`text-xs ${s.textMuted}`}>No missions yet. Start one from <b>New mission</b>.</p>
        )}
        {missions?.length > 0 && (
          <table className="w-full text-xs">
            <thead>
              <tr className={`border-b ${s.border}`}>
                {["Date", "Mission", "Field", "Regions", "Low / Normal / High", "Needs review", "Chemical vs fixed", ""].map((h) => (
                  <th key={h} className={`p-2 text-left font-semibold ${s.textMuted}`}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {missions.map((m) => (
                <tr key={m.mission_id} className={`border-b ${s.border} last:border-0`}>
                  <td className={`p-2 font-mono ${s.textMuted}`}>{m.generated_at.replace("T", " ").slice(0, 16)}</td>
                  <td className={`p-2 font-semibold font-mono ${s.textPrimary}`}>{m.mission_id}</td>
                  <td className={`p-2 ${s.textPrimary}`}>{m.field}</td>
                  <td className={`p-2 ${s.textPrimary}`}>{m.regions}</td>
                  <td className="p-2">
                    {Object.entries(LEVELS).map(([k, l], i) => (
                      <span key={k} className="font-semibold" style={{ color: l.color }}>
                        {m.by_level[k]}{i < 2 && <span className={s.textMuted}> / </span>}
                      </span>
                    ))}
                  </td>
                  <td className={`p-2 font-semibold ${m.needs_review > 0 ? "text-amber-500" : s.textPrimary}`}>{m.needs_review}</td>
                  <td className={`p-2 ${s.textPrimary}`}>×{m.relative_chemical_use.toFixed(2)}</td>
                  <td className="p-2">
                    <Link to={`/prescription?mission=${m.mission_id}`} className={`font-semibold ${s.accentText}`}>
                      Open map
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
