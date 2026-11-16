import { randomBytes } from 'node:crypto';

import { Cifrador } from './cifrador';
import { hashDeToken, Pseudonimizador } from './pseudonimizador';

describe('Cifrador AES-256-GCM', () => {
  const c = new Cifrador(randomBytes(32).toString('base64'));
  it('ida e volta', () =>
    expect(c.decifrar(c.cifrar('Observação sobre o aluno'))).toBe(
      'Observação sobre o aluno',
    ));
  it('IV aleatório: mesmo texto, cifras diferentes', () =>
    expect(c.cifrar('x')).not.toBe(c.cifrar('x')));
  it('adulteração é detectada', () => {
    const v = c.cifrar('abc');
    const bruto = Buffer.from(v.slice(3), 'base64');
    bruto[bruto.length - 1] ^= 1;
    expect(() => c.decifrar(`v1:${bruto.toString('base64')}`)).toThrow();
  });
  it('chave errada é recusada', () =>
    expect(() => new Cifrador('curta')).toThrow());
});

describe('Pseudônimos', () => {
  it('estável por chave e contexto', () => {
    const p = new Pseudonimizador('k'.repeat(40));
    expect(p.estavel('a')).toBe(p.estavel('a'));
    expect(p.estavel('a', 'x')).not.toBe(p.estavel('a', 'y'));
  });
  it('descartável não é ligável entre exportações', () =>
    expect(Pseudonimizador.descartavel()('a')).not.toBe(
      Pseudonimizador.descartavel()('a'),
    ));
  it('hash de token é determinístico e não reversível trivialmente', () =>
    expect(hashDeToken('t')).toHaveLength(64));
});
