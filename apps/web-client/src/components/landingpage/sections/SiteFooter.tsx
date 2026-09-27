export default function SiteFooter() {
  return (
    <footer className="border-t border-line/60 bg-space">
      <div className="mx-auto flex max-w-shell flex-col items-center justify-between gap-5 px-5 py-8 sm:flex-row">
        <div className="flex items-center gap-2.5">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <circle cx="12" cy="12" r="7" fill="#3FA9FF" />
            <path d="M5 12a7 7 0 0 1 9.5-6.5A6 6 0 0 0 12 17a7 7 0 0 1-7-5Z" fill="#7CE55C" />
          </svg>
          <span className="font-display text-[13px] font-bold tracking-[0.22em]">ECOSFERA</span>
        </div>
        <p className="text-[13px] text-lime">Ciência. Vida. Equilíbrio. Futuro.</p>
        <div className="flex gap-3 text-muted">
          <a href="#" aria-label="Instagram" className="transition-colors hover:text-ink">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
              <rect x="3" y="3" width="18" height="18" rx="5" />
              <circle cx="12" cy="12" r="4" />
              <circle cx="17.2" cy="6.8" r="1" fill="currentColor" stroke="none" />
            </svg>
          </a>
          <a href="#" aria-label="YouTube" className="transition-colors hover:text-ink">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round">
              <rect x="2.5" y="5.5" width="19" height="13" rx="4" />
              <path d="M10.5 9.5 15 12l-4.5 2.5Z" />
            </svg>
          </a>
          <a href="#" aria-label="Discord" className="transition-colors hover:text-ink">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round">
              <path d="M8 6.5 6 6C4 8 3 11 3 15l3 2 1.2-2M16 6.5 18 6c2 2 3 5 3 9l-3 2-1.2-2" />
              <path d="M7.2 15c3 1.6 6.6 1.6 9.6 0" />
              <circle cx="9.5" cy="12" r="1.1" fill="currentColor" stroke="none" />
              <circle cx="14.5" cy="12" r="1.1" fill="currentColor" stroke="none" />
            </svg>
          </a>
        </div>
      </div>
    </footer>
  )
}
