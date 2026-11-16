/**
 * Convenção única de chaves Redis do platform-api (documentada em docs/backend/README.md).
 * Todas com prefixo configurável (REDIS_KEY_PREFIX, padrão `ecosfera:platform:`).
 */
export class ChavesRedis {
  constructor(readonly prefixo: string) {}
  /** Sessão (família de refresh tokens). TTL = vida do refresh. */
  sessao(id: string) {
    return `${this.prefixo}session:${id}`;
  }
  /** Conjunto das sessões de um usuário (revogar tudo). */
  sessoesDoUsuario(usuarioId: string) {
    return `${this.prefixo}user_sessions:${usuarioId}`;
  }
  /** Token de redefinição de senha (hash). TTL 30 min. */
  redefinicaoDeSenha(hash: string) {
    return `${this.prefixo}pwreset:${hash}`;
  }
  limite(nome: string, chave: string) {
    return `${this.prefixo}ratelimit:${nome}:${chave}`;
  }
  /** Cache curto do estado de consentimento (invalidado ao conceder/revogar). */
  consentimento(usuarioId: string) {
    return `${this.prefixo}consent:${usuarioId}`;
  }
  /** Estado/nonce de login federado (OIDC/LTI). TTL 10 min. */
  estadoFederado(estado: string) {
    return `${this.prefixo}fed_state:${estado}`;
  }
  nonceUsado(nonce: string) {
    return `${this.prefixo}fed_nonce:${nonce}`;
  }
  /** Canal pub/sub do stream do planeta (fan-out entre réplicas). */
  canalDoPlaneta(planetaId: string) {
    return `${this.prefixo}planet:${planetaId}:stream`;
  }
  /** Canal de aviso de revogação de consentimento (fecha WebSockets do aluno em todas as réplicas). */
  canalDeRevogacao() {
    return `${this.prefixo}consent:revoked`;
  }
  /** Últimas mensagens do planeta, para reconexão (lista limitada). */
  replayDoPlaneta(planetaId: string) {
    return `${this.prefixo}planet:${planetaId}:replay`;
  }
  /** Trava curta de idempotência (pedido em andamento). */
  idempotenciaEmAndamento(escopo: string, chave: string) {
    return `${this.prefixo}idem_lock:${escopo}:${chave}`;
  }
  /** Estado do adaptador FALSO de simulação (só dev/teste). */
  simulacaoFalsa(planetaId: string) {
    return `${this.prefixo}fake_sim:${planetaId}`;
  }
  /** Pontos de ação — no fake; o dono real da regra é o ai-sim-service (ADR 0012). */
  pontosDeAcao(planetaId: string) {
    return `${this.prefixo}action_points:${planetaId}`;
  }
}
