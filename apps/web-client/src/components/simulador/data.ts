import type { Task } from './types'

/* =====================================================================
   DADOS FICTÍCIOS — tudo estático, só para a demonstração
====================================================================== */
export const INITIAL_TASKS: Task[] = [
  { title: 'Reduza a temperatura média abaixo de 30°C', tag: 'Ciências', due: 'até sex.', done: false },
  { title: 'Registre 3 espécies novas no seu ecossistema', tag: 'Biologia', due: 'entregue', done: true },
  { title: 'Explique o impacto da inclinação axial nas estações', tag: 'Geografia', due: 'até seg.', done: false },
  { title: 'Simule uma extinção em massa e analise a recuperação', tag: 'Ecologia', due: 'até qua.', done: false },
]

export const ORBIT_STATS = [
  { label: 'Raio', value: '6.400 km' },
  { label: 'Duração do dia', value: '23h 42min' },
  { label: 'Duração do ano', value: '372 dias' },
  { label: 'Inclinação axial', value: '21,3°' },
  { label: 'Gravidade', value: '0,98 g' },
  { label: 'Luas', value: '1' },
]

export const CONDITION_STATS = [
  { label: 'Temperatura média', value: '34°C', color: '#E9EFFA' },
  { label: 'Água superficial', value: '78%', color: '#3FA9FF' },
  { label: 'Biodiversidade', value: '92%', color: '#7CE55C' },
  { label: 'Estabilidade', value: '87%', color: '#7CE55C' },
]

/** Inclinação usada também para inclinar o planeta de verdade na cena 3D. */
export const AXIAL_TILT_DEG = 21.3

/* =====================================================================
   CÂMERA / ÓRBITA — presets de zoom e limites de scroll
====================================================================== */
export const VIEW_PLANET = 5 // só o planeta, de perto
export const VIEW_SYSTEM = 24 // dá pra ver a estrela e a órbita também
export const MIN_ZOOM = 4.2
export const MAX_ZOOM = 42