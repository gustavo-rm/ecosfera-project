import { Inject, Module, type OnModuleInit } from '@nestjs/common';
import { DataSource } from 'typeorm';

import { RegistroDeRegrasDePosse } from '../../shared/autorizacao/registro-de-posse';
import { IdentityModule } from '../identity/identity.module';
import { ServicoDeEducacao } from './application/educacao.service';
import { decidirAcessoAMissao, decidirAcessoATurma } from './domain/educacao';
import { REPOSITORIO_DE_EDUCACAO, type RepositorioDeEducacao } from './domain/portas';
import { RepositorioDeEducacaoTypeorm } from './infrastructure/repositorio-de-educacao';
import { EducacaoController } from './interface/educacao.controller';

/** Contexto education: escolas, turmas, trilhas, missões e currículo BNCC. */
@Module({
  imports: [IdentityModule],
  controllers: [EducacaoController],
  providers: [
    { provide: REPOSITORIO_DE_EDUCACAO, inject: [DataSource], useFactory: (ds: DataSource) => new RepositorioDeEducacaoTypeorm(ds) },
    ServicoDeEducacao,
  ],
  exports: [ServicoDeEducacao, REPOSITORIO_DE_EDUCACAO],
})
export class EducationModule implements OnModuleInit {
  constructor(
    private readonly registro: RegistroDeRegrasDePosse,
    @Inject(REPOSITORIO_DE_EDUCACAO) private readonly repo: RepositorioDeEducacao,
  ) {}

  onModuleInit(): void {
    for (const intencao of ['ler', 'gerir'] as const) {
      this.registro.registrar(`turma:${intencao}`, async (ator, id) =>
        decidirAcessoATurma(ator, await this.repo.fatosDaTurma(id, ator.papel === 'student' ? ator.usuarioId : undefined), intencao),
      );
      this.registro.registrar(`missao:${intencao}`, async (ator, id) =>
        decidirAcessoAMissao(ator, await this.repo.fatosDaMissao(id, { id: ator.usuarioId, papel: ator.papel }), intencao),
      );
    }
  }
}
