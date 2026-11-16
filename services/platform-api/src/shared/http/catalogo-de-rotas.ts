import { METHOD_METADATA, PATH_METADATA } from '@nestjs/common/constants';
import type { Type } from '@nestjs/common';

import { ArquivosController } from '../../modules/assessment/interface/arquivos.controller';
import { AvaliacaoController } from '../../modules/assessment/interface/avaliacao.controller';
import { EducacaoController } from '../../modules/education/interface/educacao.controller';
import { AuthController } from '../../modules/identity/interface/auth.controller';
import { ConsentimentoController } from '../../modules/identity/interface/consentimento.controller';
import { FederacaoController } from '../../modules/identity/interface/federacao.controller';
import { UsuariosController } from '../../modules/identity/interface/usuarios.controller';
import { IaController } from '../../modules/orchestration/interface/ia.controller';
import { PlanetasController } from '../../modules/orchestration/interface/planetas.controller';
import {
  type DeclaracaoDeAutorizacao,
  META_AUTORIZACAO,
} from '../autorizacao/autorizacao.decorator';
import { SaudeController } from '../saude/saude.controller';
import { type DefinicaoDeEndpoint, META_CONTRATO } from './contrato';

/** Todos os controladores HTTP. O teste de arquitetura confere que a lista bate com o app. */
export const CONTROLADORES: Type[] = [
  SaudeController,
  AuthController,
  UsuariosController,
  ConsentimentoController,
  FederacaoController,
  EducacaoController,
  PlanetasController,
  IaController,
  AvaliacaoController,
  ArquivosController,
];

export interface RotaDeclarada {
  controlador: string;
  metodoDaClasse: string;
  caminhoNest: string | undefined;
  verboNest: number | undefined;
  contrato: DefinicaoDeEndpoint | undefined;
  autorizacao: DeclaracaoDeAutorizacao | undefined;
}

export function rotasDeclaradas(
  controladores: Type[] = CONTROLADORES,
): RotaDeclarada[] {
  const rotas: RotaDeclarada[] = [];
  for (const c of controladores) {
    const proto = c.prototype as Record<string, unknown>;
    for (const nome of Object.getOwnPropertyNames(proto)) {
      if (nome === 'constructor') continue;
      const fn = proto[nome];
      if (typeof fn !== 'function') continue;
      const caminho = Reflect.getMetadata(PATH_METADATA, fn) as
        string | undefined;
      const verbo = Reflect.getMetadata(METHOD_METADATA, fn) as
        number | undefined;
      if (caminho === undefined && verbo === undefined) continue; // não é rota
      rotas.push({
        controlador: c.name,
        metodoDaClasse: nome,
        caminhoNest: caminho,
        verboNest: verbo,
        contrato: Reflect.getMetadata(META_CONTRATO, fn) as
          DefinicaoDeEndpoint | undefined,
        autorizacao: (Reflect.getMetadata(META_AUTORIZACAO, fn) ??
          Reflect.getMetadata(META_AUTORIZACAO, c)) as
          DeclaracaoDeAutorizacao | undefined,
      });
    }
  }
  return rotas;
}
