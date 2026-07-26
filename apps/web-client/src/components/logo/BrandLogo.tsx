'use client';

import { motion } from 'framer-motion';
import { PlanetGlyph } from './PlanetGlyph';

/** Marca ECOSFERA no canto superior esquerdo, com brilho pulsante discreto no
 *  ícone e entrada suave. */
export function BrandLogo() {
  return (
    <motion.div
      className="flex items-center gap-3"
      initial={{ opacity: 0, y: -12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.8, ease: 'easeOut', delay: 0.1 }}
    >
      <div className="relative">
        <div className="animate-logo-pulse absolute inset-0 -z-10 rounded-full bg-cyan/40 blur-lg" />
        <PlanetGlyph className="h-9 w-9 drop-shadow-[0_0_10px_rgba(34,211,238,0.55)]" />
      </div>
      <span className="text-lg font-semibold tracking-[0.42em] text-soft/95 sm:text-xl">
        ECOSFERA
      </span>
    </motion.div>
  );
}
