import type { Metadata } from 'next'
import SimulatorPage from '@/components/simulador/page'

export const metadata: Metadata = {
  title: 'Ecosfera — Simulador de Planeta (demonstração)',
  description: 'Protótipo de demonstração: um planeta orbitando uma estrela, com uma barra lateral de tarefas e dados do planeta.',
}

export default function SimuladorPage() {
  return <SimulatorPage />
}
