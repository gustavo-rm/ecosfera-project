/** Sol distante + lens flare no canto superior direito.
 *
 *  Decisão de projeto: renderizado em CSS (com `mix-blend-screen`) sobre o
 *  canvas, em vez de dentro da cena 3D. Isso garante posicionamento nítido e
 *  estável em todos os breakpoints (um Sol dentro da cena sairia do quadro em
 *  telas estreitas) e mantém a luz coerente com a `directionalLight`. */
export function SunFlare() {
  return (
    <div
      className="pointer-events-none absolute inset-0 z-20 overflow-hidden mix-blend-screen"
      aria-hidden
    >
      <div className="sun-halo animate-flare-breathe absolute -right-16 -top-20 h-80 w-80 rounded-full blur-2xl" />
      <div className="sun-core absolute right-8 top-6 h-24 w-24 rounded-full blur-md sm:right-16 sm:top-10" />

      <div className="sun-streak-h absolute right-4 top-17 h-px w-115 max-w-[60vw] sm:right-14 sm:top-22" />
      <div className="sun-streak-v absolute right-19 top-0 h-80 w-px sm:right-33" />

      <span className="absolute right-52.5 top-47.5 h-4 w-4 rounded-full bg-atmo-bright/30 blur-[2px]" />
      <span className="absolute right-82.5 top-70 h-6 w-6 rounded-full bg-bio/15 blur-[3px]" />
      <span className="absolute right-70 top-59 h-2 w-2 rounded-full bg-amber/40" />
    </div>
  );
}
