import { NavLink, Outlet, useLocation } from "react-router-dom";
import { BarChart3, Grid3x3, Home, ListChecks, Plane, Settings } from "lucide-react";
import { useTheme } from "../context/ThemeContext";
import { DroneIcon, MoonIcon, SunIcon } from "./Icons";

// Same look as the team prototype (TeaDrone), Component 4 pages only.
const NAV = [
  { to: "/", label: "Home", icon: Home },
  { to: "/prescription", label: "Prescription", icon: Grid3x3 },
  { to: "/flight", label: "Spray flight", icon: Plane },
  { to: "/missions", label: "Missions", icon: ListChecks },
  { to: "/model", label: "Model", icon: BarChart3 },
  { to: "/settings", label: "Settings", icon: Settings },
];

export default function Layout() {
  const { isDark, toggleTheme } = useTheme();
  const { pathname } = useLocation();

  const pageBg = isDark ? "bg-ink" : "bg-light-bg";
  const sideBg = isDark ? "bg-surface" : "bg-light-surface";
  const border = isDark ? "border-border" : "border-light-border";
  const textMuted = isDark ? "text-muted" : "text-light-muted";
  const textPrimary = isDark ? "text-white" : "text-light-text";
  const activeBg = isDark ? "bg-accent/10" : "bg-light-primary/10";
  const accent = isDark ? "text-accent" : "text-light-primary";
  const current = NAV.find((n) => (n.to === "/" ? pathname === "/" : pathname.startsWith(n.to)))?.label || "";

  return (
    <div className={`flex min-h-screen ${pageBg} transition-colors duration-300`}>
      <aside className={`w-56 flex-shrink-0 ${sideBg} border-r ${border} p-3 hidden md:flex flex-col`}>
        <div className="flex items-center gap-2 px-2 py-3 mb-1">
          <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${isDark ? "bg-accent" : "bg-light-primary"}`}>
            <DroneIcon className={`w-4 h-4 ${isDark ? "text-ink" : "text-white"}`} />
          </div>
          <span className={`text-sm font-semibold ${textPrimary}`}>TeaDrone</span>
        </div>
        <p className={`text-[10px] ${textMuted} px-3 mb-3 leading-snug`}>Component 4 · Maturity-Driven Variable-Rate Spraying</p>
        <nav className="flex flex-col gap-0.5">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} end={to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-2 px-3 py-2 rounded-lg text-xs transition ${
                  isActive ? `${activeBg} ${textPrimary} font-semibold` : textMuted
                }`
              }>
              {({ isActive }) => (<><Icon className={`w-4 h-4 ${isActive ? accent : ""}`} />{label}</>)}
            </NavLink>
          ))}
        </nav>
        <p className={`mt-auto text-[9px] ${textMuted} px-3`}>Standalone build · merges into the team dashboard at integration</p>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <header className={`flex items-center justify-between px-4 md:px-6 py-3 md:py-4 border-b ${border}`}>
          <p className={`text-xs ${textMuted}`}>Component 4 › {current}</p>
          <button onClick={toggleTheme} aria-label="Toggle dark or light mode"
            className={`w-8 h-8 rounded-full ${sideBg} border ${border} flex items-center justify-center`}>
            {isDark ? <SunIcon className="w-4 h-4 text-muted" /> : <MoonIcon className="w-4 h-4 text-light-muted" />}
          </button>
        </header>
        {/* compact nav for small screens */}
        <nav className={`md:hidden flex gap-1 overflow-x-auto px-4 py-2 border-b ${border}`}>
          {NAV.map(({ to, label }) => (
            <NavLink key={to} to={to} end={to === "/"}
              className={({ isActive }) => `text-xs px-3 py-1.5 rounded-full whitespace-nowrap ${isActive ? `${activeBg} ${textPrimary} font-semibold` : textMuted}`}>
              {label}
            </NavLink>
          ))}
        </nav>
        <main className="flex-1 p-4 md:p-6 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
