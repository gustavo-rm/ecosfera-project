export type Task = {
  title: string
  tag: string
  due: string
  done: boolean
}

export type ViewMode = 'system' | 'planet'

/**
 * Estado mutável lido a cada quadro pelo loop de animação da cena 3D.
 * A UI (React) só ESCREVE nele a partir de cliques/inputs — o loop de
 * animação só LÊ. Assim, mudar a velocidade no slider não precisa
 * recriar a cena inteira a cada tecla.
 */
export type SimState = {
  rotating: boolean
  speed: number
  targetRadius: number
}