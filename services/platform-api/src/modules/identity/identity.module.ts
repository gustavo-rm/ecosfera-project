import { Inject, Module, type OnModuleInit } from '@nestjs/common';
import type { Redis } from 'ioredis';
import type { Logger } from 'pino';
import { DataSource } from 'typeorm';

import { RegistroDeRegrasDePosse } from '../../shared/autorizacao/registro-de-posse';
import { GATE_DE_CONSENTIMENTO, VERIFICADOR_DE_CREDENCIAIS } from '../../shared/autorizacao/portas';
import { carregarFatosDoAlvo } from '../../shared/autorizacao/fatos';
import { CONFIGURACAO, type Configuracao } from '../../shared/config/configuracao';
import { decidirAcessoAoUsuario } from '../../shared/kernel/politica-de-acesso';
import { RELOGIO, type Relogio } from '../../shared/kernel/relogio';
import { VINCULOS_ESCOLARES, type VinculosEscolares } from '../../shared/kernel/vinculos';
import { LOGGER } from '../../shared/observabilidade/logger';
import { ChavesRedis } from '../../shared/redis/chaves';
import { REDIS } from '../../shared/redis/redis';
import { ServicoDeAutenticacao } from './application/autenticacao.service';
import { ServicoDeConsentimento } from './application/consentimento.service';
import { ServicoDeUsuarios } from './application/usuarios.service';
import { ARMAZEM_DE_SESSOES, type ArmazemDeSessoes, HASHER_DE_SENHA, MAILER, REPOSITORIO_DE_USUARIOS } from './domain/portas';
import { HasherArgon2 } from './infrastructure/hasher-argon2';
import { MailerDesligado, MailerFalso } from './infrastructure/mailers';
import { RepositorioDeUsuariosTypeorm } from './infrastructure/repositorio-de-usuarios';
import { SessoesRedis } from './infrastructure/sessoes-redis';
import { ServicoDeTokens } from './infrastructure/tokens';
import { AuthController } from './interface/auth.controller';
import { ConsentimentoController } from './interface/consentimento.controller';
import { UsuariosController } from './interface/usuarios.controller';

/** Contexto identity: IAM, RBAC, usuários, consentimento, LGPD, federação. */
@Module({
  controllers: [AuthController, UsuariosController, ConsentimentoController],
  providers: [
    { provide: HASHER_DE_SENHA, useClass: HasherArgon2 },
    { provide: REPOSITORIO_DE_USUARIOS, inject: [DataSource], useFactory: (ds: DataSource) => new RepositorioDeUsuariosTypeorm(ds) },
    { provide: ARMAZEM_DE_SESSOES, inject: [REDIS, ChavesRedis], useFactory: (r: Redis, c: ChavesRedis) => new SessoesRedis(r, c) },
    {
      provide: ServicoDeTokens,
      inject: [CONFIGURACAO, ARMAZEM_DE_SESSOES, RELOGIO],
      useFactory: (c: Configuracao, s: ArmazemDeSessoes, r: Relogio) => new ServicoDeTokens(c, s, r),
    },
    { provide: VERIFICADOR_DE_CREDENCIAIS, useExisting: ServicoDeTokens },
    {
      provide: MAILER,
      inject: [CONFIGURACAO, LOGGER],
      useFactory: (c: Configuracao, l: Logger) =>
        c.ADAPTER_MAILER === 'fake' ? new MailerFalso(l, c.NODE_ENV !== 'production') : new MailerDesligado(),
    },
    ServicoDeAutenticacao,
    ServicoDeUsuarios,
    ServicoDeConsentimento,
    { provide: GATE_DE_CONSENTIMENTO, useExisting: ServicoDeConsentimento },
  ],
  exports: [
    VERIFICADOR_DE_CREDENCIAIS,
    GATE_DE_CONSENTIMENTO,
    ServicoDeTokens,
    ServicoDeAutenticacao,
    ServicoDeUsuarios,
    ServicoDeConsentimento,
    REPOSITORIO_DE_USUARIOS,
    HASHER_DE_SENHA,
    MAILER,
  ],
})
export class IdentityModule implements OnModuleInit {
  constructor(
    private readonly registro: RegistroDeRegrasDePosse,
    @Inject(VINCULOS_ESCOLARES) private readonly vinculos: VinculosEscolares,
  ) {}

  onModuleInit(): void {
    const regra = (intencao: 'ler' | 'gerir' | 'ler-pedagogico') => async (ator: Parameters<typeof decidirAcessoAoUsuario>[0], id: string) =>
      decidirAcessoAoUsuario(ator, await carregarFatosDoAlvo(this.vinculos, ator, id), intencao);
    this.registro.registrar('usuario:ler', regra('ler'));
    this.registro.registrar('usuario:gerir', regra('gerir'));
    this.registro.registrar('usuario:pedagogico', regra('ler-pedagogico'));
    this.registro.registrar('usuario:proprio', (ator, id) => Promise.resolve(ator.usuarioId === id ? 'permitido' : 'negado'));
  }
}
