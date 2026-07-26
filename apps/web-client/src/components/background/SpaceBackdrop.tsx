/** Camada de fundo em CSS (z-0). Garante um espaço profundo imediato antes do
 *  canvas WebGL montar — e um fallback elegante caso o WebGL não exista. */
export function SpaceBackdrop() {
  return (
    <div className="absolute inset-0 z-0 overflow-hidden" aria-hidden>
      <div className="space-backdrop absolute inset-0" />
      <div className="space-vignette absolute inset-0" />
    </div>
  );
}
