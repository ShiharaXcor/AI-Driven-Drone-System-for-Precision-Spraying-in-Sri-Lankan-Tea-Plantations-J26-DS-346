// Small building blocks in the team's TeaDrone style (white cards, small grey labels, bold values)

export function Stat({ label, value }) {
  return (
    <div className="stat">
      <span>{label}</span>
      <b>{value}</b>
    </div>
  );
}

export function Tile({ label, value }) {
  return (
    <div className="tile">
      <span>{label}</span>
      <b>{value}</b>
    </div>
  );
}

// One labelled slider
export function Num({ label, value, min, max, step = 1, unit = "", onChange }) {
  return (
    <label className="field">
      <span className="field-row"><span>{label}</span><strong>{value}{unit}</strong></span>
      <input type="range" min={min} max={max} step={step} value={value} onChange={(e) => onChange(Number(e.target.value))} />
    </label>
  );
}

// Big coloured "CURRENT DECISION" card (same idea as NO_SPRAY in component 01)
export function DecisionCard({ tone, label, text, children }) {
  return (
    <section className={`decision ${tone}`} aria-live="polite">
      <span className="decision-kicker">Current decision</span>
      <strong className="decision-label">{label}</strong>
      <p className="decision-text">{text}</p>
      {children}
    </section>
  );
}
