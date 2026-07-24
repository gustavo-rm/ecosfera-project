/** Divisor "OR" com linhas que se desvanecem nas extremidades. */
export function FormDivider() {
  return (
    <div className="flex items-center gap-4">
      <span className="h-px flex-1 bg-gradient-to-r from-transparent to-white/15" />
      <span className="text-xs font-medium tracking-[0.2em] text-white/40">OR</span>
      <span className="h-px flex-1 bg-gradient-to-l from-transparent to-white/15" />
    </div>
  );
}
