/** Ícone do planeta (marca). Um SVG próprio reproduz melhor o orbe azul
 *  brilhante com anel do que qualquer ícone genérico do Lucide. */
export function PlanetGlyph({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 48 48" className={className} fill="none" aria-hidden focusable="false">
      <defs>
        <radialGradient id="ecosfera-core" cx="40%" cy="34%" r="72%">
          <stop offset="0%" stopColor="#cdeeff" />
          <stop offset="42%" stopColor="#3b82f6" />
          <stop offset="100%" stopColor="#0b2f6b" />
        </radialGradient>
      </defs>
      <circle cx="24" cy="22" r="12" fill="url(#ecosfera-core)" />
      <ellipse
        cx="24"
        cy="24"
        rx="20.5"
        ry="7"
        transform="rotate(-20 24 24)"
        stroke="#22d3ee"
        strokeOpacity="0.75"
        strokeWidth="1.6"
      />
      <circle cx="19.5" cy="17.5" r="3.1" fill="#ffffff" fillOpacity="0.5" />
    </svg>
  );
}
