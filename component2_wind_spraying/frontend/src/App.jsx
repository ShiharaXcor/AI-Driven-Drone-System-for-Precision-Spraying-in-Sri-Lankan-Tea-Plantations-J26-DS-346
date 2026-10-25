import { useEffect, useState } from "react";
import MissionView from "./views/MissionView.jsx";
import AnalysisView from "./views/AnalysisView.jsx";

// Same layout as the team's TeaDrone dashboard: left menu with the 4 components,
// a header bar, and the page content in white cards.
// This component = "04 · Adaptive Spray Control" (wind-adaptive spraying).

const Icon = {
  logo: <path d="M7 7l10 10M17 7L7 17M5 5h4v4H5zM15 5h4v4h-4zM5 15h4v4H5zM15 15h4v4h-4z" />,
  camera: <><rect x="3" y="7" width="18" height="13" rx="2" /><circle cx="12" cy="13.5" r="3.5" /><path d="M8 7l1.5-3h5L16 7" /></>,
  plane: <path d="M3 13l7-2 4-7 2 1-2 7 6 2-1 2-6-1-3 5-2-1 1-5-6-1z" />,
  leaf: <><circle cx="12" cy="9" r="5" /><path d="M5 21c1.5-4 4-6 7-6s5.5 2 7 6" /></>,
  drop: <><path d="M12 3c3 4 6 7.5 6 11a6 6 0 0 1-12 0c0-3.5 3-7 6-11z" /><path d="M4 8l3 2M4 13l3-1" /></>,
  bell: <path d="M6 16V11a6 6 0 0 1 12 0v5l2 2H4zM10 20a2 2 0 0 0 4 0" />,
  moon: <path d="M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5z" />,
  sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5L19 19M5 19l1.5-1.5M17.5 6.5L19 5" /></>,
  chevDown: <path d="M6 9l6 6 6-6" />,
  chevUp: <path d="M6 15l6-6 6 6" />,
};
const Svg = ({ d, size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"
       strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{d}</svg>
);

const COMPONENTS = [
  { no: "01", name: "Tea Plant Anomaly Detection", icon: Icon.camera },
  { no: "02", name: "Smart Path Optimization", icon: Icon.plane },
  { no: "03", name: "Tea Maturity Control", icon: Icon.leaf },
  { no: "04", name: "Adaptive Spray Control", icon: Icon.drop, mine: true },
];
const PAGES = [
  { id: "mission", label: "Mission" },
  { id: "analysis", label: "Wind analysis" },
];

export default function App() {
  const [page, setPage] = useState("mission");
  const [open, setOpen] = useState("04");
  const [dark, setDark] = useState(false);

  useEffect(() => { document.documentElement.dataset.theme = dark ? "dark" : "light"; }, [dark]);

  return (
    <div className="shell">
      {/* ---------------- left menu ---------------- */}
      <aside className="nav">
        <div className="logo">
          <span className="logo-mark"><Svg d={Icon.logo} size={16} /></span>
          <span>TeaDrone</span>
        </div>

        {COMPONENTS.map((c) => {
          const isOpen = open === c.no;
          return (
            <div key={c.no} className="nav-group">
              <button className={`nav-item${c.mine ? " active" : ""}`} onClick={() => setOpen(isOpen ? "" : c.no)}
                      aria-expanded={isOpen}>
                <Svg d={c.icon} />
                <span className="nav-name">{c.no} · {c.name}</span>
                <span className="nav-dot" aria-hidden="true" />
                <Svg d={isOpen ? Icon.chevUp : Icon.chevDown} size={14} />
              </button>
              {isOpen && (
                <ul className="nav-sub">
                  {c.mine
                    ? PAGES.map((p) => (
                        <li key={p.id}>
                          <button className={page === p.id ? "current" : ""} onClick={() => setPage(p.id)}>{p.label}</button>
                        </li>
                      ))
                    : <li><span className="nav-later">Connected after integration</span></li>}
                </ul>
              )}
            </div>
          );
        })}
      </aside>

      {/* ---------------- header + page ---------------- */}
      <div className="content">
        <header className="header">
          <span className="crumb">{PAGES.find((p) => p.id === page).label}</span>
          <div className="header-actions">
            <button className="link">Log out</button>
            <button className="icon-btn" aria-label="Alerts"><Svg d={Icon.bell} /></button>
            <button className="icon-btn round" aria-label="Toggle dark mode" onClick={() => setDark((d) => !d)}>
              <Svg d={dark ? Icon.sun : Icon.moon} />
            </button>
          </div>
        </header>
        <main className="page">
          {page === "mission" ? <MissionView /> : <AnalysisView />}
        </main>
      </div>
    </div>
  );
}
