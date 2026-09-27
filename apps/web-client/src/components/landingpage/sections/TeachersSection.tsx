const CLASSES = [
  { name: 'Turma 7A', v: 85 },
  { name: 'Turma 8B', v: 72 },
  { name: 'Turma 9C', v: 68 },
  { name: 'Turma 1A EM', v: 90 },
]

const ACTIVITY = [
  { t: 'Nova missão criada', s: 'Energia e sustentabilidade', when: 'Hoje', color: '#7CE55C' },
  { t: 'Aluna Maria evoluiu o planeta', s: 'Turma 8B', when: 'Hoje', color: '#3FA9FF' },
  { t: 'Relatório de turma disponível', s: 'Turma 7A', when: 'Ontem', color: '#7C5CFF' },
]

export default function TeachersSection() {
  return (
    <section id="professores" className="py-24">
      <div className="mx-auto max-w-shell px-5">
        <div className="grid items-center gap-14 lg:grid-cols-2">
          <div>
            <h2 className="font-display text-[34px] font-bold leading-tight tracking-[-0.02em] sm:text-[40px]">
              Para professores,
              <br />
              insights que <span className="text-lime">transformam</span>
            </h2>
            <p className="mt-5 max-w-[46ch] text-[15px] leading-relaxed text-muted">
              Acompanhe o progresso dos alunos, crie missões personalizadas e leve suas aulas para
              um novo nível.
            </p>

            <div className="mt-10 grid gap-x-8 gap-y-7 sm:grid-cols-2">
              <Feature
                color="azure"
                title="Acompanhe em tempo real"
                text="Veja relatórios de desempenho e evolução por aluno ou turma."
                icon={<path d="M4 20V11M10 20V6M16 20v-9M22 20H2" />}
              />
              <Feature
                color="violet"
                title="Missões personalizadas"
                text="Crie desafios alinhados aos conteúdos das suas aulas."
                icon={
                  <>
                    <circle cx="12" cy="12" r="8" />
                    <circle cx="12" cy="12" r="3.4" />
                    <path d="M12 2v3m0 14v3M2 12h3m14 0h3" strokeLinecap="round" />
                  </>
                }
              />
              <Feature
                color="lime"
                title="Avaliação inteligente"
                text="Avalie competências, decisões e raciocínio científico."
                icon={
                  <>
                    <circle cx="12" cy="12" r="9" />
                    <path d="m8 12.5 2.8 2.8L16 10" />
                  </>
                }
              />
              <Feature
                color="azure"
                title="Engajamento garantido"
                text="Aprendizado ativo, criativo e conectado com a realidade."
                icon={
                  <>
                    <circle cx="9" cy="9" r="3.2" />
                    <path d="M3 20a6 6 0 0 1 12 0" />
                    <circle cx="17.5" cy="10" r="2.6" />
                    <path d="M15 20a5 5 0 0 1 7-4.6" />
                  </>
                }
              />
            </div>
          </div>

          {/* Painel do professor */}
          <div className="rounded-2xl border border-line bg-panel/90 backdrop-blur-md">
            <div className="flex items-center justify-between border-b border-line px-5 py-4">
              <p className="font-display text-[15px] font-semibold">Painel do professor</p>
              <span className="flex gap-1.5">
                <i className="block h-2 w-2 rounded-full bg-line" />
                <i className="block h-2 w-2 rounded-full bg-line" />
                <i className="block h-2 w-2 rounded-full bg-lime" />
              </span>
            </div>

            <div className="flex gap-5 border-b border-line px-5 text-[13px]">
              <button className="border-b-2 border-lime py-3 font-medium text-ink">Visão geral</button>
              <button className="border-b-2 border-transparent py-3 text-muted transition-colors hover:text-ink">Turmas</button>
              <button className="border-b-2 border-transparent py-3 text-muted transition-colors hover:text-ink">Missões</button>
              <button className="border-b-2 border-transparent py-3 text-muted transition-colors hover:text-ink">Relatórios</button>
            </div>

            <div className="grid grid-cols-2 gap-3 p-5 sm:grid-cols-4">
              <Stat label="Turmas ativas" value="8" />
              <Stat label="Alunos" value="128" />
              <Stat label="Missões criadas" value="24" />
              <Stat label="Planetas criados" value="312" />
            </div>

            <div className="grid gap-5 px-5 pb-5 md:grid-cols-2">
              <div className="rounded-xl border border-line bg-deep p-4">
                <p className="text-[12px] font-medium text-muted">Progresso das turmas</p>
                <ul className="mt-4 space-y-3.5">
                  {CLASSES.map((c) => (
                    <li key={c.name} className="flex items-center gap-3 text-[12.5px]">
                      <span className="w-[70px] shrink-0 text-muted">{c.name}</span>
                      <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-line">
                        <span className="block h-full rounded-full bg-lime" style={{ width: `${c.v}%` }} />
                      </span>
                      <span className="tabular w-9 text-right font-medium">{c.v}%</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="rounded-xl border border-line bg-deep p-4">
                <p className="text-[12px] font-medium text-muted">Atividade recente</p>
                <ul className="mt-4 space-y-3.5">
                  {ACTIVITY.map((a) => (
                    <li key={a.t} className="flex items-start gap-3">
                      <span
                        className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg"
                        style={{ background: `${a.color}1F`, color: a.color }}
                      >
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M5 12.5 9.5 17 19 7" />
                        </svg>
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-[12.5px] font-medium">{a.t}</span>
                        <span className="block truncate text-[11.5px] text-muted">{a.s}</span>
                      </span>
                      <span className="shrink-0 text-[11px] text-muted">{a.when}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

function Feature({
  color,
  title,
  text,
  icon,
}: {
  color: 'lime' | 'azure' | 'violet'
  title: string
  text: string
  icon: React.ReactNode
}) {
  const styles: Record<typeof color, string> = {
    lime: 'border-lime/30 bg-lime/10 text-lime',
    azure: 'border-azure/30 bg-azure/10 text-azure',
    violet: 'border-violet/30 bg-violet/10 text-violet',
  }
  return (
    <div className="flex gap-3.5">
      <span className={`mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border ${styles[color]}`}>
        <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
          {icon}
        </svg>
      </span>
      <div>
        <h3 className="text-[14.5px] font-semibold text-ink">{title}</h3>
        <p className="mt-1 text-[13.5px] leading-relaxed text-muted">{text}</p>
      </div>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-line bg-deep px-3 py-3">
      <p className="text-[10.5px] text-muted">{label}</p>
      <p className="tabular mt-1 font-display text-[22px] font-semibold">{value}</p>
    </div>
  )
}
