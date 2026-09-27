const SCIENCES: {
  name: string
  color: string
  text: string
  icon: React.ReactNode
}[] = [
  {
    name: 'Química',
    color: '#7C5CFF',
    text: 'Entenda as reações, elementos e ciclos químicos da natureza.',
    icon: (
      <>
        <circle cx="12" cy="6" r="2.2" />
        <circle cx="6" cy="16" r="2.2" />
        <circle cx="18" cy="16" r="2.2" />
        <path d="m10.4 7.6-2.8 6.8m8.8 0-2.8-6.8M8.2 16h7.6" />
      </>
    ),
  },
  {
    name: 'Física',
    color: '#B061FF',
    text: 'Explore leis físicas que regem energia, movimento e clima.',
    icon: (
      <>
        <circle cx="12" cy="12" r="2" />
        <ellipse cx="12" cy="12" rx="9.5" ry="4" />
        <ellipse cx="12" cy="12" rx="9.5" ry="4" transform="rotate(60 12 12)" />
        <ellipse cx="12" cy="12" rx="9.5" ry="4" transform="rotate(120 12 12)" />
      </>
    ),
  },
  {
    name: 'Biologia',
    color: '#3FA9FF',
    text: 'Estude os seres vivos, adaptações e relações ecológicas.',
    icon: (
      <>
        <path d="M12 21c0-7 3.6-10.6 9-11.6C20 16 16.4 19.6 12 21Z" />
        <path d="M12 21V12" />
      </>
    ),
  },
  {
    name: 'Ecologia',
    color: '#7CE55C',
    text: 'Analise ecossistemas e o equilíbrio entre os organismos.',
    icon: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M3.5 9.5h7l2 3-3 4 1 4M20 8l-4 1-1.5 3.5 3 2" />
      </>
    ),
  },
  {
    name: 'Geografia',
    color: '#4BD6A8',
    text: 'Mapeie relevos, climas, biomas e recursos naturais.',
    icon: (
      <>
        <path d="m3 18 6-10 4 7 3-4 5 7Z" />
        <circle cx="17" cy="6" r="1.6" />
      </>
    ),
  },
  {
    name: 'Matemática',
    color: '#7C5CFF',
    text: 'Use dados, estatísticas e cálculos para prever e planejar.',
    icon: <path d="M5 7h14M9.5 7v10.5c0 1.5-.8 2.5-2 2.5M15.5 7v10c0 2 1 3 2.5 3" />,
  },
  {
    name: 'Integração',
    color: '#3FA9FF',
    text: 'Todas as áreas se conectam em um aprendizado completo.',
    icon: (
      <>
        <circle cx="12" cy="12" r="2.6" />
        <circle cx="5" cy="6" r="1.9" />
        <circle cx="19" cy="6" r="1.9" />
        <circle cx="5" cy="18" r="1.9" />
        <circle cx="19" cy="18" r="1.9" />
        <path d="m6.6 7.4 3.6 3.2m7.2-3.2-3.6 3.2M6.6 16.6l3.6-3.2m7.2 3.2-3.6-3.2" />
      </>
    ),
  },
]

export default function SciencesSection() {
  return (
    <section id="ciencias" className="py-24">
      <div className="mx-auto max-w-shell px-5">
        <h2 className="text-center font-display text-[32px] font-bold tracking-[-0.02em] sm:text-[38px]">
          Ciências que se conectam
        </h2>
        <p className="mx-auto mt-4 max-w-[62ch] text-center text-[14.5px] leading-relaxed text-muted">
          Explore como diferentes disciplinas se unem para explicar o funcionamento do nosso planeta.
        </p>

        <ul className="mt-14 grid grid-cols-2 gap-x-6 gap-y-12 sm:grid-cols-3 lg:grid-cols-7">
          {SCIENCES.map((s) => (
            <li key={s.name} className="flex flex-col items-center text-center">
              <span
                className="flex h-[74px] w-[74px] items-center justify-center rounded-full border-2"
                style={{ borderColor: `${s.color}59`, background: `${s.color}14`, color: s.color }}
              >
                <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                  {s.icon}
                </svg>
              </span>
              <h3 className="mt-4 font-display text-[14.5px] font-semibold">{s.name}</h3>
              <p className="mt-2 max-w-[24ch] text-[12.5px] leading-relaxed text-muted">{s.text}</p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}
