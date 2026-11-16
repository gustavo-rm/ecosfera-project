import { Consentimento, permiteTratamento } from './consentimento';
import { problemasDaSenha } from './politica-de-senha';
import {
  mesclarPreferencias,
  normalizarEmail,
  PREFERENCIAS_PADRAO,
  Usuario,
} from './usuario';

describe('Política de senha', () => {
  it.each([
    ['curta1', 'pelo menos 10'],
    ['somenteletras', 'letras e números'],
    ['1234567890123', 'letras e números'],
    ['senha12345', 'óbvia'],
    ['marina2026xx', 'e-mail'],
  ])('recusa %s', (s, trecho) =>
    expect(problemasDaSenha(s, 'marina@escola.br').join(' ')).toContain(trecho),
  );
  it('aceita senha razoável', () =>
    expect(problemasDaSenha('Planeta-azul-2026', 'x@y.z')).toEqual([]));
});

describe('Consentimento', () => {
  it('nasce pendente e não permite tratamento de menor', () => {
    const c = Consentimento.pendente('a', 'platform_use');
    expect(c.valido()).toBe(false);
    expect(permiteTratamento(true, c)).toBe(false);
    expect(permiteTratamento(true, undefined)).toBe(false);
  });
  it('maior de idade não depende do responsável', () =>
    expect(permiteTratamento(false, undefined)).toBe(true));
  it('concessão registra responsável, versão e data; revogação tem efeito', () => {
    const c = Consentimento.pendente('a', 'learning_assessment');
    const agora = new Date('2026-01-01');
    c.conceder('r', '0.1', agora);
    expect([
      c.valido(),
      c.responsavelId,
      c.versaoDoTexto,
      c.concedidoEm,
    ]).toEqual([true, 'r', '0.1', agora]);
    c.revogar('r', agora);
    expect(c.valido()).toBe(false);
    expect(() => c.revogar('r', agora)).toThrow(/Não há consentimento ativo/);
  });
});

describe('Usuário e preferências', () => {
  it('normaliza e-mail', () =>
    expect(normalizarEmail('  Ana@Escola.BR ')).toBe('ana@escola.br'));
  it('mescla preferências parciais sem perder o padrão', () => {
    const p = mesclarPreferencias(PREFERENCIAS_PADRAO, {
      accessibility: { highContrast: true },
    });
    expect(p.accessibility).toMatchObject({ highContrast: true, fontScale: 1 });
    expect(p.language).toBe('pt-BR');
  });
  it('pseudonimização remove PII e impede login', () => {
    const u = new Usuario(
      'id',
      'A',
      'Lucas',
      'lucas@x.com',
      'student',
      true,
      'active',
      PREFERENCIAS_PADRAO,
      '$argon2id$...',
    );
    u.pseudonimizar('p1');
    expect([
      u.nome,
      u.email.includes('lucas'),
      u.senhaHash,
      u.podeAutenticar(),
    ]).toEqual(['[removido]', false, '!', false]);
  });
  it('mudar papel de aluno para professor desmarca menor', () => {
    const u = new Usuario(
      'id',
      'A',
      'n',
      'e',
      'student',
      true,
      'active',
      PREFERENCIAS_PADRAO,
      'h',
    );
    u.alterarPapel('teacher');
    expect(u.menor).toBe(false);
  });
});
