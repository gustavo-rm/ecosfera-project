import type { Task } from '../types'
import TasksPanel from './taskpanel'
import PlanetDataPanel from './paneldata'
import SimulationControls from './controls'

type SidebarProps = {
  open: boolean
  onClose: () => void
  tasks: Task[]
  onToggleTask: (index: number) => void
  rotating: boolean
  onToggleRotating: () => void
  speed: number
  onSpeedChange: (speed: number) => void
}

export default function Sidebar({
  open,
  onClose,
  tasks,
  onToggleTask,
  rotating,
  onToggleRotating,
  speed,
  onSpeedChange,
}: SidebarProps) {
  return (
    <aside
      className={`fixed inset-y-0 right-0 z-40 flex w-[min(360px,86vw)] shrink-0 flex-col border-l border-line bg-panel/95 backdrop-blur-md transition-transform duration-300 md:static md:w-[340px] md:translate-x-0 md:bg-panel ${
        open ? 'translate-x-0' : 'translate-x-full'
      }`}
    >
      <div className="flex items-center justify-between border-b border-line px-5 py-4">
        <div>
          <p className="font-display text-[16px] font-bold">Aurora</p>
          <p className="text-[12px] text-muted">Planeta terrestre · criado por você</p>
        </div>
        <button
          onClick={onClose}
          className="flex h-8 w-8 items-center justify-center rounded-lg text-muted transition-colors hover:text-ink md:hidden"
          aria-label="Fechar painel lateral"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="m6 6 12 12M18 6 6 18" />
          </svg>
        </button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5">
        <TasksPanel tasks={tasks} onToggle={onToggleTask} />
        <PlanetDataPanel />
        <SimulationControls rotating={rotating} onToggleRotating={onToggleRotating} speed={speed} onSpeedChange={onSpeedChange} />
      </div>
    </aside>
  )
}