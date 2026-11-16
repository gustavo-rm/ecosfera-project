/**
 * Seed de DESENVOLVIMENTO: escola, um usuário de cada papel, turma, missão BNCC e vínculo responsável.
 * Determinístico nos dados (nomes, e-mails, turma), mas as SENHAS são geradas a cada execução e
 * gravadas só em `.credenciais-dev.json` (ignorado pelo git). Nada de senha fixa no repositório.
 * Recusa rodar com NODE_ENV=production.
 */
import 'reflect-metadata';
import 'dotenv/config';

import { randomBytes } from 'node:crypto';
import { writeFileSync } from 'node:fs';
import { join } from 'node:path';

import { NestFactory } from '@nestjs/core';
import { DataSource } from 'typeorm';

import { AppModule } from '../src/app.module';
import { ServicoDeEducacao } from '../src/modules/education/application/educacao.service';
import { ServicoDeUsuarios } from '../src/modules/identity/application/usuarios.service';
import { carregarConfiguracao } from '../src/shared/config/configuracao';
import type { AtorUsuario } from '../src/shared/kernel/ator';
import type { Papel } from '../src/shared/kernel/papeis';

async function principal(): Promise<void> {
  const config = carregarConfiguracao({ ...process.env, EVENTS_CONSUMER_ENABLED: 'false', OUTBOX_RELAY_ENABLED: 'false' });
  if (config.NODE_ENV === 'production') throw new Error('seed de desenvolvimento não roda em produção');
  const app = await NestFactory.createApplicationContext(AppModule.com(config), { logger: false });
  const ds = app.get(DataSource);
  const usuarios = app.get(ServicoDeUsuarios);
  const edu = app.get(ServicoDeEducacao);
  const senha = () => `Dev-${randomBytes(9).toString('base64url')}-1`;
  const credenciais: Record<string, { email: string; senha: string; id: string }> = {};

  const existente: { id: string }[] = await ds.query(`SELECT id FROM platform.school WHERE name = 'Escola Demonstração ECOSFERA'`);
  if (existente.length > 0) {
    console.log('Seed já aplicado (escola de demonstração existe). Para recriar, use um banco limpo.');
    await app.close();
    return;
  }
  const escola: { id: string }[] = await ds.query(`INSERT INTO platform.school (name) VALUES ('Escola Demonstração ECOSFERA') RETURNING id`);
  const escolaId = escola[0]!.id;
  const criar = async (chave: string, papel: Papel, nome: string, escolaDoUsuario: string | null, menor?: boolean) => {
    const s = senha();
    const email = `${chave}@demo.ecosfera.local`;
    const u = await usuarios.criar(null, { name: nome, email, role: papel, schoolId: escolaDoUsuario, isMinor: menor, password: s });
    credenciais[chave] = { email, senha: s, id: u.id };
    return u;
  };
  await criar('operador', 'platform_admin', 'Operador da Plataforma', null);
  await criar('admin', 'admin', 'Carlos (TI)', escolaId);
  const prof = await criar('professora', 'teacher', 'Marina', escolaId);
  await criar('professor.matematica', 'teacher', 'Rafael', escolaId);
  await criar('coordenadora', 'coordinator', 'Beatriz', escolaId);
  const lucas = await criar('aluno.lucas', 'student', 'Lucas', escolaId, true);
  const sofia = await criar('aluna.sofia', 'student', 'Sofia', escolaId, true);
  const helena = await criar('responsavel.helena', 'guardian', 'Helena', null);
  await criar('pesquisador', 'researcher', 'Pesquisador', null);
  await ds.query(`INSERT INTO platform.guardian (guardian_user_id, student_user_id) VALUES ($1, $2)`, [helena.id, lucas.id]);

  const atorProf: AtorUsuario = { tipo: 'usuario', usuarioId: prof.id, papel: 'teacher', escolaId, menor: false, sessaoId: 'seed' };
  const turma = await edu.criarTurma(atorProf, { name: '7º ano A', year: 7, trackLevel: 'fundamental_ii' });
  await edu.matricular(atorProf, turma.id, [lucas.id, sofia.id]);
  const missao = await edu.criarMissao(atorProf, {
    title: 'Efeito estufa no seu planeta',
    objective: 'Relacionar a concentração de CO2 com a temperatura média do planeta',
    trackLevel: 'fundamental_ii',
    bnccCodes: ['EF07CI13', 'EF07CI12'],
    parameters: { co2Inicial: 280 },
    classIds: [turma.id],
  });

  const arquivo = join(__dirname, '..', '.credenciais-dev.json');
  writeFileSync(arquivo, JSON.stringify({ geradoEm: new Date().toISOString(), escolaId, turmaId: turma.id, missaoId: missao.id, usuarios: credenciais }, null, 2), { mode: 0o600 });
  console.log(`Seed aplicado. Credenciais locais em ${arquivo} (não versionado).`);
  console.log('Lucas é menor sem consentimento: entre como a responsável Helena para consentir.');
  await app.close();
}

principal().catch((e: unknown) => {
  console.error(e);
  process.exit(1);
});
