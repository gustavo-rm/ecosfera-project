import CtaScene from "@/sim-lite/three/CtaScene"

export default function FinalCta() {
  return (
    <section id="comecar" className="relative overflow-hidden py-32">
      <CtaScene />

      <div className="relative mx-auto max-w-shell px-5 text-center">
        <h2 className="mx-auto max-w-[20ch] font-display text-[32px] font-bold leading-tight tracking-[-0.02em] sm:text-[42px]">
          O futuro do planeta começa com a educação de hoje.
        </h2>
        <p className="mt-3 font-display text-[26px] font-bold text-lime sm:text-[34px]">Vamos criar juntos?</p>

        <div className="mt-10 flex flex-wrap justify-center gap-3">
          <a href="#" className="rounded-xl bg-lime px-6 py-3 text-sm font-semibold text-[#06230A] transition-opacity hover:opacity-90">
            Criar conta de aluno
          </a>
          <a href="#" className="rounded-xl border border-line bg-panel px-6 py-3 text-sm font-semibold text-ink transition-colors hover:border-azure">
            Criar conta de professor
          </a>
        </div>
      </div>
    </section>
  )
}
