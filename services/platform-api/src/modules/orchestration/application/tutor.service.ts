import { Inject, Injectable } from '@nestjs/common';

import type { AtorUsuario } from '../../../shared/kernel/ator';
import {
  ErroAcessoNegado,
  ErroConsentimentoAusente,
  ErroNaoEncontrado,
} from '../../../shared/kernel/erros';
import { ServicoDeEducacao } from '../../education/application/educacao.service';
import { ServicoDeConsentimento } from '../../identity/application/consentimento.service';
import {
  REPOSITORIO_DE_USUARIOS,
  type RepositorioDeUsuarios,
} from '../../identity/domain/portas';
import { redigirPII, sanitizarTextoDaIA } from '../domain/redacao';
import { TUTOR_GATEWAY, type TutorGateway } from '../domain/portas';
import { ServicoDePlanetas } from './planetas.service';

/** Proxy autorizado do tutor. Não há lógica de tutoria aqui (ADR 0012). */
@Injectable()
export class ServicoDeTutor {
  constructor(
    @Inject(TUTOR_GATEWAY) private readonly tutor: TutorGateway,
    @Inject(REPOSITORIO_DE_USUARIOS)
    private readonly usuarios: RepositorioDeUsuarios,
    private readonly planetas: ServicoDePlanetas,
    private readonly educacao: ServicoDeEducacao,
    private readonly consentimento: ServicoDeConsentimento,
  ) {}

  private async nomes(ator: AtorUsuario): Promise<string[]> {
    const u = await this.usuarios.porId(ator.usuarioId);
    return u ? [u.nome] : [];
  }

  async *explicar(
    ator: AtorUsuario,
    p: { planetId: string; contextRef: string; question?: string },
  ): AsyncIterable<string> {
    const m = await this.planetas.exigir(ator, p.planetId, 'agir');
    const pergunta = p.question
      ? redigirPII(p.question, await this.nomes(ator))
      : undefined;
    for await (const trecho of this.tutor.explicar(
      { ...p, question: pergunta },
      this.planetas.ctx(m),
    )) {
      yield sanitizarTextoDaIA(trecho);
    }
  }

  async dica(ator: AtorUsuario, p: { planetId: string; missionId: string }) {
    const m = await this.planetas.exigir(ator, p.planetId, 'agir');
    await this.educacao.exigirMissao(ator, p.missionId, 'ler');
    const r = await this.tutor.dica(p, this.planetas.ctx(m));
    return { hint: sanitizarTextoDaIA(r.hint), level: r.level };
  }

  async conselheiro(ator: AtorUsuario, p: { role: string; query: string }) {
    if (!(await this.consentimento.permite(ator.usuarioId, 'platform_use')))
      throw new ErroConsentimentoAusente('platform_use');
    const r = await this.tutor.conselheiro(
      { role: p.role, query: redigirPII(p.query, await this.nomes(ator)) },
      { alunoId: ator.usuarioId, escolaId: ator.escolaId },
    );
    return { advice: sanitizarTextoDaIA(r.advice) };
  }

  /** Parâmetros adaptativos: só a equipe da escola (a IA informa; o professor decide — RP-007). */
  async adaptacao(ator: AtorUsuario, alunoId: string) {
    const alvo = await this.usuarios.porId(alunoId);
    if (!alvo || alvo.escolaId !== ator.escolaId)
      throw new ErroNaoEncontrado('Aluno');
    if (ator.papel === 'student') throw new ErroAcessoNegado();
    if (!(await this.consentimento.permite(alunoId, 'learning_assessment')))
      throw new ErroConsentimentoAusente('learning_assessment');
    return this.tutor.adaptacao({ alunoId, escolaId: alvo.escolaId });
  }
}
