/** Documentação navegável estática do OpenAPI (sem JavaScript nem CDN de terceiros). */
const esc = (s: unknown) =>
  (typeof s === 'string'
    ? s
    : s === undefined || s === null
      ? ''
      : JSON.stringify(s)
  ).replace(
    /[&<>"]/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]!,
  );

export function gerarHtmlDaDocumentacao(doc: Record<string, unknown>): string {
  const paths = doc.paths as Record<
    string,
    Record<string, Record<string, unknown>>
  >;
  const schemas = (doc.components as { schemas: Record<string, unknown> })
    .schemas;
  const porTag = new Map<string, string[]>();
  for (const [p, ops] of Object.entries(paths)) {
    for (const [m, op] of Object.entries(ops)) {
      const tag = (op.tags as string[])[0];
      const respostas = Object.entries(
        op.responses as Record<string, { description: string }>,
      )
        .map(([s, r]) => `<li><code>${s}</code> ${esc(r.description)}</li>`)
        .join('');
      const auth = `<pre>${esc(JSON.stringify(op['x-authorization']))}</pre>`;
      const params = (
        (op.parameters as
          { name: string; in: string; required: boolean }[] | undefined) ?? []
      )
        .map(
          (x) =>
            `<code>${esc(x.in)}:${esc(x.name)}${x.required ? '*' : ''}</code>`,
        )
        .join(' ');
      const corpo = op.requestBody
        ? `<pre>${esc(JSON.stringify((op.requestBody as { content: Record<string, { schema: unknown }> }).content['application/json']?.schema))}</pre>`
        : '';
      (porTag.get(tag) ?? porTag.set(tag, []).get(tag)!).push(
        `<details id="${esc(op.operationId)}"><summary><span class="m ${m}">${m.toUpperCase()}</span> <code>${esc(p)}</code> — ${esc(op.summary)}</summary>` +
          `${op.description ? `<p>${esc(op.description)}</p>` : ''}<p>${params}</p>${corpo ? `<h4>Corpo</h4>${corpo}` : ''}<h4>Respostas</h4><ul>${respostas}</ul><h4>Autorização</h4>${auth}</details>`,
      );
    }
  }
  const info = doc.info as {
    title: string;
    version: string;
    description: string;
  };
  const secoes = [...porTag]
    .map(
      ([t, ops]) =>
        `<section><h2 id="tag-${esc(t)}">${esc(t)}</h2>${ops.join('')}</section>`,
    )
    .join('');
  const indice = [...porTag.keys()]
    .map((t) => `<a href="#tag-${esc(t)}">${esc(t)}</a>`)
    .join(' · ');
  const esq = Object.entries(schemas)
    .map(
      ([k, v]) =>
        `<details id="schema-${esc(k)}"><summary><code>${esc(k)}</code></summary><pre>${esc(JSON.stringify(v, null, 2))}</pre></details>`,
    )
    .join('');
  return `<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${esc(info.title)}</title>
<style>body{font:15px/1.5 system-ui,sans-serif;max-width:1100px;margin:auto;padding:16px;color:#1b1b1b;background:#fff}code,pre{font-family:ui-monospace,monospace}pre{background:#f4f4f4;padding:8px;overflow:auto;font-size:12px}details{border:1px solid #ddd;border-radius:6px;margin:6px 0;padding:6px 10px}summary{cursor:pointer}.m{display:inline-block;min-width:56px;font-weight:700;font-size:12px}.get{color:#0a6}.post{color:#06c}.patch,.put{color:#a60}.delete{color:#c22}@media (prefers-color-scheme:dark){body{background:#151515;color:#eee}pre{background:#222}details{border-color:#333}}</style></head>
<body><h1>${esc(info.title)} <small>v${esc(info.version)}</small></h1><p>${esc(info.description)}</p><p>Base: <code>/platform/api/v1</code>. Gerado do código; a fonte é <code>packages/api-contracts/openapi/platform-api.v1.yaml</code>.</p><nav>${indice}</nav>${secoes}<section><h2>Schemas</h2>${esq}</section></body></html>
`;
}
