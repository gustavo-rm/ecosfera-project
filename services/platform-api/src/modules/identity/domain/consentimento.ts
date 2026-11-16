import { ErroDeConflito } from '../../../shared/kernel/erros';
import type { Finalidade } from '../../../shared/kernel/finalidades';

export type EstadoDoConsentimento = 'pending' | 'granted' | 'revoked';

/**
 * Consentimento do responsável para uma finalidade (RF-008, RNF-009).
 * Sem consentimento válido, dado do menor não é coletado para aquela finalidade.
 */
export class Consentimento {
  constructor(
    readonly alunoId: string,
    readonly finalidade: Finalidade,
    public estado: EstadoDoConsentimento,
    public responsavelId: string | null,
    public versaoDoTexto: string | null,
    public concedidoEm: Date | null,
    public revogadoEm: Date | null,
    public revogadoPor: string | null,
  ) {}

  static pendente(alunoId: string, finalidade: Finalidade): Consentimento {
    return new Consentimento(alunoId, finalidade, 'pending', null, null, null, null, null);
  }

  valido(): boolean {
    return this.estado === 'granted';
  }

  conceder(responsavelId: string, versaoDoTexto: string, agora: Date): void {
    this.estado = 'granted';
    this.responsavelId = responsavelId;
    this.versaoDoTexto = versaoDoTexto;
    this.concedidoEm = agora;
    this.revogadoEm = null;
    this.revogadoPor = null;
  }

  revogar(por: string, agora: Date): void {
    if (this.estado !== 'granted') throw new ErroDeConflito(`Não há consentimento ativo para "${this.finalidade}"`);
    this.estado = 'revoked';
    this.revogadoEm = agora;
    this.revogadoPor = por;
  }
}

/** Regra central: maior de idade não depende de consentimento do responsável. */
export function permiteTratamento(menor: boolean, c: Consentimento | undefined): boolean {
  if (!menor) return true;
  return c?.valido() ?? false;
}
