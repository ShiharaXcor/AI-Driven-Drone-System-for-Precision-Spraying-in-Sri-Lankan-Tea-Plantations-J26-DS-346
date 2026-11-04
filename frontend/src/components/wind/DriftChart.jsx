import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ReferenceLine, ReferenceDot,
} from "recharts";

// Fixed colour per droplet class (same order everywhere)
const COLORS = { "VF-F": "var(--series-1)", "F-M": "var(--series-2)", "M-C": "var(--series-3)", "C-VC": "var(--series-4)" };

export default function DriftChart({ rows, limit, current, droplet }) {
  if (!rows.length) return <p className="sub">Loading chart…</p>;
  const cw = current.drift_m == null ? null : Math.min(Math.max(current.crosswind_ms, 0.5), 6.5);

  return (
    <div style={{ width: "100%", height: 340 }}>
      <ResponsiveContainer>
        <LineChart data={rows} margin={{ top: 10, right: 80, left: 0, bottom: 20 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="crosswind" type="number" domain={[0.5, 6.5]} tick={{ fill: "var(--text-secondary)" }}
                 stroke="var(--grid)" label={{ value: "crosswind (m/s)", position: "insideBottom", offset: -5, fill: "var(--text-secondary)" }} />
          <YAxis tick={{ fill: "var(--text-secondary)" }} stroke="var(--grid)"
                 label={{ value: "drift (m)", angle: -90, position: "insideLeft", fill: "var(--text-secondary)" }} />
          <Tooltip contentStyle={{ background: "var(--surface-2)", border: "1px solid var(--grid)", color: "var(--text-primary)" }}
                   labelFormatter={(v) => `crosswind ${v} m/s`} formatter={(v, name) => [`${v} m`, name]} />
          <Legend verticalAlign="top" height={30}
                  formatter={(v) => <span style={{ color: "var(--text-primary)" }}>{v}</span>} />
          <ReferenceLine y={limit} stroke="var(--text-secondary)" strokeDasharray="4 4"
                         label={{ value: `limit ${limit} m`, position: "right", fill: "var(--text-secondary)" }} />
          {Object.keys(COLORS).map((d) => (
            <Line key={d} type="monotone" dataKey={d} stroke={COLORS[d]} strokeWidth={2} dot={false} activeDot={{ r: 5 }} />
          ))}
          {cw != null && (
            <ReferenceDot x={cw} y={current.drift_m} r={7} fill={COLORS[droplet]} stroke="var(--surface-1)" strokeWidth={2} />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
