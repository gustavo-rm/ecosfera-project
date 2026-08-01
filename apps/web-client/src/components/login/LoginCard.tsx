'use client';

import type { ReactNode } from 'react';
import { motion } from 'framer-motion';

/** Cartão glassmorphism: fundo azul translúcido, blur de fundo, borda iluminada
 *  e sombra difusa. Entra com fade + leve subida + desfoque desaparecendo. */
export function LoginCard({ children }: { children: ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 24, filter: 'blur(14px)' }}
      animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
      transition={{
        duration: 0.9,
        ease: [0.22, 1, 0.36, 1] as [number, number, number, number],
        delay: 0.15,
      }}
      className="relative w-full rounded-[28px] border-[.5px] backdrop-blur-[7px] bg-black/25 border-white/30 p-7 shadow-[0_30px_80px_-20px_rgba(0,0,0,0.75)] sm:p-9"
    >
      <div className="pointer-events-none absolute inset-0 rounded-[28px]" />
      <div className="pointer-events-none absolute inset-0 rounded-[28px] shadow-[inset_0_1px_0_0_rgba(255,255,255,0.16)] ring-1 ring-inset ring-atmo/15" />
      <div className="relative">{children}</div>
    </motion.div>
  );
}
