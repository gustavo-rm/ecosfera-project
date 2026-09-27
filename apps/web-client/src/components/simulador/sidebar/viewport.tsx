'use client'

import { useEffect, useRef } from 'react'
import type { RefObject } from 'react'
import type { SimState, ViewMode } from '../types'
import { createPlanetSystemScene } from '@/rendering/scene/demo'

type ViewportProps = {
  simRef: RefObject<SimState>
  activeView: ViewMode
  onSetView: (view: ViewMode) => void
  onOpenSidebar: () => void
}

export default function Viewport({ simRef, activeView, onSetView, onOpenSidebar }: ViewportProps) {
  const viewportRef = useRef<HTMLDivElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    const viewport = viewportRef.current
    if (!canvas || !viewport) return
    return createPlanetSystemScene(canvas, viewport, simRef)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div ref={viewportRef} className="relative flex-1 overflow-hidden" style={{ touchAction: 'none' }}>
      <canvas ref={canvasRef} className="absolute inset-0 h-full w-full" />

      {/* cabeçalho flutuante */}
      <div className="pointer-events-none absolute inset-x-0 top-0 flex items-start justify-between p-4 sm:p-5">
        <div className="flex flex-wrap items-center gap-2.5">
          <div className="pointer-events-auto flex items-center gap-2.5 rounded-xl border border-line bg-panel/80 px-3.5 py-2.5 backdrop-blur-md">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <circle cx="12" cy="12" r="7" fill="#3FA9FF" />
              <path d="M5 12a7 7 0 0 1 9.5-6.5A6 6 0 0 0 12 17a7 7 0 0 1-7-5Z" fill="#7CE55C" />
            </svg>
            <div className="leading-tight">
              <p className="font-display text-[12.5px] font-bold tracking-[0.16em]">ECOSFERA</p>
              <p className="text-[10.5px] text-muted">Simulador de planeta</p>
            </div>
            <span className="ml-1 rounded-full border border-amber/40 bg-amber/10 px-2 py-0.5 text-[10px] font-semibold text-amber">
              Demonstração
            </span>
          </div>

          <div className="pointer-events-auto flex items-center gap-1 rounded-xl border border-line bg-panel/80 p-1 backdrop-blur-md">
            <button
              onClick={() => onSetView('system')}
              className={`rounded-lg px-3 py-1.5 text-[11.5px] font-medium transition-colors ${
                activeView === 'system' ? 'bg-lime text-[#06230A]' : 'text-muted hover:text-ink'
              }`}
            >
              Sistema
            </button>
            <button
              onClick={() => onSetView('planet')}
              className={`rounded-lg px-3 py-1.5 text-[11.5px] font-medium transition-colors ${
                activeView === 'planet' ? 'bg-lime text-[#06230A]' : 'text-muted hover:text-ink'
              }`}
            >
              Planeta
            </button>
          </div>
        </div>

        <button
          onClick={onOpenSidebar}
          className="pointer-events-auto flex h-10 w-10 items-center justify-center rounded-xl border border-line bg-panel/80 text-ink backdrop-blur-md transition-colors hover:border-azure md:hidden"
          aria-label="Abrir painel lateral"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M4 7h16M4 12h16M4 17h16" />
          </svg>
        </button>
      </div>

      {/* dica de interação */}
      <div className="pointer-events-none absolute inset-x-0 bottom-4 flex justify-center sm:bottom-5">
        <p className="rounded-full border border-line bg-panel/70 px-3.5 py-1.5 text-[11.5px] text-muted backdrop-blur-md">
          Arraste para girar a câmera · scroll para aproximar
        </p>
      </div>
    </div>
  )
}