import type { ExecutionContext } from '@nestjs/common';
import { Reflector } from '@nestjs/core';

import type { AtorUsuario } from '../kernel/ator';
import {
  ErroAcessoNegado,
  ErroConsentimentoAusente,
  ErroNaoAutenticado,
  ErroNaoEncontrado,
} from '../kernel/erros';
import {
  type DeclaracaoDeAutorizacao,
  META_AUTORIZACAO,
} from './autorizacao.decorator';
import { GuardCentral } from './guard-central';
import { RegistroDeRegrasDePosse } from './registro-de-posse';

const aluno: AtorUsuario = {
  tipo: 'usuario',
  usuarioId: 'u1',
  papel: 'student',
  escolaId: 'A',
  menor: true,
  sessaoId: 's',
};

function contexto(
  decl: DeclaracaoDeAutorizacao | undefined,
  req: Record<string, unknown>,
): ExecutionContext {
  const handler = () => undefined;
  if (decl) Reflect.defineMetadata(META_AUTORIZACAO, decl, handler);
  return {
    getType: () => 'http',
    getHandler: () => handler,
    getClass: () => class {},
    switchToHttp: () => ({ getRequest: () => req }),
  } as unknown as ExecutionContext;
}

describe('Guard central (negar por padrão)', () => {
  const registro = new RegistroDeRegrasDePosse();
  registro.registrar('teste', (_a, id) =>
    Promise.resolve(
      id === '00000000-0000-4000-8000-000000000001'
        ? 'permitido'
        : id === '00000000-0000-4000-8000-000000000002'
          ? 'negado'
          : 'inexistente',
    ),
  );
  let consentido = false;
  const guard = new GuardCentral(
    new Reflector(),
    {
      verificarAcesso: () => Promise.resolve(aluno),
      verificarServico: () => Promise.reject(new ErroNaoAutenticado()),
    },
    { permite: () => Promise.resolve(consentido) },
    registro,
  );
  const auth = {
    headers: { authorization: 'Bearer x' },
    params: {} as Record<string, string>,
  };

  it('rota SEM @Autorizacao é negada', async () => {
    await expect(
      guard.canActivate(contexto(undefined, auth)),
    ).rejects.toBeInstanceOf(ErroAcessoNegado);
  });
  it('sem token → 401', async () => {
    await expect(
      guard.canActivate(contexto({ papeis: ['student'] }, { headers: {} })),
    ).rejects.toBeInstanceOf(ErroNaoAutenticado);
  });
  it('papel fora da lista → 403', async () => {
    await expect(
      guard.canActivate(contexto({ papeis: ['teacher'] }, auth)),
    ).rejects.toBeInstanceOf(ErroAcessoNegado);
  });
  it('posse: permitido, negado (403), inexistente/ID malformado (404)', async () => {
    const d: DeclaracaoDeAutorizacao = {
      papeis: ['student'],
      posse: { regra: 'teste' },
    };
    await expect(
      guard.canActivate(
        contexto(d, {
          ...auth,
          params: { id: '00000000-0000-4000-8000-000000000001' },
        }),
      ),
    ).resolves.toBe(true);
    await expect(
      guard.canActivate(
        contexto(d, {
          ...auth,
          params: { id: '00000000-0000-4000-8000-000000000002' },
        }),
      ),
    ).rejects.toBeInstanceOf(ErroAcessoNegado);
    await expect(
      guard.canActivate(
        contexto(d, {
          ...auth,
          params: { id: '00000000-0000-4000-8000-000000000003' },
        }),
      ),
    ).rejects.toBeInstanceOf(ErroNaoEncontrado);
    await expect(
      guard.canActivate(contexto(d, { ...auth, params: { id: "1' OR 1=1" } })),
    ).rejects.toBeInstanceOf(ErroNaoEncontrado);
  });
  it('regra de posse desconhecida → negado', async () => {
    await expect(
      guard.canActivate(
        contexto(
          { papeis: ['student'], posse: { regra: 'nao-existe' } },
          { ...auth, params: { id: '00000000-0000-4000-8000-000000000001' } },
        ),
      ),
    ).rejects.toBeInstanceOf(ErroAcessoNegado);
  });
  it('ator menor sem consentimento → consent-required; com consentimento passa', async () => {
    consentido = false;
    await expect(
      guard.canActivate(
        contexto({ papeis: ['student'], consentimento: 'platform_use' }, auth),
      ),
    ).rejects.toBeInstanceOf(ErroConsentimentoAusente);
    consentido = true;
    await expect(
      guard.canActivate(
        contexto({ papeis: ['student'], consentimento: 'platform_use' }, auth),
      ),
    ).resolves.toBe(true);
  });
  it('rota de serviço recusa token de usuário', async () => {
    await expect(
      guard.canActivate(contexto({ servico: true }, auth)),
    ).rejects.toBeInstanceOf(ErroNaoAutenticado);
  });
});
