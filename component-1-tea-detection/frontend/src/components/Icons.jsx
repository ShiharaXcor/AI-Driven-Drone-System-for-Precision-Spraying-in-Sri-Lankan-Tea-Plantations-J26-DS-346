export function DroneIcon({ className, style }) {
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

export function SunIcon({ className }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} xmlns="http://www.w3.org/2000/svg">
      <circle cx="12" cy="12" r="4" stroke="currentColor" strokeWidth="2" />
      <path stroke="currentColor" strokeWidth="2" strokeLinecap="round" d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
    </svg>
  );
}

export function MoonIcon({ className }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className} xmlns="http://www.w3.org/2000/svg">
      <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z" />
    </svg>
  );
}