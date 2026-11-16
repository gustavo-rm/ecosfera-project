import type { AtorUsuario } from './ator';
import type { Papel } from './papeis';
import { decidirAcessoAoUsuario, type FatosDoAlvo } from './politica-de-acesso';

const ator = (
  papel: Papel,
  escolaId: string | null = 'A',
  id = 'u1',
): AtorUsuario => ({
  tipo: 'usuario',
  usuarioId: id,
  papel,
  escolaId,
  menor: false,
  sessaoId: 's',
});
const alvo = (o: Partial<FatosDoAlvo> = {}): FatosDoAlvo => ({
  existe: true,
  alvoId: 'alvo',
  escolaId: 'A',
  lecionaParaAlvo: false,
  responsavelPeloAlvo: false,
  ...o,
});

describe('Política de acesso a dados de usuário', () => {
  it('inexistente → 404', () =>
    expect(
      decidirAcessoAoUsuario(ator('admin'), alvo({ existe: false }), 'ler'),
    ).toBe('inexistente'));
  it('outra escola é tratada como inexistente para todos os papéis escolares', () => {
    for (const p of ['admin', 'coordinator', 'teacher', 'student'] as Papel[])
      expect(
        decidirAcessoAoUsuario(ator(p), alvo({ escolaId: 'B' }), 'ler'),
      ).toBe('inexistente');
  });
  it('aluno lê a si mesmo, mas NÃO os próprios dados pedagógicos (RP-004)', () => {
    const eu = alvo({ alvoId: 'u1' });
    expect(decidirAcessoAoUsuario(ator('student'), eu, 'ler')).toBe(
      'permitido',
    );
    expect(decidirAcessoAoUsuario(ator('student'), eu, 'ler-pedagogico')).toBe(
      'negado',
    );
    expect(decidirAcessoAoUsuario(ator('student'), eu, 'gerir')).toBe('negado');
  });
  it('aluno não lê outro aluno', () =>
    expect(decidirAcessoAoUsuario(ator('student'), alvo(), 'ler')).toBe(
      'negado',
    ));
  it('professor só lê aluno da própria turma', () => {
    expect(
      decidirAcessoAoUsuario(ator('teacher'), alvo(), 'ler-pedagogico'),
    ).toBe('negado');
    expect(
      decidirAcessoAoUsuario(
        ator('teacher'),
        alvo({ lecionaParaAlvo: true }),
        'ler-pedagogico',
      ),
    ).toBe('permitido');
    expect(
      decidirAcessoAoUsuario(
        ator('teacher'),
        alvo({ lecionaParaAlvo: true }),
        'gerir',
      ),
    ).toBe('negado');
  });
  it('coordenação lê, não gere; admin gere', () => {
    expect(
      decidirAcessoAoUsuario(ator('coordinator'), alvo(), 'ler-pedagogico'),
    ).toBe('permitido');
    expect(decidirAcessoAoUsuario(ator('coordinator'), alvo(), 'gerir')).toBe(
      'negado',
    );
    expect(decidirAcessoAoUsuario(ator('admin'), alvo(), 'gerir')).toBe(
      'permitido',
    );
  });
  it('responsável: só os vinculados, só leitura básica', () => {
    expect(decidirAcessoAoUsuario(ator('guardian', null), alvo(), 'ler')).toBe(
      'inexistente',
    );
    expect(
      decidirAcessoAoUsuario(
        ator('guardian', null),
        alvo({ responsavelPeloAlvo: true }),
        'ler',
      ),
    ).toBe('permitido');
    expect(
      decidirAcessoAoUsuario(
        ator('guardian', null),
        alvo({ responsavelPeloAlvo: true }),
        'ler-pedagogico',
      ),
    ).toBe('negado');
  });
  it('pesquisador nunca lê dado individual; operador não lê dado pedagógico', () => {
    expect(
      decidirAcessoAoUsuario(
        ator('researcher', null),
        alvo({ escolaId: null }),
        'ler',
      ),
    ).toBe('inexistente');
    expect(
      decidirAcessoAoUsuario(
        ator('platform_admin', null),
        alvo(),
        'ler-pedagogico',
      ),
    ).toBe('negado');
  });
});
