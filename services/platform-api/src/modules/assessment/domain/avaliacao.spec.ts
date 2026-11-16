import { calcularAlertas, CONFIGURACAO_PADRAO } from './alertas';
import { anonimizar, procurarPII, semanaIso } from './anonimizacao';

describe('Alertas de dificuldade (RF-077)', () => {
  const agora = new Date('2026-06-15T12:00:00Z');
  it('alerta só com domínio baixo, incerteza aceitável e evidências suficientes', () => {
    const a = calcularAlertas(
      [
        {
          alunoId: 'a',
          competencia: 'C',
          probabilidade: 0.2,
          incerteza: 0.1,
          evidencias: 5,
        },
        {
          alunoId: 'b',
          competencia: 'C',
          probabilidade: 0.2,
          incerteza: 0.9,
          evidencias: 5,
        },
        {
          alunoId: 'c',
          competencia: 'C',
          probabilidade: 0.2,
          incerteza: 0.1,
          evidencias: 1,
        },
        {
          alunoId: 'd',
          competencia: 'C',
          probabilidade: 0.8,
          incerteza: 0.1,
          evidencias: 9,
        },
      ],
      new Map(),
      CONFIGURACAO_PADRAO,
      agora,
    );
    expect(a.map((x) => x.studentId)).toEqual(['a']);
  });
  it('alerta de inatividade', () => {
    const a = calcularAlertas(
      [],
      new Map([
        ['x', new Date('2026-05-01')],
        ['y', new Date('2026-06-14')],
        ['z', null],
      ]),
      CONFIGURACAO_PADRAO,
      agora,
    );
    expect(a.map((x) => x.studentId).sort()).toEqual(['x', 'z']);
  });
});

describe('Anonimização do dataset (RNF-011)', () => {
  const linha = (aluno: string, escola: string) => ({
    alunoId: aluno,
    escolaId: escola,
    nivel: 'medio',
    competencia: 'C',
    probabilidade: 0.5123,
    incerteza: 0.2,
    evidencias: 3,
    atualizadoEm: new Date('2026-03-04'),
    sintetico: false,
  });
  const ids = (n: number, escola: string) =>
    Array.from({ length: n }, (_, i) =>
      linha(`aaaaaaaa-0000-4000-8000-00000000000${i}`, escola),
    );
  it('suprime grupos com menos de k alunos e não deixa sair identificador', () => {
    const brutas = [
      ...ids(5, 'e1111111-0000-4000-8000-000000000000'),
      ...ids(2, 'e2222222-0000-4000-8000-000000000000'),
    ];
    let n = 0;
    const r = anonimizar(brutas, 5, (v) => `p${(n++).toString()}-${v.length}`);
    expect(r.gruposSuprimidos).toBe(1);
    expect(r.linhasSuprimidas).toBe(2);
    expect(r.linhas).toHaveLength(5);
    const texto = JSON.stringify(r.linhas);
    expect(
      procurarPII(
        texto,
        brutas.flatMap((b) => [b.alunoId, b.escolaId]),
      ),
    ).toEqual([]);
    expect(r.linhas[0].probability).toBe(0.51);
    expect(r.linhas[0].week).toBe('2026-W10');
  });
  it('o detector de PII acha UUID, e-mail e valores conhecidos', () => {
    expect(procurarPII('x 3f1c2b9a-1111-4222-8333-444455556666', [])).toContain(
      'uuid',
    );
    expect(procurarPII('ana@escola.br', [])).toContain('email');
    expect(procurarPII('nome Marina', ['Marina'])).toHaveLength(1);
  });
  it('semana ISO', () =>
    expect(semanaIso(new Date('2026-01-01'))).toBe('2026-W01'));
});
