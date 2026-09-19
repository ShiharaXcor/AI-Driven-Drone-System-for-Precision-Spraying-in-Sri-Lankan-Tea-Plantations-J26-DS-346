import { Outlet, useLocation } from "react-router-dom";
import { Bell } from "lucide-react";
import Sidebar from "../components/Sidebar";
import { useTheme } from "../context/ThemeContext";
import { SunIcon, MoonIcon } from "../components/Icons";

export default function DashboardLayout() {
  const { isDark, toggleTheme } = useTheme();
  const location = useLocation();

  const pageBg = isDark ? "bg-ink" : "bg-light-bg";
  const textMuted = isDark ? "text-muted" : "text-light-muted";
  const cardBg = isDark ? "bg-surface" : "bg-light-surface";
  const border = isDark ? "border-border" : "border-light-border";

  const crumbs = location.pathname
    .replace("/dashboard/", "")
    .split("/")
    .filter(Boolean)
    .join(" › ") || "detection";

  return (
    <div className={`flex min-h-screen ${pageBg} transition-colors duration-300`}>
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <header className={`flex items-center justify-between px-6 py-4 border-b ${border}`}>
          <p className={`text-xs ${textMuted} capitalize`}>{crumbs}</p>
          <div className="flex items-center gap-3">
            <Bell className={`w-4 h-4 ${textMuted}`} />
            <button
              onClick={toggleTheme}
              className={`w-8 h-8 rounded-full ${cardBg} border ${border} flex items-center justify-center`}
              aria-label="Toggle dark or light mode"
            >
              {isDark ? <SunIcon className="w-4 h-4 text-muted" /> : <MoonIcon className="w-4 h-4 text-light-muted" />}
            </button>
          </div>
        </header>
        <main className="flex-1 p-6 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}