/**
 * Papéis da plataforma. Valores iguais ao enum `platform.user_role`
 * (baseline + migração 1794880000000). Nomes do domínio em português
 * ficam nos comentários e no glossário (ADR 0008).
 */
export const PAPEIS = [
  'student', // aluno
  'teacher', // professor
  'coordinator', // coordenador
  'admin', // administrador da escola
  'guardian', // responsável
  'researcher', // pesquisador
  'platform_admin', // operador da plataforma (cria escolas)
] as const;
export type Papel = (typeof PAPEIS)[number];

export const PAPEIS_DE_EQUIPE_ESCOLAR: readonly Papel[] = [
  'teacher',
  'coordinator',
  'admin',
];

/** Papéis que um admin de escola pode atribuir. */
export const PAPEIS_ATRIBUIVEIS_PELA_ESCOLA: readonly Papel[] = [
  'student',
  'teacher',
  'coordinator',
  'admin',
  'guardian',
];

export function ehPapel(v: unknown): v is Papel {
  return typeof v === 'string' && (PAPEIS as readonly string[]).includes(v);
}
