import type { AtorUsuario } from '../../../shared/kernel/ator';
import type { Papel } from '../../../shared/kernel/papeis';
import {
  codigoBnccValido,
  decidirAcessoAMissao,
  decidirAcessoATurma,
  validarAncoragem,
  validarParametros,
} from './educacao';

const ator = (papel: Papel, id = 'u1'): AtorUsuario => ({
  tipo: 'usuario',
  usuarioId: id,
  papel,
  escolaId: 'A',
  menor: false,
  sessaoId: 's',
});

describe('Missão ancorada à BNCC (RP-001)', () => {
  const catalogo = new Set(['EF07CI13', 'EM13CNT203']);
  it('exige ao menos uma habilidade', () =>
    expect(() => validarAncoragem([], catalogo)).toThrow(/pelo menos uma/));
  it('recusa código fora do catálogo, apontando qual', () => {
    try {
      validarAncoragem(['EF07CI13', 'EF99ZZ99'], catalogo);
      fail();
    } catch (e) {
      expect(JSON.stringify(e)).toContain('EF99ZZ99');
    }
  });
  it('aceita códigos do catálogo sem diferenciar caixa', () =>
    expect(() => validarAncoragem(['ef07ci13'], catalogo)).not.toThrow());
  it('formato BNCC', () => {
    expect(codigoBnccValido('EF07CI13')).toBe(true);
    expect(codigoBnccValido('EM13CNT203')).toBe(true);
    expect(codigoBnccValido('XX07CI13')).toBe(false);
  });
  it('limita tamanho dos parâmetros', () =>
    expect(() => validarParametros({ x: 'a'.repeat(9000) })).toThrow(
      /grandes demais/,
    ));
});

describe('Acesso a turma e missão', () => {
  const turma = {
    existe: true,
    escolaId: 'A',
    professorId: 'prof',
    alunoMatriculado: false,
  };
  it('professor de outra turma da mesma escola → negado; da turma → permitido', () => {
    expect(decidirAcessoATurma(ator('teacher'), turma, 'ler')).toBe('negado');
    expect(decidirAcessoATurma(ator('teacher', 'prof'), turma, 'gerir')).toBe(
      'permitido',
    );
  });
  it('aluno matriculado só lê', () => {
    const t = { ...turma, alunoMatriculado: true };
    expect(decidirAcessoATurma(ator('student'), t, 'ler')).toBe('permitido');
    expect(decidirAcessoATurma(ator('student'), t, 'gerir')).toBe('negado');
  });
  it('outra escola → inexistente', () =>
    expect(
      decidirAcessoATurma(ator('admin'), { ...turma, escolaId: 'B' }, 'ler'),
    ).toBe('inexistente'));
  it('aluno só vê missão publicada para a turma dele', () => {
    const m = {
      existe: true,
      escolaId: 'A',
      autorId: 'prof',
      publicadaParaTurmaDoAluno: false,
      publicadaParaTurmaDoProfessor: false,
      publicada: false,
    };
    expect(decidirAcessoAMissao(ator('student'), m, 'ler')).toBe('negado');
    expect(
      decidirAcessoAMissao(
        ator('student'),
        { ...m, publicadaParaTurmaDoAluno: true },
        'ler',
      ),
    ).toBe('permitido');
    expect(decidirAcessoAMissao(ator('teacher'), m, 'gerir')).toBe('negado');
    expect(decidirAcessoAMissao(ator('teacher'), m, 'ler')).toBe('negado'); // rascunho de colega
    expect(
      decidirAcessoAMissao(ator('teacher'), { ...m, publicada: true }, 'ler'),
    ).toBe('permitido');
    expect(decidirAcessoAMissao(ator('teacher', 'prof'), m, 'gerir')).toBe(
      'permitido',
    );
  });
});
