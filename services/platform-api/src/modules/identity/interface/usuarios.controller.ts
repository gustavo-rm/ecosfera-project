import { Body, Controller, Param } from '@nestjs/common';
import type { z } from 'zod';

import { Autorizacao } from '../../../shared/autorizacao/autorizacao.decorator';
import { Endpoint } from '../../../shared/http/contrato';
import { Consulta, UsuarioAtual } from '../../../shared/http/decoradores';
import type { AtorUsuario } from '../../../shared/kernel/ator';
import type { Papel } from '../../../shared/kernel/papeis';
import { ServicoDeAutenticacao } from '../application/autenticacao.service';
import { ServicoDeUsuarios } from '../application/usuarios.service';
import { ContratosUsuarios } from './contratos';
import type { EsquemaCorrecao, EsquemaMudancaDePapel, EsquemaMudancaDePreferencias, EsquemaNovoUsuario, EsquemaVinculoResponsavel } from './esquemas';
import { paraPerfil } from './esquemas';

@Controller()
export class UsuariosController {
  constructor(
    private readonly usuarios: ServicoDeUsuarios,
    private readonly auth: ServicoDeAutenticacao,
  ) {}

  @Endpoint(ContratosUsuarios.criar)
  @Autorizacao({ papeis: ['admin', 'teacher', 'platform_admin'] })
  async criar(@UsuarioAtual() ator: AtorUsuario, @Body() b: z.infer<typeof EsquemaNovoUsuario>) {
    return paraPerfil(await this.usuarios.criar(ator, b));
  }

  @Endpoint(ContratosUsuarios.listar)
  @Autorizacao({ papeis: ['admin', 'coordinator'] })
  async listar(@UsuarioAtual() ator: AtorUsuario, @Consulta() q: { page: number; pageSize: number; role?: Papel }) {
    const r = await this.usuarios.listar(ator, q.role, q.page, q.pageSize);
    return { items: r.itens.map(paraPerfil), page: q.page, pageSize: q.pageSize, total: r.total };
  }

  @Endpoint(ContratosUsuarios.alunosDoResponsavel)
  @Autorizacao({ papeis: ['guardian'] })
  async alunosDoResponsavel(@UsuarioAtual() ator: AtorUsuario) {
    const alunos = await this.usuarios.alunosDoResponsavel(ator);
    return { items: alunos.map((a) => ({ id: a.id, name: a.nome, schoolId: a.escolaId })) };
  }

  @Endpoint(ContratosUsuarios.obter)
  @Autorizacao({ papeis: ['student', 'teacher', 'coordinator', 'admin', 'guardian', 'platform_admin'], posse: { regra: 'usuario:ler' } })
  async obter(@UsuarioAtual() ator: AtorUsuario, @Param('id') id: string) {
    return paraPerfil(await this.usuarios.perfil(ator, id));
  }

  @Endpoint(ContratosUsuarios.corrigir)
  @Autorizacao({ papeis: ['admin', 'platform_admin'], posse: { regra: 'usuario:gerir' } })
  async corrigir(@UsuarioAtual() ator: AtorUsuario, @Param('id') id: string, @Body() b: z.infer<typeof EsquemaCorrecao>) {
    return paraPerfil(await this.usuarios.corrigir(ator, id, b));
  }

  @Endpoint(ContratosUsuarios.preferencias)
  @Autorizacao({ papeis: ['student', 'teacher', 'coordinator', 'admin', 'guardian', 'researcher', 'platform_admin'], posse: { regra: 'usuario:proprio' } })
  async preferencias(@UsuarioAtual() ator: AtorUsuario, @Param('id') id: string, @Body() b: z.infer<typeof EsquemaMudancaDePreferencias>) {
    return paraPerfil(await this.usuarios.atualizarPreferencias(ator, id, b));
  }

  @Endpoint(ContratosUsuarios.papel)
  @Autorizacao({ papeis: ['admin', 'platform_admin'], posse: { regra: 'usuario:gerir' } })
  async papel(@UsuarioAtual() ator: AtorUsuario, @Param('id') id: string, @Body() b: z.infer<typeof EsquemaMudancaDePapel>) {
    return paraPerfil(await this.usuarios.alterarPapel(ator, id, b.role));
  }

  @Endpoint(ContratosUsuarios.redefinicaoPeloAdmin)
  @Autorizacao({ papeis: ['admin', 'platform_admin'], posse: { regra: 'usuario:gerir' } })
  async redefinicao(@UsuarioAtual() ator: AtorUsuario, @Param('id') id: string) {
    await this.auth.iniciarRedefinicaoPeloAdmin(ator, id);
  }

  @Endpoint(ContratosUsuarios.vincularResponsavel)
  @Autorizacao({ papeis: ['admin'], posse: { regra: 'usuario:gerir' } })
  async vincular(@UsuarioAtual() ator: AtorUsuario, @Param('id') id: string, @Body() b: z.infer<typeof EsquemaVinculoResponsavel>) {
    await this.usuarios.vincularResponsavel(ator, id, b.guardianUserId);
  }
}
