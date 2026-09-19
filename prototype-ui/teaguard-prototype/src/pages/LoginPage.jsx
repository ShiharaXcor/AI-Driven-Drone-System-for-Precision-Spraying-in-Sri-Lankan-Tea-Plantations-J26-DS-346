import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useTheme } from "../context/ThemeContext";

export default function LoginPage() {
  const navigate = useNavigate();
  const { isDark, toggleTheme } = useTheme();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  function handleLogin(e) {
    e.preventDefault();
    navigate("/dashboard");
  }

  const pageBg = isDark ? "bg-ink" : "bg-light-bg";
  const textPrimary = isDark ? "text-white" : "text-light-text";
  const textMuted = isDark ? "text-muted" : "text-light-muted";
  const cardBg = isDark ? "bg-surface" : "bg-light-surface";
  const cardBorder = isDark ? "border-border" : "border-light-border";
  const inputBg = isDark ? "bg-ink" : "bg-light-bg";
  const primaryFrom = isDark ? "from-accent" : "from-light-primary";
  const primaryTo = isDark ? "to-accent-dark" : "to-light-primary-mid";
  const primaryTextOn = isDark ? "text-ink" : "text-white";
  const overlay = isDark
    ? "from-ink/95 via-ink/85 to-ink"
    : "from-light-bg/95 via-light-bg/90 to-light-bg";

  return (
    <div className={`relative min-h-screen ${pageBg} ${textPrimary} overflow-hidden flex items-center justify-center px-6 transition-colors duration-300`}>
      <div
        className="absolute inset-0 bg-cover bg-center"
        style={{ backgroundImage: "url('/assets/drone-hero.jpg')" }}
      />
      <div className={`absolute inset-0 bg-gradient-to-b ${overlay}`} />

      <button
        onClick={toggleTheme}
        className={`absolute top-6 right-6 z-10 w-10 h-10 rounded-full ${cardBg} border ${cardBorder} flex items-center justify-center hover:scale-105 transition`}
        aria-label="Toggle dark or light mode"
      >
        {isDark ? (
          <SunIcon className="w-4 h-4 text-muted" />
        ) : (
          <MoonIcon className="w-4 h-4 text-light-muted" />
        )}
      </button>

      <div className={`relative z-10 w-full max-w-sm ${cardBg} border ${cardBorder} rounded-2xl p-8 shadow-2xl transition-colors duration-300`}>
        <div className="flex flex-col items-center mb-8">
          <div className={`w-10 h-10 rounded-lg bg-gradient-to-r ${primaryFrom} ${primaryTo} flex items-center justify-center mb-3`}>
            <DroneIcon className={`w-6 h-6 ${primaryTextOn}`} />
          </div>
          <h1 className="text-xl font-semibold tracking-wide">TeaDrone</h1>
          <p className={`text-xs ${textMuted} mt-1 uppercase tracking-[0.2em]`}>
            System Access
          </p>
        </div>

        <form onSubmit={handleLogin} className="flex flex-col gap-4">
          <div>
            <label className={`text-xs ${textMuted} mb-1 block`}>Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className={`w-full ${inputBg} border ${cardBorder} rounded-lg px-3 py-2.5 text-sm ${textPrimary} placeholder:opacity-50 focus:outline-none focus:border-accent transition`}
              required
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label className={`text-xs ${textMuted}`}>Password</label>
              <a href="#" className={`text-xs ${textMuted} hover:opacity-80 transition`}>
                Forgot password?
              </a>
            </div>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className={`w-full ${inputBg} border ${cardBorder} rounded-lg px-3 py-2.5 text-sm ${textPrimary} placeholder:opacity-50 focus:outline-none focus:border-accent transition`}
              required
            />
          </div>

          <button
            type="submit"
            className={`mt-2 w-full py-3 rounded-full bg-gradient-to-r ${primaryFrom} ${primaryTo} ${primaryTextOn} font-semibold text-sm tracking-wide hover:scale-[1.02] transition-transform`}
          >
            LOGIN
          </button>

          <button
            type="button"
            onClick={() => navigate("/dashboard")}
            className={`w-full py-3 rounded-full border ${cardBorder} ${textMuted} text-sm hover:opacity-80 transition`}
          >
            Continue as demo user
          </button>
        </form>

        <p className={`text-center text-xs ${textMuted} mt-6`}>
          Don't have an account?{" "}
          <Link to="/signup" className="text-accent hover:underline">
            Sign up
          </Link>
        </p>
      </div>

      <div className={`absolute bottom-8 z-10 flex items-center gap-2 px-4 py-2 rounded-full ${cardBg} border ${cardBorder}`}>
        <span className="w-2 h-2 rounded-full bg-accent animate-pulse" />
        <span className={`text-xs font-mono tracking-wider ${textMuted}`}>
          DRONE SYSTEM READY
        </span>
      </div>
    </div>
  );
}

function DroneIcon({ className }) {
  return (
    <svg viewBox="0 0 100 100" fill="none" className={className} xmlns="http://www.w3.org/2000/svg">
      <circle cx="20" cy="20" r="10" stroke="currentColor" strokeWidth="4" />
      <circle cx="80" cy="20" r="10" stroke="currentColor" strokeWidth="4" />
      <circle cx="20" cy="80" r="10" stroke="currentColor" strokeWidth="4" />
      <circle cx="80" cy="80" r="10" stroke="currentColor" strokeWidth="4" />
      <line x1="20" y1="20" x2="42" y2="42" stroke="currentColor" strokeWidth="4" />
      <line x1="80" y1="20" x2="58" y2="42" stroke="currentColor" strokeWidth="4" />
      <line x1="20" y1="80" x2="42" y2="58" stroke="currentColor" strokeWidth="4" />
      <line x1="80" y1="80" x2="58" y2="58" stroke="currentColor" strokeWidth="4" />
      <rect x="38" y="38" width="24" height="24" rx="4" fill="currentColor" />
    </svg>
  );
}

function SunIcon({ className }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} xmlns="http://www.w3.org/2000/svg">
      <circle cx="12" cy="12" r="4" stroke="currentColor" strokeWidth="2" />
      <path stroke="currentColor" strokeWidth="2" strokeLinecap="round" d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
    </svg>
  );
}

function MoonIcon({ className }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className} xmlns="http://www.w3.org/2000/svg">
      <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z" />
    </svg>
  );
}