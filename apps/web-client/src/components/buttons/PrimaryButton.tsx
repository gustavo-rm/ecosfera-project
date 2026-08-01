'use client';

import type { ReactNode } from 'react';
import { motion } from 'framer-motion';
import { Leaf } from 'lucide-react';

interface PrimaryButtonProps {
  children: ReactNode;
  type?: 'submit' | 'button';
  onClick?: () => void;
}

/** Botão principal "Enter my planet": gradiente verde, brilho, ícone de folha e
 *  microinterações (hover luminoso + compressão elástica no clique). */
export function PrimaryButton({ children, type = 'submit', onClick }: PrimaryButtonProps) {
  return (
    <motion.button
      type={type}
      onClick={onClick}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.97 }}
      transition={{ type: 'spring', stiffness: 420, damping: 17 }}
      className="group relative flex h-14 w-full items-center justify-center gap-2 overflow-hidden rounded-2xl bg-linear-to-r from-bio via-[#10b981] to-[#059f7a] text-sm font-semibold uppercase tracking-[0.16em] text-white shadow-[0_12px_34px_-10px_rgba(16,185,129,0.75)] outline-none transition-shadow duration-300 hover:shadow-[0_16px_44px_-8px_rgba(16,185,129,0.9)] focus-visible:ring-2 focus-visible:ring-bio-bright/70"
    >
      <span className="absolute inset-0 bg-white/0 transition-colors duration-300 group-hover:bg-white/10" />
      <span className="relative">{children}</span>
      <Leaf className="relative h-4.5 w-4.5" strokeWidth={2} />
    </motion.button>
  );
}
