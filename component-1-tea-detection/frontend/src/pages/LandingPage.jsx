import { useNavigate } from "react-router-dom";


export default function LandingPage() {
  const navigate = useNavigate();
 

  return (
    <div className="relative min-h-screen bg-ink text-white overflow-hidden">
      {/* Background image */}
      <div
        className="absolute inset-0 bg-cover bg-center"
        style={{ backgroundImage: "url('/assets/drone-hero.jpeg')" }}
      />
      {/* Dark gradient overlay so text stays readable */}
      <div className="absolute inset-0 bg-gradient-to-b from-ink/90 via-ink/70 to-ink" />

      {/* Top nav */}
      <nav className="relative z-10 flex items-center justify-between px-10 py-6">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center">
            <DroneIcon className="w-5 h-5 text-ink" />
          </div>
          <span className="text-lg font-semibold tracking-wide">TeaDrone</span>
        </div>
        <button
          onClick={() => navigate("/login")}
          className="text-sm px-4 py-2 rounded-full border border-border text-muted hover:text-white hover:border-accent transition"
        >
          Login
        </button>
       
      </nav>

      {/* Hero */}
      <main className="relative z-10 flex flex-col items-center justify-center text-center px-6 pt-20 pb-16">
        <div className="mb-8">
          <DroneIcon
            className="w-24 h-24 text-accent mx-auto"
            style={{ filter: "drop-shadow(0 0 30px rgba(198,241,53,0.35))" }}
          />
          {/* spray visualization beneath the drone */}
          <div className="w-40 h-8 mx-auto mt-2 bg-gradient-to-b from-accent/30 to-transparent rounded-full blur-md" />
        </div>

        <h1 className="text-5xl md:text-6xl font-bold tracking-tight mb-2">
          TEA<span className="text-accent">DRONE</span>
        </h1>
        <p className="text-sm md:text-base tracking-[0.3em] text-muted mb-10 uppercase">
          AI-Driven Precision Spraying
        </p>

        <button
          onClick={() => navigate("/login")}
          className="group flex items-center gap-2 px-8 py-4 rounded-full bg-gradient-to-r from-accent to-accent-dark text-ink font-semibold text-sm tracking-wide hover:scale-105 transition-transform"
        >
          START SYSTEM
          <span className="group-hover:translate-x-1 transition-transform inline-block">→</span>
        </button>
      </main>

      {/* System status indicator */}
      <div className="relative z-10 flex justify-center pb-8">
        <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-surface border border-border">
          <span className="w-2 h-2 rounded-full bg-accent animate-pulse" />
          <span className="text-xs font-mono tracking-wider text-muted">
            DRONE SYSTEM READY
          </span>
        </div>
      </div>
    </div>
  );
}

function DroneIcon({ className, style }) {
  return (
    <svg viewBox="0 0 100 100" fill="none" className={className} style={style} xmlns="http://www.w3.org/2000/svg">
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