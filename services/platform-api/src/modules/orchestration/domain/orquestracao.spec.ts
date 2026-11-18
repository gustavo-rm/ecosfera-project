import type { AtorUsuario } from '../../../shared/kernel/ator';
import type { Papel } from '../../../shared/kernel/papeis';
import { decidirAcessoAoPlaneta } from './planeta';
import { redigirPII, sanitizarTextoDaIA } from './redacao';

const ator = (papel: Papel, id = 'u1'): AtorUsuario => ({
  tipo: 'usuario',
  usuarioId: id,
  papel,
  escolaId: 'A',
  menor: true,
  sessaoId: 's',
});
const fatos = {
  existe: true,
  donoId: 'dono',
  escolaId: 'A',
  professorDoDono: false,
};

describe('Posse do planeta', () => {
  it('outro aluno → inexistente (404), mesmo na mesma escola', () =>
    expect(decidirAcessoAoPlaneta(ator('student'), fatos, 'ler')).toBe(
      'inexistente',
    ));
  it('dono lê e age', () => {
    expect(decidirAcessoAoPlaneta(ator('student', 'dono'), fatos, 'agir')).toBe(
      'permitido',
    );
  });
  it('professor do dono lê, mas não age', () => {
    expect(
      decidirAcessoAoPlaneta(
        ator('teacher'),
        { ...fatos, professorDoDono: true },
        'ler',
      ),
    ).toBe('permitido');
    expect(
      decidirAcessoAoPlaneta(
        ator('teacher'),
        { ...fatos, professorDoDono: true },
        'agir',
      ),
    ).toBe('negado');
    expect(decidirAcessoAoPlaneta(ator('teacher'), fatos, 'ler')).toBe(
      'negado',
    );
  });
  it('outra escola → inexistente', () =>
    expect(
      decidirAcessoAoPlaneta(ator('admin'), { ...fatos, escolaId: 'B' }, 'ler'),
    ).toBe('inexistente'));
});

describe('Proteção da IA no gateway', () => {
  it('redige e-mail, CPF, telefone, CEP, links e o nome do aluno', () => {
    const r = redigirPII(
      'Sou Lucas Silva, lucas@x.com, CPF 123.456.789-09, tel (11) 98765-4321, CEP 01310-100, veja https://a.b/c',
      ['Lucas Silva'],
    );
    expect(r).not.toMatch(/Lucas|Silva|lucas@|123\.456|98765|01310|https/);
    expect(r).toContain('[email]');
  });
  it('trata texto da IA como dado: remove caracteres de controle', () =>
    expect(sanitizarTextoDaIA('ok\u0000\u001bfim\n')).toBe('okfim\n'));
});
