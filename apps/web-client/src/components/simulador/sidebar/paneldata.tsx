import { ORBIT_STATS, CONDITION_STATS } from "../data"

export default function PlanetDataPanel() {
  return (
    <section className="mt-8">
      <h2 className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted">Dados do planeta</h2>

      <div className="mt-3 flex items-center justify-between rounded-lg border border-line bg-space/60 px-3 py-2.5">
        <span className="text-[12.5px] text-muted">Tipo</span>
        <span className="text-[12.5px] font-medium">Terrestre</span>
      </div>

      <p className="mb-2 mt-4 text-[11px] font-medium text-muted">Órbita e rotação</p>
      <div className="grid grid-cols-2 gap-2">
        {ORBIT_STATS.map((s) => (
          <div key={s.label} className="rounded-lg border border-line bg-space/60 px-2.5 py-2">
            <p className="text-[10px] text-muted">{s.label}</p>
            <p className="tabular mt-0.5 text-[12.5px] font-semibold">{s.value}</p>
          </div>
        ))}
      </div>

      <p className="mb-2 mt-4 text-[11px] font-medium text-muted">Condições atuais</p>
      <div className="grid grid-cols-2 gap-2">
        {CONDITION_STATS.map((s) => (
          <div key={s.label} className="rounded-lg border border-line bg-space/60 px-2.5 py-2">
            <p className="text-[10px] text-muted">{s.label}</p>
            <p className="tabular mt-0.5 text-[12.5px] font-semibold" style={{ color: s.color }}>
              {s.value}
            </p>
          </div>
        ))}
      </div>
    </section>
  )
}