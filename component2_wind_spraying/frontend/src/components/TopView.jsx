// Top view drawn as SVG. The drone always flies "up"; everything else is drawn relative to it.
// x = sideways distance (m, right is +), y = along the flight line (m).

const W = 640, H = 400;
const XMIN = -8.6, XMAX = 8.6, YMIN = -7, YMAX = 9;
const X = (x) => ((x - XMIN) / (XMAX - XMIN)) * W;
const Y = (y) => ((YMAX - y) / (YMAX - YMIN)) * H;

export default function TopView({ r, wind, windDir, heading, swath }) {
  const sign = r.wind_from_side === "right" ? 1 : -1;
  const shift = r.mode === "CORRECT" ? r.spray_shift_m : 0;
  const offset = sign * r.path_offset_m;
  const half = swath / 2;

  // Unit vector pointing to where the wind comes FROM (clockwise from "up")
  const rel = ((windDir - heading) * Math.PI) / 180;
  const fx = Math.sin(rel), fy = Math.cos(rel);
  const start = { x: 6 * fx, y: 6 * fy };          // wind arrow starts on the windward side
  const end = { x: 3 * fx, y: 3 * fy };

  const ticks = [-8, -6, -4, -2, 0, 2, 4, 6, 8];

  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H + 46}`} className="topview" role="img"
           aria-label={`Top view: spray lands ${shift} m to the ${sign > 0 ? "left" : "right"}; path moved ${r.path_offset_m} m`}>
        <defs>
          <marker id="arrow-wind" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M0,0 L10,5 L0,10 z" className="wind-fill" />
          </marker>
          <marker id="arrow-drone" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M0,0 L10,5 L0,10 z" className="ink-fill" />
          </marker>
        </defs>

        {/* grid */}
        {ticks.map((t) => (
          <g key={t}>
            <line x1={X(t)} x2={X(t)} y1={0} y2={H} className="grid" />
            <text x={X(t)} y={H + 18} className="tick" textAnchor="middle">{t}</text>
          </g>
        ))}

        {/* target swath */}
        <rect x={X(-half)} y={Y(6)} width={X(half) - X(-half)} height={Y(-6) - Y(6)} className="swath" />
        <text x={X(0)} y={Y(6) - 8} textAnchor="middle" className="label">target tea rows (swath)</text>

        {/* planned path */}
        <line x1={X(0)} x2={X(0)} y1={Y(-6)} y2={Y(6)} className="planned" />

        {shift > 0 && (
          <>
            <line x1={X(-sign * shift)} x2={X(-sign * shift)} y1={Y(-6)} y2={Y(6)} className="uncorrected">
              <title>Spray without correction lands {shift} m off target</title>
            </line>
            <line x1={X(offset)} x2={X(offset)} y1={Y(-6)} y2={Y(6)} className="corrected">
              <title>Corrected flight line ({r.path_offset_m} m)</title>
            </line>
          </>
        )}

        {/* drone */}
        <line x1={X(offset)} y1={Y(-6)} x2={X(offset)} y2={Y(-4.3)} className="drone" markerEnd="url(#arrow-drone)" />
        <text x={X(offset)} y={Y(-6.7)} textAnchor="middle" className="label">drone (flies up ↑)</text>

        {/* wind */}
        {wind > 0 && (
          <>
            <line x1={X(start.x)} y1={Y(start.y)} x2={X(end.x)} y2={Y(end.y)} className="wind" markerEnd="url(#arrow-wind)" />
            <text x={X(start.x)} y={Y(start.y) - 8} textAnchor="middle" className="label">wind {wind} m/s</text>
          </>
        )}
        <text x={W / 2} y={H + 42} textAnchor="middle" className="tick">sideways distance (m)  ← left | right →</text>
      </svg>

      <ul className="legend">
        <li><span className="key planned-key" /> Planned path</li>
        <li><span className="key uncorrected-key" /> Spray without correction</li>
        <li><span className="key corrected-key" /> Corrected path</li>
        <li><span className="key wind-key" /> Wind</li>
      </ul>
    </div>
  );
}
