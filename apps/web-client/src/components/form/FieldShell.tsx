import type { ReactNode } from 'react';
import type { LucideIcon } from 'lucide-react';

interface FieldShellProps {
  icon: LucideIcon;
  children: ReactNode;
  trailing?: ReactNode;
}

/** Moldura compartilhada dos campos: ícone à esquerda, glow ciano ao focar e
 *  transição suave. Centraliza o visual para evitar classes repetidas. */
export function FieldShell({ icon: Icon, children, trailing }: FieldShellProps) {
  return (
    <div className="group flex h-14 items-center gap-3 rounded-2xl border border-white/10 bg-white/4 px-4 transition-all duration-300 focus-within:border-cyan/60 focus-within:bg-white/6 focus-within:shadow-[0_0_0_1px_rgba(34,211,238,0.28),0_0_28px_-8px_rgba(34,211,238,0.55)]">
      <Icon
        className="h-4.5 w-4.5 shrink-0 text-white/40 transition-colors duration-300 group-focus-within:text-cyan"
        strokeWidth={1.75}
      />
      {children}
      {trailing}
    </div>
  );
}
