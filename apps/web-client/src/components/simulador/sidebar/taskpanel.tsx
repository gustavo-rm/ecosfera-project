import type { Task } from '../types'

type TasksPanelProps = {
  tasks: Task[]
  onToggle: (index: number) => void
}

export default function TasksPanel({ tasks, onToggle }: TasksPanelProps) {
  const doneCount = tasks.filter((t) => t.done).length

  return (
    <section>
      <div className="flex items-center justify-between">
        <h2 className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted">Tarefas do professor</h2>
        <span className="tabular text-[11px] text-muted">
          {doneCount}/{tasks.length}
        </span>
      </div>
      <ul className="mt-3 space-y-2">
        {tasks.map((t, i) => (
          <li key={t.title}>
            <button
              onClick={() => onToggle(i)}
              className="flex w-full items-start gap-2.5 rounded-lg border border-line bg-space/60 px-3 py-2.5 text-left transition-colors hover:border-azure/60"
            >
              <span
                className={`mt-0.5 flex h-[18px] w-[18px] shrink-0 items-center justify-center rounded-md border ${
                  t.done ? 'border-lime bg-lime' : 'border-line'
                }`}
              >
                {t.done && (
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#06230A" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                    <path d="m5 12.5 4.5 4.5L19 7" />
                  </svg>
                )}
              </span>
              <span className="min-w-0 flex-1">
                <span className={`block text-[12.5px] leading-snug ${t.done ? 'text-muted line-through' : 'text-ink'}`}>{t.title}</span>
                <span className="mt-1 flex items-center gap-2">
                  <span className="rounded-full border border-line px-1.5 py-0.5 text-[10px] text-muted">{t.tag}</span>
                  <span className={`text-[10px] ${t.done ? 'text-lime' : 'text-muted'}`}>{t.due}</span>
                </span>
              </span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}