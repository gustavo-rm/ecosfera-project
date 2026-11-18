import type { AtorUsuario } from '../kernel/ator';
import type { FatosDoAlvo } from '../kernel/politica-de-acesso';
import type { VinculosEscolares } from '../kernel/vinculos';

/** Carrega os fatos necessários à política de acesso a um usuário-alvo. */
export async function carregarFatosDoAlvo(
  v: VinculosEscolares,
  ator: AtorUsuario,
  alvoId: string,
): Promise<FatosDoAlvo> {
  const alvo = await v.escolaDoUsuario(alvoId);
  if (!alvo.existe) {
    return {
      existe: false,
      alvoId,
      escolaId: null,
      lecionaParaAlvo: false,
      responsavelPeloAlvo: false,
    };
  }
  const [leciona, responsavel] = await Promise.all([
    ator.papel === 'teacher'
      ? v.professorLecionaParaAluno(ator.usuarioId, alvoId)
      : Promise.resolve(false),
    ator.papel === 'guardian'
      ? v.responsavelPeloAluno(ator.usuarioId, alvoId)
      : Promise.resolve(false),
  ]);
  return {
    existe: true,
    alvoId,
    escolaId: alvo.escolaId,
    lecionaParaAlvo: leciona,
    responsavelPeloAlvo: responsavel,
  };
}
