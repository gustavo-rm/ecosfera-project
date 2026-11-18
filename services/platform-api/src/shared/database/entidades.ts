import {
  AvaliacaoEntity,
  ConfiguracaoDeAlertaEntity,
  EstimativaDeCompetenciaEntity,
  EvidenciaEntity,
  FeedbackEntity,
  PerfilCognitivoEntity,
  RegistroDeExportacaoEntity,
} from '../../modules/assessment/infrastructure/persistencia/avaliacao.entity';
import {
  CompetenciaEntity,
  HabilidadeBnccEntity,
} from '../../modules/education/infrastructure/persistencia/curriculo.entity';
import { EscolaEntity } from '../../modules/education/infrastructure/persistencia/escola.entity';
import {
  MissaoEntity,
  MissaoHabilidadeEntity,
  PublicacaoDeMissaoEntity,
} from '../../modules/education/infrastructure/persistencia/missao.entity';
import {
  MatriculaEntity,
  TrilhaEntity,
  TurmaEntity,
} from '../../modules/education/infrastructure/persistencia/turma.entity';
import { ConsentimentoEntity } from '../../modules/identity/infrastructure/persistencia/consentimento.entity';
import {
  ContextoLtiEntity,
  IdentidadeExternaEntity,
  PlataformaLtiEntity,
  ProvedorOidcEntity,
} from '../../modules/identity/infrastructure/persistencia/federacao.entity';
import {
  PedidoDeTitularEntity,
  PoliticaDeRetencaoEntity,
} from '../../modules/identity/infrastructure/persistencia/lgpd.entity';
import { TextoDeConsentimentoEntity } from '../../modules/identity/infrastructure/persistencia/texto-consentimento.entity';
import { UsuarioEntity } from '../../modules/identity/infrastructure/persistencia/usuario.entity';
import { VinculoResponsavelEntity } from '../../modules/identity/infrastructure/persistencia/vinculo-responsavel.entity';
import {
  PlanetaMetaEntity,
  RegistroDeIdempotenciaEntity,
} from '../../modules/orchestration/infrastructure/persistencia/planeta.entity';
import { AuditLogEntity } from '../auditoria/audit-log.entity';
import {
  EventoDeSaidaEntity,
  EventoProcessadoEntity,
} from '../eventos/eventos.entity';

/** Todas as entidades do schema `platform`. A verificação de drift compara isto com as migrações. */
export const ENTIDADES = [
  EscolaEntity,
  UsuarioEntity,
  VinculoResponsavelEntity,
  ConsentimentoEntity,
  TextoDeConsentimentoEntity,
  IdentidadeExternaEntity,
  PlataformaLtiEntity,
  ProvedorOidcEntity,
  ContextoLtiEntity,
  PedidoDeTitularEntity,
  PoliticaDeRetencaoEntity,
  TrilhaEntity,
  TurmaEntity,
  MatriculaEntity,
  MissaoEntity,
  MissaoHabilidadeEntity,
  PublicacaoDeMissaoEntity,
  CompetenciaEntity,
  HabilidadeBnccEntity,
  PerfilCognitivoEntity,
  EstimativaDeCompetenciaEntity,
  EvidenciaEntity,
  AvaliacaoEntity,
  FeedbackEntity,
  ConfiguracaoDeAlertaEntity,
  RegistroDeExportacaoEntity,
  PlanetaMetaEntity,
  RegistroDeIdempotenciaEntity,
  AuditLogEntity,
  EventoDeSaidaEntity,
  EventoProcessadoEntity,
];
