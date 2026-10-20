import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine } from "recharts";

// Wind speed over the mission, with the strong-wind limit and the current moment
export default function WindTimeline({ steps, t, limit }) {
  const data = steps.map((s) => ({ t: s.t, wind: s.wind_ms, cross: s.crosswind_ms }));
  return (
    <div style={{ width: "100%", height: 200 }}>
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 8, right: 70, left: -10, bottom: 4 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="t" type="number" domain={["dataMin", "dataMax"]} tick={{ fill: "var(--text-secondary)", fontSize: 12 }}
                 stroke="var(--grid)" tickFormatter={(v) => `${Math.round(v)}s`} />
          <YAxis tick={{ fill: "var(--text-secondary)", fontSize: 12 }} stroke="var(--grid)" unit=" m/s" width={60} />
          <Tooltip contentStyle={{ background: "var(--surface-2)", border: "1px solid var(--grid)", color: "var(--text-primary)" }}
                   labelFormatter={(v) => `t = ${v} s`}
                   formatter={(v, n) => [`${v} m/s`, n === "wind" ? "wind" : "crosswind"]} />
          <ReferenceLine y={limit} stroke="var(--uncorrected)" strokeDasharray="4 4"
                         label={{ value: `hold > ${limit}`, position: "right", fill: "var(--text-secondary)", fontSize: 12 }} />
          <ReferenceLine x={t} stroke="var(--text-primary)" />
          <Line type="monotone" dataKey="cross" stroke="var(--series-1)" strokeWidth={2} dot={false} isAnimationActive={false} />
          <Line type="monotone" dataKey="wind" stroke="var(--wind)" strokeWidth={2.5} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
      <ul className="legend">
        <li><span className="key wind-key" /> wind</li>
        <li><span className="key corrected-key" /> crosswind (across the flight line)</li>
      </ul>
    </div>
  );
}
