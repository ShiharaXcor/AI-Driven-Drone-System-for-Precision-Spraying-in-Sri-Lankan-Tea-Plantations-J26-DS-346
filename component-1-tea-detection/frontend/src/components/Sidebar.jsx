import { useState } from "react";
import { NavLink } from "react-router-dom";
import {
  Camera, Map, ListChecks, Bell, Hand, Settings,
  Plane, MapPinned, Droplets, ChevronDown, Circle,
} from "lucide-react";
import { useTheme } from "../context/ThemeContext";
import { DroneIcon } from "./Icons";

const groups = [
  {
    id: "detection",
    label: "01 · Tea Plant Anomaly Detection",
    icon: Camera,
    online: true,
    basePath: "/dashboard/detection",
    items: [
      { label: "Home", path: "" },
      { label: "Detection map", path: "map" },
      { label: "Logs", path: "logs" },
      { label: "Alerts", path: "alerts" },
      { label: "Manual control", path: "manual" },
      { label: "Settings", path: "settings" },
    ],
  },
{
  id: "flight",
  label: "02 · Smart Path Optimization",
  icon: Plane,
  online: true,
  basePath: "/dashboard/flight",
  items: [
    { label: "Live Mission", path: "" },
    { label: "Mission Planner", path: "planner" },
    { label: "Flight Analytics", path: "analytics" },
    { label: "Estates", path: "estates" },
  ],
},
 {
  id: "mapping",
  label: "03 · Tea Maturity Control",
  icon: MapPinned,
  online: true,
  basePath: "/dashboard/mapping",
  items: [
    { label: "Home", path: "" },
    { label: "Missions", path: "missions" },
    { label: "Prescription", path: "prescription" },
    { label: "Flight", path: "flight" },
    { label: "Settings", path: "settings" },
  ],
},
  {
  id: "spray",
  label: "04 · Adaptive Spray Control",
  icon: Droplets,
  online: true,
  basePath: "/dashboard/spray",
  items: [
    { label: "Mission Setup", path: "" },
    { label: "Wind Monitor", path: "wind" },
    { label: "Spray Compensation", path: "compensation" },
    { label: "Performance", path: "performance" },
  ],
},
];

export default function Sidebar() {
  const { isDark } = useTheme();
  const [openGroup, setOpenGroup] = useState("detection");

  const sidebarBg = isDark ? "bg-surface" : "bg-light-surface";
  const border = isDark ? "border-border" : "border-light-border";
  const textMuted = isDark ? "text-muted" : "text-light-muted";
  const textPrimary = isDark ? "text-white" : "text-light-text";
  const accent = isDark ? "text-accent" : "text-light-primary";
  const activeGroupBg = isDark ? "bg-accent/10" : "bg-light-primary/10";
  const activeItemText = isDark ? "text-white font-semibold" : "text-light-text font-semibold";

  return (
    <aside className={`w-56 flex-shrink-0 ${sidebarBg} border-r ${border} p-3 flex flex-col`}>
      <div className="flex items-center gap-2 px-2 py-3 mb-2">
        <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${isDark ? "bg-accent" : "bg-light-primary"}`}>
          <DroneIcon className={`w-4 h-4 ${isDark ? "text-ink" : "text-white"}`} />
        </div>
        <span className={`text-sm font-semibold ${textPrimary}`}>TeaDrone</span>
      </div>

      <nav className="flex-1 overflow-y-auto">
        {groups.map((group) => {
          const Icon = group.icon;
          const isOpen = openGroup === group.id;
          return (
            <div key={group.id} className="mb-1">
              <button
                onClick={() => setOpenGroup(isOpen ? null : group.id)}
                className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left transition ${
                  isOpen ? activeGroupBg : ""
                }`}
              >
                <Icon className={`w-4 h-4 ${isOpen ? accent : textMuted}`} />
                <span className={`text-xs flex-1 ${isOpen ? activeItemText : textMuted}`}>
                  {group.label}
                </span>
                <Circle
                  className={`w-2 h-2 ${group.online ? accent : "text-gray-500"}`}
                  fill="currentColor"
                />
                <ChevronDown
                  className={`w-3 h-3 ${textMuted} transition-transform ${isOpen ? "rotate-180" : ""}`}
                />
              </button>

              {isOpen && (
                <div
                  className={`ml-5 pl-3 mt-1 flex flex-col gap-0.5 border-l-2 ${
                    isDark ? "border-accent" : "border-light-primary"
                  }`}
                >
                  {group.items.map((item) => (
                    <NavLink
                      key={item.label}
                      to={`${group.basePath}${item.path ? "/" + item.path : ""}`}
                      end={item.path === ""}
                      className={({ isActive }) =>
                        `text-xs px-2 py-1.5 rounded-md transition ${
                          isActive ? activeItemText : textMuted
                        } hover:${isDark ? "text-white" : "text-light-text"}`
                      }
                    >
                      {item.label}
                    </NavLink>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </nav>
    </aside>
  );
}