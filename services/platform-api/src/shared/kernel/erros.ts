/**
 * Erros de domínio e de aplicação. Não dependem de framework.
 * O filtro HTTP traduz cada um para RFC 7807 (ver shared/http/problemas.ts).
 * Mensagens nunca carregam PII.
 */
export type TipoDeProblema =
  | 'validation'
  | 'bad-request'
  | 'unauthenticated'
  | 'forbidden'
  | 'consent-required'
  | 'not-found'
  | 'conflict'
  | 'insufficient-action-points'
  | 'payload-too-large'
  | 'rate-limited'
  | 'dependency-unavailable'
  | 'dependency-timeout'
  | 'not-implemented'
  | 'internal';

export interface DetalheDeCampo {
  campo: string;
  mensagem: string;
}

export abstract class ErroDeAplicacao extends Error {
  abstract readonly tipo: TipoDeProblema;
  readonly extras: Record<string, unknown> = {};
  constructor(mensagem: string) {
    super(mensagem);
    this.name = new.target.name;
  }
}

export class ErroDeValidacao extends ErroDeAplicacao {
  readonly tipo = 'validation';
  constructor(
    mensagem: string,
    public readonly campos: DetalheDeCampo[] = [],
  ) {
    super(mensagem);
  }
}

export class ErroRequisicaoInvalida extends ErroDeAplicacao {
  readonly tipo = 'bad-request';
}

export class ErroNaoAutenticado extends ErroDeAplicacao {
  readonly tipo = 'unauthenticated';
  constructor(mensagem = 'Autenticação necessária ou inválida') {
    super(mensagem);
  }
}

export class ErroAcessoNegado extends ErroDeAplicacao {
  readonly tipo = 'forbidden';
  constructor(mensagem = 'Você não tem permissão para esta ação') {
    super(mensagem);
  }
}

export class ErroConsentimentoAusente extends ErroDeAplicacao {
  readonly tipo = 'consent-required';
  constructor(public readonly finalidade: string) {
    super(
      `Esta ação exige consentimento válido do responsável para a finalidade "${finalidade}". Peça ao responsável para registrar o consentimento.`,
    );
    this.extras.finalidade = finalidade;
  }
}

export class ErroNaoEncontrado extends ErroDeAplicacao {
  readonly tipo = 'not-found';
  constructor(recurso: string) {
    super(`${recurso} não encontrado(a)`);
  }
}

export class ErroDeConflito extends ErroDeAplicacao {
  readonly tipo = 'conflict';
}

export class ErroPontosDeAcaoInsuficientes extends ErroDeAplicacao {
  readonly tipo = 'insufficient-action-points';
  constructor(restantes: number, necessarios: number) {
    super(
      `Pontos de ação insuficientes: ${restantes} disponíveis, ${necessarios} necessários`,
    );
    this.extras.actionPoints = { remaining: restantes, required: necessarios };
  }
}

export class ErroCargaGrandeDemais extends ErroDeAplicacao {
  readonly tipo = 'payload-too-large';
}

export class ErroLimiteDeRequisicoes extends ErroDeAplicacao {
  readonly tipo = 'rate-limited';
  constructor(public readonly tentarDepoisSegundos: number) {
    super('Muitas tentativas. Aguarde antes de tentar de novo.');
    this.extras.retryAfterSeconds = tentarDepoisSegundos;
  }
}

export class ErroDeDependencia extends ErroDeAplicacao {
  readonly tipo: 'dependency-unavailable' | 'dependency-timeout';
  constructor(
    public readonly dependencia: string,
    porTempo = false,
  ) {
    super(
      porTempo
        ? `O serviço ${dependencia} não respondeu a tempo. Tente de novo em instantes.`
        : `O serviço ${dependencia} está indisponível no momento. Tente de novo em instantes.`,
    );
    this.tipo = porTempo ? 'dependency-timeout' : 'dependency-unavailable';
    this.extras.dependency = dependencia;
  }
}

export class ErroNaoImplementado extends ErroDeAplicacao {
  readonly tipo = 'not-implemented';
}
