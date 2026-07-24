'use client';

import dynamic from 'next/dynamic';

/** A cena WebGL só existe no cliente. Carregamos via `dynamic` com `ssr: false`
 *  para evitar mismatch de hidratação; o `SpaceBackdrop` cobre o intervalo de
 *  carregamento (e o caso de WebGL indisponível). */
const PlanetScene = dynamic(
  () => import('./PlanetScene').then((mod) => mod.PlanetScene),
  { ssr: false },
);

export function PlanetSceneClient() {
  return (
    <div className="pointer-events-none absolute inset-0 z-10" aria-hidden>
      <PlanetScene />
    </div>
  );
}
