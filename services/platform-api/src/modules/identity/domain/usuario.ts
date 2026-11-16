import { ErroDeValidacao } from '../../../shared/kernel/erros';
import type { Papel } from '../../../shared/kernel/papeis';

export type SituacaoDaConta = 'active' | 'disabled' | 'pseudonymized';

export const IDIOMAS = ['pt-BR', 'en', 'es'] as const;
export type Idioma = (typeof IDIOMAS)[number];

/** VO Preferências (RF-010): idioma e acessibilidade. */
export interface Preferencias {
  language: Idioma;
  accessibility: {
    highContrast: boolean;
    fontScale: number;
    reducedMotion: boolean;
    screenReader: boolean;
    captions: boolean;
    colorBlindMode: 'none' | 'protanopia' | 'deuteranopia' | 'tritanopia';
  };
}

export const PREFERENCIAS_PADRAO: Preferencias = {
  language: 'pt-BR',
  accessibility: {
    highContrast: false,
    fontScale: 1,
    reducedMotion: false,
    screenReader: false,
    captions: false,
    colorBlindMode: 'none',
  },
};

export interface MudancaDePreferencias {
  language?: Idioma;
  accessibility?: Partial<Preferencias['accessibility']>;
}

export function mesclarPreferencias(
  atual: MudancaDePreferencias | undefined,
  mudanca: MudancaDePreferencias,
): Preferencias {
  const base = { ...PREFERENCIAS_PADRAO, ...(atual ?? {}) };
  return {
    language: mudanca.language ?? base.language,
    accessibility: {
      ...PREFERENCIAS_PADRAO.accessibility,
      ...base.accessibility,
      ...(mudanca.accessibility ?? {}),
    },
  };
}

/** Normaliza e-mail para comparação e unicidade (minúsculas, sem espaços). */
export function normalizarEmail(email: string): string {
  return email.trim().toLowerCase();
}

/** Agregado Usuário. Sem dependência de framework. */
export class Usuario {
  constructor(
    readonly id: string,
    public escolaId: string | null,
    public nome: string,
    public email: string,
    public papel: Papel,
    public menor: boolean,
    public situacao: SituacaoDaConta,
    public preferencias: Preferencias,
    public senhaHash: string,
  ) {}

  podeAutenticar(): boolean {
    return this.situacao === 'active';
  }

  alterarPapel(novo: Papel): void {
    if (this.situacao !== 'active')
      throw new ErroDeValidacao('Conta inativa não pode mudar de papel');
    this.papel = novo;
    if (novo !== 'student') this.menor = false;
  }

  /** Pseudonimização (direito de exclusão): o registro fica para manter a auditoria íntegra, sem PII. */
  pseudonimizar(pseudonimo: string): void {
    this.nome = '[removido]';
    this.email = `removido+${pseudonimo}@invalid.ecosfera`;
    this.senhaHash = '!';
    this.situacao = 'pseudonymized';
    this.preferencias = PREFERENCIAS_PADRAO;
  }
}
