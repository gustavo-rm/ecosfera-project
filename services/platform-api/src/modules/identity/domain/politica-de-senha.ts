/**
 * Política de senha (RF-003/006): razoável para escola, sem regras que levem a post-it.
 * - 10 a 128 caracteres;
 * - ao menos uma letra e um dígito;
 * - não pode conter a parte local do e-mail;
 * - não pode estar na lista de senhas óbvias.
 */
const OBVIAS = new Set([
  'senha12345',
  'password123',
  '1234567890',
  'qwerty1234',
  'abc1234567',
  'ecosfera123',
  'escola12345',
  'senha123456',
]);

export function problemasDaSenha(senha: string, email?: string): string[] {
  const p: string[] = [];
  if (senha.length < 10) p.push('A senha precisa ter pelo menos 10 caracteres');
  if (senha.length > 128) p.push('A senha pode ter no máximo 128 caracteres');
  if (!/\p{L}/u.test(senha) || !/\d/.test(senha))
    p.push('A senha precisa ter letras e números');
  const local = email?.split('@')[0]?.toLowerCase();
  if (local && local.length >= 3 && senha.toLowerCase().includes(local))
    p.push('A senha não pode conter o seu e-mail');
  if (OBVIAS.has(senha.toLowerCase())) p.push('Essa senha é óbvia demais');
  return p;
}
