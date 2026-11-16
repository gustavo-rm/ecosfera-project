/** Gera docs/backend/MATRIZ_DE_AUTORIZACAO.md a partir das declarações @Autorizacao do código. */
import 'reflect-metadata';

import { writeFileSync } from 'node:fs';
import { join } from 'node:path';

import { rotasDeclaradas } from '../src/shared/http/catalogo-de-rotas';

const NOMES: Record<string, string> = {
  student: 'aluno', teacher: 'professor', coordinator: 'coordenador', admin: 'admin da escola', guardian: 'responsável', researcher: 'pesquisador', platform_admin: 'operador da plataforma',
};
const REGRAS: Record<string, string> = {
  'usuario:ler': 'próprio usuário; responsável vinculado; admin/coordenação da escola; professor só de aluno da sua turma; outra escola → 404',
  'usuario:gerir': 'admin da mesma escola ou operador; outra escola → 404',
  'usuario:pedagogico': 'professor do aluno, coordenação/admin da escola; o próprio aluno NÃO (RP-004); outra escola → 404',
  'usuario:proprio': 'só o próprio usuário',
  'turma:ler': 'professor da turma; aluno matriculado; coordenação/admin da escola; outra escola → 404',
  'turma:gerir': 'professor da turma; coordenação/admin da escola; outra escola → 404',
  'missao:ler': 'equipe da escola; aluno só se publicada para turma dele; outra escola → 404',
  'missao:gerir': 'autor; coordenação/admin da escola',
  'planeta:ler': 'dono (aluno); professor de turma do dono; coordenação/admin da escola; outro aluno → 404',
  'planeta:agir': 'só o dono (aluno)',
};

const linhas = rotasDeclaradas()
  .filter((r) => r.contrato && !r.contrato.interna)
  .sort((a, b) => a.contrato!.caminho.localeCompare(b.contrato!.caminho) || a.contrato!.metodo.localeCompare(b.contrato!.metodo))
  .map((r) => {
    const a = r.autorizacao!;
    const quem = 'publico' in a ? `**público** — ${a.motivo}` : 'servico' in a ? `**credencial de serviço** (${a.servicos?.join(', ') ?? 'SERVICE_ALLOWED_NAMES'})` : a.papeis.map((p) => NOMES[p] ?? p).join(', ');
    const posse = !('papeis' in a) || !a.posse ? '—' : `\`${a.posse.regra}\` sobre \`${a.posse.origem ?? 'params'}.${a.posse.parametro ?? 'id'}\``;
    const consent = 'papeis' in a && a.consentimento ? `\`${a.consentimento}\` se o ator é menor` : '—';
    return `| ${r.contrato!.metodo} | \`${r.contrato!.caminho}\` | ${quem} | ${posse} | ${consent} | ${r.controlador}.${r.metodoDaClasse} |`;
  });

const md = `# Matriz de autorização do platform-api

> **Gerada do código** (\`pnpm authz:matriz\`, a partir dos decoradores \`@Autorizacao\`). Não edite à mão.
> O teste \`test/seguranca/matriz-de-acesso.int-spec.ts\` percorre esta mesma lista e confere que o código NEGA
> o que a matriz manda negar (sem token → 401; papel fora da lista → 403; recurso de outra escola → 404).

Regras gerais:

- **Negar por padrão**: rota sem \`@Autorizacao\` é recusada pelo guard central e reprovada pelo teste de arquitetura.
- **Defesa em profundidade**: a regra de posse é avaliada no guard e de novo no caso de uso, com fatos carregados pelo próprio caso de uso.
- **Isolamento por escola** (RNF-013): recurso de outra escola responde **404** (não revela existência); mesma escola sem permissão responde **403**.
- **Consentimento**: além da coluna abaixo (ator menor), todo caso de uso que lê dado de um aluno confere o consentimento **do titular** (\`platform_use\` para planeta, \`learning_assessment\` para avaliação).

Regras de posse:

${Object.entries(REGRAS).map(([k, v]) => `- \`${k}\`: ${v}`).join('\n')}

| Método | Rota | Quem pode | Posse | Consentimento | Implementação |
|---|---|---|---|---|---|
${linhas.join('\n')}

WebSocket \`GET /planets/{id}/stream\`: aluno, professor, coordenação, admin; posse \`planeta:ler\`; consentimento \`platform_use\` do dono; conexão fechada (4403) quando o consentimento é revogado e (4401) quando a sessão é revogada.
`;
writeFileSync(join(__dirname, '..', '..', '..', 'docs', 'backend', 'MATRIZ_DE_AUTORIZACAO.md'), md);
console.log(`Matriz com ${linhas.length} rotas escrita.`);
