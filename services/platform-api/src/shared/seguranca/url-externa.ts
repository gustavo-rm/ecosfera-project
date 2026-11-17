import { lookup } from 'node:dns/promises';
import { isIP } from 'node:net';

import { ErroDeValidacao } from '../kernel/erros';

/** Faixas que um servidor não deve alcançar por URL vinda de usuário (SSRF). */
export function ipInterno(ip: string): boolean {
  const v4 = ip.startsWith('::ffff:') ? ip.slice(7) : ip;
  if (isIP(v4) === 4) {
    const [a, b] = v4.split('.').map(Number) as [number, number];
    return (
      a === 10 ||
      a === 127 ||
      a === 0 ||
      (a === 169 && b === 254) ||
      (a === 172 && b >= 16 && b <= 31) ||
      (a === 192 && b === 168) ||
      (a === 100 && b >= 64 && b <= 127) ||
      a >= 224
    );
  }
  const l = ip.toLowerCase();
  return (
    l === '::1' ||
    l === '::' ||
    l.startsWith('fc') ||
    l.startsWith('fd') ||
    l.startsWith('fe80')
  );
}

/**
 * URL configurada por admin (IdP, JWKS, LMS). Em produção: só https e host público.
 * Fora de produção, http e localhost são aceitos (provedor local de teste).
 */
export async function exigirUrlExterna(
  url: string,
  producao: boolean,
  campo = 'url',
): Promise<void> {
  let u: URL;
  try {
    u = new URL(url);
  } catch {
    throw new ErroDeValidacao('URL inválida', [
      { campo, mensagem: 'URL inválida' },
    ]);
  }
  if (!producao) return;
  if (u.protocol !== 'https:')
    throw new ErroDeValidacao('Em produção a URL precisa ser https', [
      { campo, mensagem: 'use https' },
    ]);
  const host = u.hostname.replace(/^\[|\]$/g, '');
  const enderecos = isIP(host)
    ? [host]
    : (await lookup(host, { all: true }).catch(() => [])).map((e) => e.address);
  if (enderecos.length === 0 || enderecos.some(ipInterno)) {
    throw new ErroDeValidacao(
      'A URL aponta para endereço interno ou não resolve',
      [{ campo, mensagem: 'endereço não permitido' }],
    );
  }
}

/** Nomes de variável aceitos para o segredo de cliente OIDC (nunca segredos do próprio servidor). */
export const PADRAO_VARIAVEL_DE_SEGREDO_OIDC =
  /^OIDC_CLIENT_SECRET_[A-Z0-9_]{1,40}$/;
