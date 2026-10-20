import { useState } from "react";
import MissionView from "./views/MissionView.jsx";
import AnalysisView from "./views/AnalysisView.jsx";

// Top bar with two tabs: the whole-mission view and the single-condition analysis
export default function App() {
  const [tab, setTab] = useState("mission");
  return (
    <div className="app">
      <nav className="topbar">
        <div className="brand">
          <strong>Wind-adaptive spraying</strong>
          <span>Component 2 · tea plantation UAV</span>
        </div>
        <div className="tabs" role="tablist">
          <button role="tab" aria-selected={tab === "mission"} className={tab === "mission" ? "tab active" : "tab"}
                  onClick={() => setTab("mission")}>Mission</button>
          <button role="tab" aria-selected={tab === "analysis"} className={tab === "analysis" ? "tab active" : "tab"}
                  onClick={() => setTab("analysis")}>Analysis</button>
        </div>
      </nav>
      {tab === "mission" ? <MissionView /> : <AnalysisView />}
    </div>
  );
}
