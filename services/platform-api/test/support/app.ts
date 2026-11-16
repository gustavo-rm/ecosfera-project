import { randomBytes } from 'node:crypto';

import type { INestApplication } from '@nestjs/common';
import { Test } from '@nestjs/testing';
import request from 'supertest';
import { DataSource } from 'typeorm';

import { AppModule } from '../../src/app.module';
import { configurarAplicacao } from '../../src/configurar-aplicacao';
import { ServicoDeUsuarios } from '../../src/modules/identity/application/usuarios.service';
import { carregarConfiguracao, type Configuracao } from '../../src/shared/config/configuracao';
import { PREFIXO_API } from '../../src/shared/http/contrato';
import type { Papel } from '../../src/shared/kernel/papeis';

export const API = `/${PREFIXO_API}`;
export const SENHA_PADRAO = 'Planeta-azul-2026';

export interface AppDeTeste {
  app: INestApplication;
  config: Configuracao;
  ds: DataSource;
  http: () => ReturnType<typeof request>;
  fechar: () => Promise<void>;
}

/** Sobe a aplicação completa (mesma configuração do main.ts) contra os contêineres de teste. */
export async function criarApp(sobrescritas: Record<string, string> = {}): Promise<AppDeTeste> {
  const config = carregarConfiguracao({ ...process.env, ...sobrescritas });
  const mod = await Test.createTestingModule({ imports: [AppModule.com(config)] }).compile();
  const app = mod.createNestApplication({ bodyParser: false, logger: false });
  configurarAplicacao(app, config);
  await app.init();
  const servidor = app.getHttpServer() as Parameters<typeof request>[0];
  return {
    app,
    config,
    ds: app.get(DataSource),
    http: () => request(servidor),
    fechar: () => app.close(),
  };
}

export function sufixo(): string {
  return randomBytes(4).toString('hex');
}

export async function criarEscola(t: AppDeTeste, nome = `Escola ${sufixo()}`): Promise<string> {
  const r: { id: string }[] = await t.ds.query(`INSERT INTO platform.school (name) VALUES ($1) RETURNING id`, [nome]);
  return r[0]!.id;
}

export interface UsuarioDeTeste {
  id: string;
  email: string;
  senha: string;
  papel: Papel;
  escolaId: string | null;
  token: string;
  refresh: string;
}

/** Cria usuário pelo caso de uso real (ator de bootstrap) e faz login. */
export async function criarUsuario(
  t: AppDeTeste,
  papel: Papel,
  escolaId: string | null,
  extra: { isMinor?: boolean; nome?: string } = {},
): Promise<UsuarioDeTeste> {
  const email = `${papel}.${sufixo()}@teste.ecosfera.local`;
  const u = await t.app.get(ServicoDeUsuarios).criar(null, {
    name: extra.nome ?? `Usuário ${papel}`,
    email,
    role: papel,
    schoolId: escolaId,
    isMinor: extra.isMinor,
    password: SENHA_PADRAO,
  });
  const { token, refresh } = await login(t, email, SENHA_PADRAO);
  return { id: u.id, email, senha: SENHA_PADRAO, papel, escolaId, token, refresh };
}

export async function login(t: AppDeTeste, email: string, senha: string): Promise<{ token: string; refresh: string }> {
  const r = await t
    .http()
    .post(`${API}/auth/login`)
    .set('X-Refresh-Transport', 'body')
    .send({ email, senha });
  if (r.status !== 200) throw new Error(`login falhou: ${r.status} ${JSON.stringify(r.body)}`);
  const corpo = r.body as { accessToken: string; refreshToken: string };
  return { token: corpo.accessToken, refresh: corpo.refreshToken };
}

export function bearer(u: { token: string }): [string, string] {
  return ['Authorization', `Bearer ${u.token}`];
}
