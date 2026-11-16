import { type DynamicModule, Module } from '@nestjs/common';
import { APP_FILTER, APP_GUARD, APP_INTERCEPTOR } from '@nestjs/core';

import { EducationModule } from './modules/education/education.module';
import { IdentityModule } from './modules/identity/identity.module';
import { GuardCentral } from './shared/autorizacao/guard-central';
import type { Configuracao } from './shared/config/configuracao';
import { FiltroDeErros } from './shared/http/filtro-de-erros';
import { InterceptadorDeValidacao } from './shared/http/validacao';
import { InfraestruturaModule } from './shared/infraestrutura.module';
import { SaudeController } from './shared/saude/saude.controller';

/**
 * Monólito modular: quatro contextos (identity, education, assessment, orchestration)
 * sobre a infraestrutura compartilhada. Guard, validação e filtro de erros são globais.
 */
@Module({})
export class AppModule {
  static com(config: Configuracao): DynamicModule {
    return {
      module: AppModule,
      imports: [InfraestruturaModule.com(config), IdentityModule, EducationModule],
      controllers: [SaudeController],
      providers: [
        { provide: APP_GUARD, useClass: GuardCentral },
        { provide: APP_INTERCEPTOR, useClass: InterceptadorDeValidacao },
        FiltroDeErros,
        { provide: APP_FILTER, useExisting: FiltroDeErros },
      ],
    };
  }
}
