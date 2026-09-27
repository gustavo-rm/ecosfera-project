export default function Navbar() {
  return (
    <header className="fixed top-0 inset-x-0 z-50 border-b border-line/60 bg-space/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-shell items-center justify-between px-5">
        <a href="#" className="flex items-center gap-2.5">
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <circle cx="12" cy="12" r="7" fill="#3FA9FF" />
            <path d="M5 12a7 7 0 0 1 9.5-6.5A6 6 0 0 0 12 17a7 7 0 0 1-7-5Z" fill="#7CE55C" />
            <ellipse cx="12" cy="12" rx="11" ry="4" transform="rotate(-22 12 12)" stroke="#7CE55C" strokeWidth="1.3" />
          </svg>
          <span className="font-display text-[15px] font-bold tracking-[0.22em] text-ink">ECOSFERA</span>
        </a>

        <nav className="hidden items-center gap-7 text-[13.5px] text-muted lg:flex">
          <a className="transition-colors hover:text-ink" href="#planeta">Sobre</a>
          <a className="transition-colors hover:text-ink" href="#planeta">Recursos</a>
          <a className="transition-colors hover:text-ink" href="#professores">Para professores</a>
          <a className="transition-colors hover:text-ink" href="#ciencias">Como funciona</a>
          <a className="transition-colors hover:text-ink" href="#comecar">Depoimentos</a>
        </nav>

        <div className="flex items-center gap-2.5">
          <a
            href="#comecar"
            className="hidden rounded-lg border border-line px-4 py-2 text-[13.5px] font-medium text-ink transition-colors hover:border-azure sm:block"
          >
            Entrar
          </a>
          <a
            href="#comecar"
            className="rounded-lg bg-lime px-4 py-2 text-[13.5px] font-semibold text-[#06230A] transition-opacity hover:opacity-90"
          >
            Começar agora
          </a>
        </div>
      </div>
    </header>
  )
}
