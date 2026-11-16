/**
 * Proteção da IA, parte do gateway (Dossiê §10): remove PII do texto livre antes de
 * enviá-lo ao serviço de IA. Conservador: prefere redigir demais a vazar.
 */
const PADROES: [RegExp, string][] = [
  [/[\w.+-]+@[\w-]+(\.[\w-]+)+/g, '[email]'],
  [/\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b/g, '[cpf]'],
  [/(\+?55\s?)?(\(?\d{2}\)?\s?)?9?\d{4}[-\s]?\d{4}\b/g, '[telefone]'],
  [/\b\d{5}-?\d{3}\b/g, '[cep]'],
  [/https?:\/\/\S+/g, '[link]'],
];

export function redigirPII(
  texto: string,
  nomesConhecidos: string[] = [],
): string {
  let r = texto;
  for (const [re, troca] of PADROES) r = r.replace(re, troca);
  for (const nome of nomesConhecidos) {
    for (const parte of nome.split(/\s+/).filter((p) => p.length >= 3)) {
      r = r.replace(
        new RegExp(
          `\\b${parte.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`,
          'gi',
        ),
        '[nome]',
      );
    }
  }
  return r;
}

/** O que volta da IA é dado, não instrução: tira caracteres de controle (exceto quebra de linha). */
export function sanitizarTextoDaIA(texto: string): string {
  // eslint-disable-next-line no-control-regex
  return texto.replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, '');
}
