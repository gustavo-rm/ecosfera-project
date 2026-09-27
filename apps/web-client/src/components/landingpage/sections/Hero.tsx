import HeroScene from "@/sim-lite/three/HeroScene"

export default function Hero() {
  return (
    <section className="relative min-h-svh overflow-hidden">
      <HeroScene />

      <div className="relative mx-auto flex min-h-svh max-w-shell flex-col justify-center px-5 pb-24 pt-28">
        <div className="grid items-center gap-10 lg:grid-cols-12">
          <div className="lg:col-span-5">
            <h1
              className="font-display text-[44px] leading-[1.02] tracking-[-0.02em] sm:text-[58px]"
              style={{ fontWeight: 800 }}
            >
              Crie.
              <br />
              Explore.
              <br />
              Entenda.
              <br />
              <span className="text-lime">Transforme.</span>
            </h1>
            <p className="mt-6 max-w-[42ch] text-[15px] leading-relaxed text-muted">
              No Ecosfera, você cria o seu próprio planeta e descobre como ciência, vida e natureza
              trabalham juntas para manter tudo em equilíbrio.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <a
                href="#comecar"
                className="inline-flex items-center gap-2 rounded-xl bg-lime px-5 py-3 text-sm font-semibold text-[#06230A] transition-opacity hover:opacity-90"
              >
                Sou aluno
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <path d="M9 3h6M10 3v5.5L5.5 17A2.5 2.5 0 0 0 7.8 21h8.4a2.5 2.5 0 0 0 2.3-3.5L14 8.5V3" />
                </svg>
              </a>
              <a
                href="#professores"
                className="inline-flex items-center gap-2 rounded-xl border border-line bg-panel px-5 py-3 text-sm font-semibold text-ink transition-colors hover:border-azure"
              >
                Sou professor
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <path d="M9 3h6M10 3v5.5L5.5 17A2.5 2.5 0 0 0 7.8 21h8.4a2.5 2.5 0 0 0 2.3-3.5L14 8.5V3" />
                </svg>
              </a>
            </div>
          </div>

          <div className="hidden lg:col-span-4 lg:col-start-9 lg:block">
            <div className="rounded-2xl border border-line bg-panel/70 p-6 backdrop-blur-sm">
              <p className="font-display text-[19px] font-semibold leading-snug text-lime">
                Ciência. Vida.
                <br />
                Equilíbrio. Futuro.
              </p>
              <p className="mt-3 text-sm text-muted">Tudo começa com as suas escolhas.</p>
              <button
                className="mt-6 flex h-14 w-14 items-center justify-center rounded-full border border-azure/50 bg-azure/10 transition-colors hover:bg-azure/20"
                aria-label="Assistir apresentação"
              >
                <svg width="17" height="17" viewBox="0 0 24 24" fill="#E9EFFA">
                  <path d="M8 5.5v13l11-6.5-11-6.5Z" />
                </svg>
              </button>
            </div>
          </div>
        </div>

        <div className="absolute inset-x-0 bottom-8 flex justify-center">
          <div className="flex items-center gap-2.5 text-[11.5px] text-muted">
            <span className="flex h-[22px] w-[15px] items-start justify-center rounded-full border border-line pt-1">
              <span className="block h-[4px] w-[2px] animate-scrolldot rounded-full bg-lime motion-reduce:animate-none" />
            </span>
            Role para explorar
          </div>
        </div>
      </div>
    </section>
  )
}
