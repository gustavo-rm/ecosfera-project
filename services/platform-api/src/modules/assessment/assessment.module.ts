import { Module } from '@nestjs/common';
import { DataSource } from 'typeorm';

import { EducationModule } from '../education/education.module';
import { IdentityModule } from '../identity/identity.module';
import { OrchestrationModule } from '../orchestration/orchestration.module';
import { ServicoDeExportacao } from './application/exportacao.service';
import { ServicoLgpd } from './application/lgpd.service';
import { ServicoDePainel } from './application/painel.service';
import { ProjecaoDeAvaliacao } from './application/projecao.service';
import { ConsultasDeAvaliacao } from './infrastructure/consultas';
import { ArquivosController } from './interface/arquivos.controller';
import { AvaliacaoController } from './interface/avaliacao.controller';

/** Contexto assessment: modelo de LEITURA da avaliação, painel, exportações e LGPD do dado pedagógico. */
@Module({
  imports: [IdentityModule, EducationModule, OrchestrationModule],
  controllers: [AvaliacaoController, ArquivosController],
  providers: [
    { provide: ConsultasDeAvaliacao, inject: [DataSource], useFactory: (ds: DataSource) => new ConsultasDeAvaliacao(ds) },
    ProjecaoDeAvaliacao,
    ServicoDePainel,
    ServicoDeExportacao,
    ServicoLgpd,
  ],
  exports: [ProjecaoDeAvaliacao, ServicoLgpd],
})
export class AssessmentModule {}
