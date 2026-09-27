export default function PlanetSection() {
  return (
    <section id="planeta" className="relative overflow-hidden py-24">
      <div className="relative z-10 mx-auto max-w-shell px-5">
        <div className="grid items-center gap-14 lg:grid-cols-2">
          <div>
            <h2 className="font-display text-[34px] font-bold leading-tight tracking-[-0.02em] sm:text-[40px]">
              Seu planeta,
              <br />
              suas <span className="text-lime">descobertas</span>
            </h2>
            <p className="mt-5 max-w-[46ch] text-[15px] leading-relaxed text-muted">
              Crie, personalize e evolua o seu planeta. Cada escolha impacta o clima, a vida, os
              recursos e os ecossistemas.
            </p>

            <div className="mt-10 grid gap-x-8 gap-y-7 sm:grid-cols-2">
              <Feature
                color="lime"
                title="Criação livre"
                text="Dê forma ao seu planeta do zero."
                icon={<path d="M20 4C10 4 4 9 4 17v3M20 4c0 9-5 13-12 13H5" />}
              />
              <Feature
                color="azure"
                title="Simulações reais"
                text="Veja as consequências das suas decisões em tempo real."
                icon={<path d="M4 20V10M10 20V4M16 20v-7M22 20H2" />}
              />
              <Feature
                color="lime"
                title="Vida e ecossistemas"
                text="Observe a evolução da vida e das cadeias alimentares."
                icon={
                  <>
                    <path d="M12 21c0-6 3-9 8-10-1 6-4 9-8 10Z" />
                    <path d="M12 21c0-5-2.5-8-7-9 1 5 3.5 8 7 9Z" />
                    <path d="M12 21v-4" />
                  </>
                }
              />
              <Feature
                color="amber"
                title="Desafios e missões"
                text="Cumpra missões, desbloqueie recursos e torne-se guardião do planeta."
                icon={<path d="m12 3 2.6 5.5 6 .9-4.3 4.2 1 6-5.3-2.9L6.7 19.6l1-6L3.4 9.4l6-.9L12 3Z" />}
              />
            </div>
          </div>

          {/* Painel do mundo */}
          <div className="rounded-2xl border border-line bg-panel/90 p-3 backdrop-blur-md">
            <div className="relative overflow-hidden rounded-xl" style={{ aspectRatio: '4 / 3' }}>
              <svg
                viewBox="0 0 400 300"
                className="h-full w-full"
                preserveAspectRatio="xMidYMid slice"
                role="img"
                aria-label="Vista do bioma criado pelo aluno"
              >
                <rect width="400" height="300" fill="#2E6FA8" />
                <circle cx="320" cy="52" r="20" fill="#F2F7FF" opacity=".9" />
                <ellipse cx="80" cy="60" rx="46" ry="16" fill="#4E8FC4" />
                <ellipse cx="112" cy="52" rx="30" ry="13" fill="#5C9BCE" />
                <ellipse cx="250" cy="44" rx="38" ry="13" fill="#4E8FC4" />
                <path d="M0 150 90 78l62 72Z" fill="#4A5A6B" />
                <path d="M90 78 152 150H108Z" fill="#5E7185" />
                <path d="M60 106 90 78l14 16-18 12Z" fill="#E8F1FA" />
                <path d="M140 156 215 92l70 64Z" fill="#3F4E5D" />
                <path d="M215 92 285 156h-44Z" fill="#54677A" />
                <path d="M280 160 340 108l60 52Z" fill="#4A5A6B" />
                <rect y="148" width="400" height="152" fill="#2F7D4E" />
                <path
                  d="M0 176c70-16 120 10 186 4 62-6 108-24 214-14v40c-96-8-150 12-212 16-66 4-118-18-188-8Z"
                  fill="#2A6EA8"
                />
                <path
                  d="M0 184c70-14 120 10 186 4 62-6 108-22 214-12v22c-96-8-150 10-212 14-66 4-118-16-188-6Z"
                  fill="#3E92C9"
                />
                <rect y="212" width="400" height="88" fill="#357F4F" />
                <path
                  d="M0 230c60 14 110-10 170-2 58 8 110 26 230 10v62H0Z"
                  fill="#2B6B42"
                />
                <g fill="#1F5533">
                  <path d="M40 252l10-20 10 20zM44 262l6-13 6 13z" />
                  <path d="M300 246l11-22 11 22zM304 258l7-15 7 15z" />
                  <path d="M355 266l9-18 9 18z" />
                  <path d="M120 272l8-16 8 16z" />
                </g>
              </svg>

              <div className="absolute right-3 top-3 w-[124px] space-y-2">
                <Metric label="Temperatura" value="34°C" valueClass="text-ink" />
                <Metric label="Água" value="78%" valueClass="text-azure" />
                <Metric label="Biodiversidade" value="92%" valueClass="text-lime" />
                <Metric label="Estabilidade" value="87%" valueClass="text-lime" />
              </div>

              <div className="absolute bottom-3 left-3 flex gap-1.5 rounded-xl border border-line bg-space/85 p-1.5 backdrop-blur-sm">
                <ToolButton active label="Vegetação">
                  <path d="m12 3 6 9h-4l4 7H6l4-7H6l6-9Z" />
                </ToolButton>
                <ToolButton label="Água" hoverClass="hover:text-azure">
                  <path d="M12 3s6 6.5 6 10.5A6 6 0 0 1 6 13.5C6 9.5 12 3 12 3Z" />
                </ToolButton>
                <ToolButton label="Relevo">
                  <path d="m3 19 6-11 4.5 8M11 19l4-7 6 7Z" />
                </ToolButton>
                <ToolButton label="Clima">
                  <path d="M3 9h12a3 3 0 1 0-3-3M3 14h16a3 3 0 1 1-3 3M3 19h8" />
                </ToolButton>
                <ToolButton label="Vida" hoverClass="hover:text-violet">
                  <circle cx="12" cy="12" r="3" />
                  <circle cx="5" cy="7" r="2" />
                  <circle cx="19" cy="7" r="2" />
                  <circle cx="5" cy="17" r="2" />
                  <circle cx="19" cy="17" r="2" />
                  <path d="m7 8 3 3m7-3-3 3m-4 5-3 2m10-2-3-2" />
                </ToolButton>
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
  color: 'lime' | 'azure' | 'amber'
  title: string
  text: string
  icon: React.ReactNode
}) {
  const styles: Record<typeof color, string> = {
    lime: 'border-lime/30 bg-lime/10 text-lime',
    azure: 'border-azure/30 bg-azure/10 text-azure',
    amber: 'border-[#F5C451]/30 bg-[#F5C451]/10 text-[#F5C451]',
  }
  return (
    <div className="flex gap-3.5">
      <span className={`mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border ${styles[color]}`}>
        <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
          {icon}
        </svg>
      </span>
      <div>
        <h3 className={`text-[14.5px] font-semibold ${color === 'lime' ? 'text-lime' : 'text-ink'}`}>{title}</h3>
        <p className="mt-1 text-[13.5px] leading-relaxed text-muted">{text}</p>
      </div>
    </div>
  )
}

function Metric({ label, value, valueClass }: { label: string; value: string; valueClass: string }) {
  return (
    <div className="rounded-lg border border-line bg-space/85 px-3 py-2 backdrop-blur-sm">
      <p className="text-[10px] text-muted">{label}</p>
      <p className={`tabular mt-0.5 font-display text-[17px] font-semibold ${valueClass}`}>{value}</p>
    </div>
  )
}

function ToolButton({
  children,
  label,
  active,
  hoverClass = 'hover:text-ink',
}: {
  children: React.ReactNode
  label: string
  active?: boolean
  hoverClass?: string
}) {
  return (
    <button
      className={`flex h-8 w-8 items-center justify-center rounded-lg transition-colors ${
        active ? 'bg-lime/15 text-lime' : `text-muted ${hoverClass}`
      }`}
      aria-label={label}
    >
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        {children}
      </svg>
    </button>
  )
}
