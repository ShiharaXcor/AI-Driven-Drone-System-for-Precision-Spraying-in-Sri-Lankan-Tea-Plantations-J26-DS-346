const ICON = { info: "🔧", line: "↕", warning: "⚠️", critical: "⏸", good: "▶" };
const mmss = (t) => `${String(Math.floor(t / 60)).padStart(2, "0")}:${String(Math.floor(t % 60)).padStart(2, "0")}`;

// Newest decision first
export default function DecisionLog({ events }) {
  const list = [...events].reverse();
  return (
    <ol className="log">
      {list.map((e, i) => (
        <li key={`${e.t}-${i}`} className={`log-${e.kind}`}>
          <time>{mmss(e.t)}</time>
          <span aria-hidden="true">{ICON[e.kind] || "•"}</span>
          <span>{e.text}</span>
        </li>
      ))}
    </ol>
  );
}
