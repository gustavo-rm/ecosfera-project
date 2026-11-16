/**
 * Anonimização do dataset de pesquisa (RNF-011, RF-078).
 * Método:
 *  1. identificadores diretos (nome, e-mail, ids) nunca entram; o id do aluno vira pseudônimo
 *     com sal aleatório descartado ao fim da exportação (não ligável entre exportações);
 *  2. quase-identificadores generalizados: escola → pseudônimo; data → semana ISO; turma → nível;
 *  3. k-anonimato por supressão: grupos (escola, nível) com menos de k alunos são removidos.
 * Limite: com k pequeno e turmas pequenas, há risco residual de reidentificação por cruzamento
 * com dados externos; por isso k padrão = 5 e o dataset é auditado.
 */
export interface LinhaBruta {
  alunoId: string;
  escolaId: string;
  nivel: string | null;
  competencia: string;
  probabilidade: number;
  incerteza: number | null;
  evidencias: number;
  atualizadoEm: Date;
  sintetico: boolean;
}

export interface LinhaAnonima {
  student: string;
  school: string;
  trackLevel: string;
  competency: string;
  probability: number;
  uncertainty: number | null;
  evidenceCount: number;
  week: string;
  synthetic: boolean;
}

export function semanaIso(d: Date): string {
  const t = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()));
  const dia = t.getUTCDay() || 7;
  t.setUTCDate(t.getUTCDate() + 4 - dia);
  const inicio = new Date(Date.UTC(t.getUTCFullYear(), 0, 1));
  const semana = Math.ceil(((t.getTime() - inicio.getTime()) / 86_400_000 + 1) / 7);
  return `${t.getUTCFullYear()}-W${String(semana).padStart(2, '0')}`;
}

export function anonimizar(
  linhas: LinhaBruta[],
  k: number,
  pseudo: (v: string) => string,
): { linhas: LinhaAnonima[]; gruposSuprimidos: number; linhasSuprimidas: number } {
  const grupos = new Map<string, Set<string>>();
  for (const l of linhas) {
    const g = `${l.escolaId}|${l.nivel ?? 'sem_nivel'}`;
    (grupos.get(g) ?? grupos.set(g, new Set()).get(g)!).add(l.alunoId);
  }
  const suprimidos = new Set([...grupos].filter(([, alunos]) => alunos.size < k).map(([g]) => g));
  const saida: LinhaAnonima[] = [];
  let linhasSuprimidas = 0;
  for (const l of linhas) {
    if (suprimidos.has(`${l.escolaId}|${l.nivel ?? 'sem_nivel'}`)) {
      linhasSuprimidas++;
      continue;
    }
    saida.push({
      student: pseudo(`aluno:${l.alunoId}`),
      school: pseudo(`escola:${l.escolaId}`),
      trackLevel: l.nivel ?? 'sem_nivel',
      competency: l.competencia,
      probability: Math.round(l.probabilidade * 100) / 100,
      uncertainty: l.incerteza === null ? null : Math.round(l.incerteza * 100) / 100,
      evidenceCount: l.evidencias,
      week: semanaIso(l.atualizadoEm),
      synthetic: l.sintetico,
    });
  }
  // Embaralha a ordem para não preservar a ordem de inserção (que poderia ligar linhas).
  saida.sort((a, b) => (a.student + a.competency).localeCompare(b.student + b.competency));
  return { linhas: saida, gruposSuprimidos: suprimidos.size, linhasSuprimidas };
}

const UUID = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;
const EMAIL = /[\w.+-]+@[\w-]+(\.[\w-]+)+/;

/** Procura PII no texto exportado: UUIDs, e-mails e valores sensíveis conhecidos (nomes, ids). */
export function procurarPII(texto: string, conhecidos: string[]): string[] {
  const achados: string[] = [];
  if (UUID.test(texto)) achados.push('uuid');
  if (EMAIL.test(texto)) achados.push('email');
  const baixo = texto.toLowerCase();
  for (const c of conhecidos) if (c.length >= 4 && baixo.includes(c.toLowerCase())) achados.push(`valor conhecido (${c.length} caracteres)`);
  return achados;
}
