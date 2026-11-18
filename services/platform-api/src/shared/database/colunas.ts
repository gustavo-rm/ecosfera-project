import type { ValueTransformer } from 'typeorm';

/** numeric do PostgreSQL chega como string; converte para number. */
export const numerico: ValueTransformer = {
  to: (v: number | null | undefined) => v,
  from: (v: string | null) =>
    v === null || v === undefined ? null : Number(v),
};

export const AGORA = () => 'now()';
export const JSON_VAZIO = {};

/** Conteúdo de coluna jsonb (objeto). */

export type Json = Record<string, any>;
