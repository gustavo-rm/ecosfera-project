/**
 * Alertas de dificuldade (RF-077). A IA informa, o professor decide (RP-007):
 * o alerta é um aviso com origem rastreável, nunca uma ação automática sobre o aluno.
 * Limiares são PLACEHOLDER pedagógico (alert_config.review_status = pending_pedagogical_review).
 */
export interface ConfiguracaoDeAlerta {
  limiarDeDominio: number;
  incertezaMaxima: number;
  minimoDeEvidencias: number;
  diasDeInatividade: number;
  situacaoDaRevisao: string;
}

export const CONFIGURACAO_PADRAO: ConfiguracaoDeAlerta = {
  limiarDeDominio: 0.4,
  incertezaMaxima: 0.35,
  minimoDeEvidencias: 3,
  diasDeInatividade: 14,
  situacaoDaRevisao: 'pending_pedagogical_review',
};

export interface EstimativaParaAlerta {
  alunoId: string;
  competencia: string;
  probabilidade: number;
  incerteza: number | null;
  evidencias: number;
}

export interface Alerta {
  studentId: string;
  kind: 'low_mastery' | 'inactivity';
  competencyCode: string | null;
  probability: number | null;
  uncertainty: number | null;
  evidenceCount: number;
  reason: string;
}

export function calcularAlertas(
  estimativas: EstimativaParaAlerta[],
  ultimaAtividade: Map<string, Date | null>,
  c: ConfiguracaoDeAlerta,
  agora: Date,
): Alerta[] {
  const alertas: Alerta[] = [];
  for (const e of estimativas) {
    const confiavel = e.incerteza === null || e.incerteza <= c.incertezaMaxima;
    if (e.probabilidade < c.limiarDeDominio && confiavel && e.evidencias >= c.minimoDeEvidencias) {
      alertas.push({
        studentId: e.alunoId,
        kind: 'low_mastery',
        competencyCode: e.competencia,
        probability: e.probabilidade,
        uncertainty: e.incerteza,
        evidenceCount: e.evidencias,
        reason: `Domínio estimado abaixo de ${c.limiarDeDominio} com ${e.evidencias} evidências`,
      });
    }
  }
  const limite = agora.getTime() - c.diasDeInatividade * 86_400_000;
  for (const [aluno, quando] of ultimaAtividade) {
    if (!quando || quando.getTime() < limite) {
      alertas.push({
        studentId: aluno,
        kind: 'inactivity',
        competencyCode: null,
        probability: null,
        uncertainty: null,
        evidenceCount: 0,
        reason: quando ? `Sem atividade há mais de ${c.diasDeInatividade} dias` : 'Ainda sem atividade registrada',
      });
    }
  }
  return alertas;
}
