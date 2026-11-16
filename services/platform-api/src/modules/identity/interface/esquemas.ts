import { z } from 'zod';

import { Uuid } from '../../../shared/http/esquemas-comuns';
import { PAPEIS } from '../../../shared/kernel/papeis';
import { IDIOMAS, type Usuario } from '../domain/usuario';

export const EsquemaPapel = z.enum(PAPEIS).meta({ id: 'Role', description: 'student=aluno, teacher=professor, coordinator=coordenador, admin=admin da escola, guardian=responsável, researcher=pesquisador, platform_admin=operador da plataforma' });

export const EsquemaPreferencias = z
  .object({
    language: z.enum(IDIOMAS),
    accessibility: z.object({
      highContrast: z.boolean(),
      fontScale: z.number().min(0.75).max(2),
      reducedMotion: z.boolean(),
      screenReader: z.boolean(),
      captions: z.boolean(),
      colorBlindMode: z.enum(['none', 'protanopia', 'deuteranopia', 'tritanopia']),
    }),
  })
  .meta({ id: 'Preferences' });

export const EsquemaMudancaDePreferencias = z
  .object({
    language: z.enum(IDIOMAS).optional(),
    accessibility: EsquemaPreferencias.shape.accessibility.partial().optional(),
  })
  .strict()
  .meta({ id: 'PreferencesPatch' });

export const EsquemaPerfil = z
  .object({
    id: Uuid,
    name: z.string(),
    email: z.string(),
    role: EsquemaPapel,
    schoolId: Uuid.nullable(),
    isMinor: z.boolean(),
    status: z.enum(['active', 'disabled', 'pseudonymized']),
    preferences: EsquemaPreferencias,
  })
  .meta({ id: 'UserProfile' });

export function paraPerfil(u: Usuario): z.infer<typeof EsquemaPerfil> {
  return {
    id: u.id,
    name: u.nome,
    email: u.email,
    role: u.papel,
    schoolId: u.escolaId,
    isMinor: u.menor,
    status: u.situacao,
    preferences: u.preferencias,
  };
}

export const EsquemaLogin = z
  .object({ email: z.email().max(254), senha: z.string().min(1).max(256) })
  .meta({ id: 'LoginRequest' });

export const EsquemaTokens = z
  .object({
    accessToken: z.string(),
    tokenType: z.literal('Bearer'),
    expiresIn: z.number().int().describe('Validade do access token, em segundos'),
    refreshToken: z
      .string()
      .optional()
      .describe('Só no corpo quando o cliente pede X-Refresh-Transport: body (apps sem navegador). Navegadores recebem cookie httpOnly.'),
  })
  .meta({ id: 'Tokens' });

export const EsquemaRespostaLogin = EsquemaTokens.extend({ perfil: EsquemaPerfil }).meta({ id: 'LoginResponse' });

export const EsquemaRefresh = z
  .object({ refreshToken: z.string().min(10).max(512).optional() })
  .meta({ id: 'RefreshRequest' });

export const EsquemaEsqueci = z.object({ email: z.email().max(254) }).meta({ id: 'ForgotPasswordRequest' });
export const EsquemaRedefinir = z
  .object({ token: z.string().min(20).max(256), newPassword: z.string().min(1).max(256) })
  .meta({ id: 'ResetPasswordRequest' });

export const EsquemaNovoUsuario = z
  .object({
    name: z.string().trim().min(1).max(200),
    email: z.email().max(254),
    role: EsquemaPapel,
    schoolId: Uuid.optional(),
    isMinor: z.boolean().optional().describe('Só para alunos. Padrão: true (menor de idade)'),
    password: z.string().min(1).max(256).optional().describe('Senha inicial. Se omitida, um link de ativação é enviado.'),
  })
  .strict()
  .meta({ id: 'CreateUserRequest' });

export const EsquemaCorrecao = z
  .object({ name: z.string().trim().min(1).max(200).optional(), email: z.email().max(254).optional() })
  .strict()
  .refine((v) => v.name !== undefined || v.email !== undefined, 'Informe ao menos um campo')
  .meta({ id: 'RectifyUserRequest' });

export const EsquemaMudancaDePapel = z.object({ role: EsquemaPapel }).strict().meta({ id: 'ChangeRoleRequest' });
export const EsquemaVinculoResponsavel = z.object({ guardianUserId: Uuid }).strict().meta({ id: 'LinkGuardianRequest' });

export const EsquemaResumoDeAluno = z.object({ id: Uuid, name: z.string(), schoolId: Uuid.nullable() }).meta({ id: 'StudentSummary' });
