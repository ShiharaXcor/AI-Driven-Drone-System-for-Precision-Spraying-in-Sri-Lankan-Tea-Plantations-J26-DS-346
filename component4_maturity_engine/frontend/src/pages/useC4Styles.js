import { useTheme } from "../context/ThemeContext";

// Theme class names shared by the Component 4 pages (same tokens as the rest of the prototype).
export default function useC4Styles() {
  const { isDark } = useTheme();
  return {
    isDark,
    cardBg: isDark ? "bg-surface" : "bg-light-surface",
    border: isDark ? "border-border" : "border-light-border",
    textMuted: isDark ? "text-muted" : "text-light-muted",
    textPrimary: isDark ? "text-white" : "text-light-text",
    inner: isDark ? "bg-ink" : "bg-light-bg",
    accentBg: isDark ? "bg-accent" : "bg-light-primary",
    accentTextOn: isDark ? "text-ink" : "text-white",
    accentText: isDark ? "text-accent" : "text-light-primary",
    accentHex: isDark ? "#C6F135" : "#2F5233",
  };
}
