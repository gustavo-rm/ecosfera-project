'use client';

import type { ReactNode } from 'react';
import { motion } from 'framer-motion';

interface SecondaryButtonProps {
  children: ReactNode;
  onClick?: () => void;
}

/** Botão secundário "Create account": contorno ciano translúcido com realce
 *  suave no hover. */
export function SecondaryButton({ children, onClick }: SecondaryButtonProps) {
  return (
    <motion.button
      type="button"
      onClick={onClick}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.97 }}
      transition={{ type: 'spring', stiffness: 420, damping: 17 }}
      className="flex h-14 w-full items-center justify-center rounded-2xl border border-cyan/45 bg-cyan/5 text-sm font-semibold uppercase tracking-[0.16em] text-cyan outline-none transition-colors duration-300 hover:border-cyan/80 hover:bg-cyan/10 focus-visible:ring-2 focus-visible:ring-cyan/70"
    >
      {children}
    </motion.button>
  );
}
