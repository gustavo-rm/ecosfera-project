import { Body, Controller, Param } from '@nestjs/common';
import type { z } from 'zod';

import { Autorizacao } from '../../../shared/autorizacao/autorizacao.decorator';
import { Endpoint } from '../../../shared/http/contrato';
import { Consulta, UsuarioAtual } from '../../../shared/http/decoradores';
import type { AtorUsuario } from '../../../shared/kernel/ator';
import { paraPerfil } from '../../identity/interface/esquemas';
import type { Missao, Turma } from '../domain/educacao';
import { ServicoDeEducacao } from '../application/educacao.service';
import {
  ContratosEducacao as C,
  type EsquemaMatricula,
  type EsquemaNovaEscola,
  type EsquemaNovaHabilidade,
  type EsquemaNovaMissao,
  type EsquemaNovaTurma,
  type EsquemaPublicacao,
  type EsquemaRevisaoHabilidade,
  type EsquemaTrilhaDaTurma,
} from './contratos';

const paraTurma = (t: Turma) => ({ id: t.id, schoolId: t.escolaId, teacherUserId: t.professorId, name: t.nome, year: t.ano, trackLevel: t.nivel });
const paraMissao = (m: Missao) => ({
  id: m.id,
  schoolId: m.escolaId,
  authorUserId: m.autorId,
  title: m.titulo,
  description: m.descricao,
  objective: m.objetivo,
  trackLevel: m.nivel,
  bnccCodes: m.habilidades,
  parameters: m.parametros,
  status: m.situacao,
  classIds: m.turmas,
});

const EQUIPE = ['teacher', 'coordinator', 'admin'] as const;

@Controller()
export class EducacaoController {
  constructor(private readonly edu: ServicoDeEducacao) {}

  @Endpoint(C.criarEscola)
  @Autorizacao({ papeis: ['platform_admin'] })
  async criarEscola(@UsuarioAtual() ator: AtorUsuario, @Body() b: z.infer<typeof EsquemaNovaEscola>) {
    const r = await this.edu.criarEscola(ator, b.name, b.admin);
    return { school: { id: r.escola.id, name: r.escola.nome }, admin: paraPerfil(r.admin) };
  }

  @Endpoint(C.escola)
  @Autorizacao({ papeis: ['admin', 'coordinator', 'teacher', 'platform_admin'] })
  async escola(@UsuarioAtual() ator: AtorUsuario, @Param('id') id: string) {
    const e = await this.edu.escola(ator, id);
    return { id: e.id, name: e.nome };
  }

  @Endpoint(C.criarTurma)
  @Autorizacao({ papeis: EQUIPE })
  async criarTurma(@UsuarioAtual() ator: AtorUsuario, @Body() b: z.infer<typeof EsquemaNovaTurma>) {
    return paraTurma(await this.edu.criarTurma(ator, b));
  }

  @Endpoint(C.turmas)
  @Autorizacao({ papeis: ['student', ...EQUIPE] })
  async turmas(@UsuarioAtual() ator: AtorUsuario) {
    return { items: (await this.edu.turmas(ator)).map(paraTurma) };
  }

  @Endpoint(C.turma)
  @Autorizacao({ papeis: ['student', ...EQUIPE], posse: { regra: 'turma:ler' } })
  async turma(@UsuarioAtual() ator: AtorUsuario, @Param('id') id: string) {
    return paraTurma(await this.edu.exigirTurma(ator, id, 'ler'));
  }

  @Endpoint(C.matricular)
  @Autorizacao({ papeis: EQUIPE, posse: { regra: 'turma:gerir' } })
  async matricular(@UsuarioAtual() ator: AtorUsuario, @Param('id') id: string, @Body() b: z.infer<typeof EsquemaMatricula>) {
    const r = await this.edu.matricular(ator, id, b.studentIds);
    return { enrolled: r.novos, alreadyEnrolled: r.jaMatriculados };
  }

  @Endpoint(C.alunos)
  @Autorizacao({ papeis: EQUIPE, posse: { regra: 'turma:gerir' } })
  async alunos(@UsuarioAtual() ator: AtorUsuario, @Param('id') id: string) {
    return { items: (await this.edu.alunos(ator, id)).map((a) => ({ id: a.id, name: a.nome, isMinor: a.menor })) };
  }

  @Endpoint(C.desmatricular)
  @Autorizacao({ papeis: EQUIPE, posse: { regra: 'turma:gerir' } })
  async desmatricular(@UsuarioAtual() ator: AtorUsuario, @Param('id') id: string, @Param('studentId') alunoId: string) {
    await this.edu.desmatricular(ator, id, alunoId);
  }

  @Endpoint(C.trilha)
  @Autorizacao({ papeis: EQUIPE, posse: { regra: 'turma:gerir' } })
  async trilha(@UsuarioAtual() ator: AtorUsuario, @Param('id') id: string, @Body() b: z.infer<typeof EsquemaTrilhaDaTurma>) {
    return paraTurma(await this.edu.definirTrilha(ator, id, b.level));
  }

  @Endpoint(C.trilhas)
  @Autorizacao({ papeis: ['student', ...EQUIPE] })
  trilhas() {
    return {
      items: [
        { level: 'fundamental_ii' as const, name: 'Fundamental II' },
        { level: 'medio' as const, name: 'Ensino Médio' },
        { level: 'tecnico' as const, name: 'Técnico' },
      ],
    };
  }

  @Endpoint(C.criarMissao)
  @Autorizacao({ papeis: EQUIPE })
  async criarMissao(@UsuarioAtual() ator: AtorUsuario, @Body() b: z.infer<typeof EsquemaNovaMissao>) {
    return paraMissao(await this.edu.criarMissao(ator, b));
  }

  @Endpoint(C.missoes)
  @Autorizacao({ papeis: ['student', ...EQUIPE], posse: { regra: 'turma:ler', parametro: 'classId', origem: 'query' } })
  async missoes(@UsuarioAtual() ator: AtorUsuario, @Consulta() q: { classId: string }) {
    return { items: (await this.edu.missoesDaTurma(ator, q.classId)).map(paraMissao) };
  }

  @Endpoint(C.missao)
  @Autorizacao({ papeis: ['student', ...EQUIPE], posse: { regra: 'missao:ler' } })
  async missao(@UsuarioAtual() ator: AtorUsuario, @Param('id') id: string) {
    return paraMissao(await this.edu.exigirMissao(ator, id, 'ler'));
  }

  @Endpoint(C.publicar)
  @Autorizacao({ papeis: EQUIPE, posse: { regra: 'missao:gerir' } })
  async publicar(@UsuarioAtual() ator: AtorUsuario, @Param('id') id: string, @Body() b: z.infer<typeof EsquemaPublicacao>) {
    return paraMissao(await this.edu.publicar(ator, id, b.classIds));
  }

  @Endpoint(C.competencias)
  @Autorizacao({ papeis: [...EQUIPE, 'researcher', 'platform_admin'] })
  async competencias() {
    return { items: await this.edu.competencias() };
  }

  @Endpoint(C.habilidades)
  @Autorizacao({ papeis: [...EQUIPE, 'researcher', 'platform_admin'] })
  async habilidades(@Consulta() q: { stage?: string; competency?: string }) {
    return { items: await this.edu.habilidades({ stage: q.stage, competencyCode: q.competency }) };
  }

  @Endpoint(C.criarHabilidade)
  @Autorizacao({ papeis: ['platform_admin'] })
  async criarHabilidade(@UsuarioAtual() ator: AtorUsuario, @Body() b: z.infer<typeof EsquemaNovaHabilidade>) {
    return this.edu.revisarHabilidade(ator, b.code, b, true);
  }

  @Endpoint(C.revisarHabilidade)
  @Autorizacao({ papeis: ['platform_admin'] })
  async revisarHabilidade(@UsuarioAtual() ator: AtorUsuario, @Param('code') code: string, @Body() b: z.infer<typeof EsquemaRevisaoHabilidade>) {
    return this.edu.revisarHabilidade(ator, code, b, false);
  }
}
