import { randomUUID } from 'node:crypto';
import http from 'node:http';
import type { AddressInfo } from 'node:net';

import { exportJWK, generateKeyPair, type JWTPayload, SignJWT } from 'jose';

/**
 * Provedor de identidade LOCAL, só para teste: serve descoberta OIDC, JWKS e token endpoint,
 * e assina id_tokens (OIDC e LTI 1.3). Não substitui um teste contra LMS/IdP reais.
 */
export class ProvedorDeTeste {
  servidor?: http.Server;
  url = '';
  private chave?: CryptoKey;
  private codigos = new Map<string, JWTPayload>();
  clientId = 'ecosfera-teste';

  async iniciar(): Promise<void> {
    const { publicKey, privateKey } = await generateKeyPair('RS256');
    this.chave = privateKey;
    const jwk = {
      ...(await exportJWK(publicKey)),
      kid: 'k1',
      alg: 'RS256',
      use: 'sig',
    };
    this.servidor = http.createServer((req, res) => {
      const u = new URL(req.url ?? '/', this.url);
      const json = (s: number, b: unknown) =>
        res
          .writeHead(s, { 'content-type': 'application/json' })
          .end(JSON.stringify(b));
      if (u.pathname === '/.well-known/openid-configuration') {
        return json(200, {
          issuer: this.url,
          authorization_endpoint: `${this.url}/authorize`,
          token_endpoint: `${this.url}/token`,
          jwks_uri: `${this.url}/jwks`,
        });
      }
      if (u.pathname === '/jwks') return json(200, { keys: [jwk] });
      if (u.pathname === '/token' && req.method === 'POST') {
        let corpo = '';
        req.on('data', (c: Buffer) => (corpo += c.toString()));
        req.on('end', () => {
          const p = new URLSearchParams(corpo);
          const claims = this.codigos.get(p.get('code') ?? '');
          if (!claims || !p.get('code_verifier'))
            return json(400, { error: 'invalid_grant' });
          this.codigos.delete(p.get('code')!);
          void this.assinar(claims).then((t) =>
            json(200, { id_token: t, token_type: 'Bearer' }),
          );
        });
        return;
      }
      json(404, {});
    });
    await new Promise<void>((ok) => this.servidor!.listen(0, '127.0.0.1', ok));
    this.url = `http://127.0.0.1:${(this.servidor.address() as AddressInfo).port}`;
  }

  async assinar(claims: JWTPayload, chave = this.chave!): Promise<string> {
    return new SignJWT(claims)
      .setProtectedHeader({ alg: 'RS256', kid: 'k1' })
      .setIssuer(this.url)
      .setAudience(this.clientId)
      .setIssuedAt()
      .setExpirationTime('5m')
      .sign(chave);
  }

  /** Simula o usuário autenticando no provedor: devolve um code ligado às claims. */
  emitirCodigo(claims: JWTPayload): string {
    const c = randomUUID();
    this.codigos.set(c, claims);
    return c;
  }

  async parar(): Promise<void> {
    await new Promise((ok) => this.servidor?.close(ok));
  }
}
