/**
 * Finalidades de tratamento de dados de menor (LGPD art. 14).
 * O consentimento do responsável é registrado por finalidade.
 * Os textos legais de cada finalidade são placeholders versionados
 * (tabela platform.consent_text), pendentes de revisão do DPO/jurídico.
 */
export const FINALIDADES = [
  /** Usar a plataforma: conta, turma, planetas, missões, tutor. */
  'platform_use',
  /** Avaliação de aprendizagem: telemetria, evidências, perfil por competência. */
  'learning_assessment',
  /** Inclusão, anonimizada, em dataset de pesquisa. */
  'research',
] as const;
export type Finalidade = (typeof FINALIDADES)[number];
