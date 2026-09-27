type SimulationControlsProps = {
  rotating: boolean
  onToggleRotating: () => void
  speed: number
  onSpeedChange: (speed: number) => void
}

export default function SimulationControls({ rotating, onToggleRotating, speed, onSpeedChange }: SimulationControlsProps) {
  return (
    <section className="mt-8">
      <h2 className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted">Simulação</h2>
      <div className="mt-3 rounded-xl border border-line bg-space/60 p-3.5">
        <div className="flex items-center justify-between">
          <span className="text-[12.5px]">Rotação e órbita</span>
          <button
            onClick={onToggleRotating}
            className="flex items-center gap-1.5 rounded-lg border border-line bg-panel px-2.5 py-1.5 text-[11.5px] font-medium transition-colors hover:border-azure"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
              {rotating ? <path d="M8 5h3v14H8zM13 5h3v14h-3z" /> : <path d="M8 5.5v13l11-6.5-11-6.5Z" />}
            </svg>
            <span>{rotating ? 'Girando' : 'Pausada'}</span>
          </button>
        </div>
        <div className="mt-3.5">
          <div className="flex items-center justify-between text-[11.5px] text-muted">
            <span>Velocidade</span>
            <span className="tabular">{speed.toFixed(1)}×</span>
          </div>
          <input
            type="range"
            min={0}
            max={4}
            step={0.1}
            value={speed}
            onChange={(e) => onSpeedChange(Number(e.target.value))}
            className="mt-2 w-full"
          />
        </div>
      </div>
      <p className="mt-3 text-[11px] leading-relaxed text-muted">
        Dados fictícios, só para ilustrar como a barra lateral do seu planeta poderia funcionar dentro do Ecosfera.
      </p>
    </section>
  )
}