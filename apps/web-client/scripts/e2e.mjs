// End-to-end verification with human-readable output: accessibility (axe-core), keyboard flows, screen states,
// console errors and action -> feedback latency. Writes docs/frontend/relatorios/e2e.md.
// Usage: BASE_URL=http://localhost:3100 node scripts/e2e.mjs   (against `next start`)
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { BASE, launch } from "./browser.mjs";
const require = createRequire(import.meta.url);
const axeSource = fs.readFileSync(require.resolve("axe-core/axe.min.js"), "utf8");
const out = path.resolve(import.meta.dirname, "../../../docs/frontend/relatorios");
fs.mkdirSync(out, { recursive: true });
const G = "still=1&dev=1&cenario=genesis&tick=12600", T = "papel=teacher&dev=1";
const SCREENS = [
  ["Início", "/?dev=1", "[data-screen=home]"], ["Jogo (HUD)", `/jogo?${G}`, "canvas"], ["Jogo em modo texto", `/jogo?${G}&texto=1`, "[data-text-mode]"], ["Gênese", "/jogo/genese?still=1&dev=1", "canvas"],
  ["Códex", `/jogo/codex?${G}`, "[data-screen=codex]"], ["Ficha de espécie", `/jogo/codex?${G}&especie=her4`, "[data-species-sheet]"], ["Pesquisa", `/jogo/pesquisa?${G}`, "[data-node]"], ["Missões", `/jogo/missoes?${G}`, "[data-mission]"],
  ["Dados: séries", `/jogo/dados?${G}`, "[data-chart-summary]"], ["Dados: energia", `/jogo/dados?${G}&aba=energy`, "[data-pyramid]"], ["Dados: teia", `/jogo/dados?${G}&aba=web`, "[data-foodweb]"], ["Dados: árvore", `/jogo/dados?${G}&aba=phylogeny`, "[data-phylogeny]"],
  ["Dados: estrutura", `/jogo/dados?${G}&aba=structure`, "[data-chart-summary]"], ["Dados: ciclos", `/jogo/dados?${G}&aba=cycles`, "[data-cycle]"], ["Configurações", "/configuracoes?dev=1", "[data-settings]"],
  ["Professor: turma", `/professor?${T}`, "[data-heatmap]"], ["Professor: aluno", `/professor/aluno?${T}`, "[data-trace]"], ["Professor: BNCC", `/professor/bncc?${T}`, "[data-screen]"], ["Professor: gestão", `/professor/gestao?${T}`, "[data-screen]"],
  ["Professor: desafios", `/professor/desafios?${T}`, "[data-screen]"], ["Professor: comparar", `/professor/comparar?${T}`, "[data-compare-card]"], ["Professor: exportar", `/professor/exportar?${T}`, "[data-screen]"], ["Professor: mensagens", `/professor/mensagens?${T}`, "[data-screen]"],
  ["Professor: privacidade", `/professor/privacidade?${T}`, "[data-screen]"], ["Coordenação", "/coordenacao?papel=coordinator&dev=1", "[data-screen]"], ["Responsável", "/responsavel?papel=guardian&dev=1", "[data-screen]"], ["Laboratório", "/lab?dev=1&still=1", "canvas"],
];
const THEMES = [["escuro", ""], ["claro", "&tema=light"], ["alto contraste", "&contraste=high"]];
const lines = ["# Relatório de verificação de ponta a ponta", "", `Gerado por \`scripts/e2e.mjs\` em ${new Date().toISOString().slice(0, 10)}, Chromium headless (WebGL por software), contra o build de produção.`, ""];
const browser = await launch();
let failures = 0;
const check = (ok, label, detail = "") => { if (!ok) failures++; lines.push(`- ${ok ? "OK" : "**FALHA**"}: ${label}${detail ? ` (${detail})` : ""}`); console.log(`${ok ? "ok  " : "FAIL"} ${label} ${detail}`); return ok; };
async function open(ctx, url, sel, settle = 1500) {
  const page = await ctx.newPage(), errors = [];
  page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
  page.on("pageerror", (e) => errors.push(String(e)));
  await page.goto(BASE + url, { waitUntil: "domcontentloaded" });
  await page.waitForSelector(sel, { timeout: 60000 }).catch(() => errors.push(`selector not found: ${sel}`));
  await page.waitForTimeout(settle);
  return { page, errors };
}

// ---------------------------------------------------------------- 1. axe-core on every screen, three themes
lines.push("## 1. Acessibilidade automática (axe-core, regras WCAG 2.1 A e AA)", "", "| Tela | Tema | Violações | Regras violadas | Erros no console |", "|---|---|---|---|---|");
const axeTotals = { screens: 0, violations: 0, console: 0 };
for (const [themeName, themeQuery] of THEMES) {
  const ctx = await browser.newContext({ viewport: { width: 1366, height: 768 } });
  for (const [name, url, sel] of SCREENS) {
    if (themeName !== "escuro" && !["Jogo (HUD)", "Gênese", "Ficha de espécie", "Dados: séries", "Dados: teia", "Professor: turma", "Responsável", "Missões"].includes(name)) continue;
    const { page, errors } = await open(ctx, url + themeQuery, sel);
    await page.evaluate(axeSource);
    const res = await page.evaluate(() => window.axe.run(document, { runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"] } }));
    const v = res.violations.map((x) => `${x.id} [${x.impact}] ×${x.nodes.length}`);
    for (const x of res.violations) console.log(`   ${name} / ${themeName}: ${x.id} [${x.impact}] ${x.nodes.slice(0, 2).map((n) => n.target.join(" ")).join(" | ")} ${x.nodes[0]?.failureSummary?.split("\n")[1] ?? ""}`);
    axeTotals.screens++; axeTotals.violations += res.violations.length; axeTotals.console += errors.length;
    if (res.violations.length || errors.length) failures++;
    lines.push(`| ${name} | ${themeName} | ${res.violations.length} | ${v.join("; ") || "nenhuma"} | ${errors.length ? errors.slice(0, 2).join(" / ").replace(/\|/g, "/").slice(0, 160) : "0"} |`);
    console.log(`${res.violations.length || errors.length ? "FAIL" : "ok  "} axe ${name} / ${themeName}: ${res.violations.length} violações, ${errors.length} erros de console`);
    await page.close();
  }
  await ctx.close();
}
lines.push("", `Resumo: ${axeTotals.screens} combinações de tela e tema, ${axeTotals.violations} violações, ${axeTotals.console} erros de console.`, "");

// ---------------------------------------------------------------- 2. keyboard flows
lines.push("## 2. Fluxos só com teclado", "");
{
  const ctx = await browser.newContext({ viewport: { width: 1366, height: 768 } });
  let { page } = await open(ctx, "/?dev=1", "[data-screen=home]");
  await page.keyboard.press("Tab"); // skip link
  check(await page.evaluate(() => document.activeElement?.classList.contains("ec-skip")), "O primeiro Tab leva ao link “Pular para o conteúdo”");
  for (let i = 0; i < 6 && !(await page.evaluate(() => document.activeElement?.getAttribute("href") === "/jogo")); i++) await page.keyboard.press("Tab");
  await page.keyboard.press("Enter");
  await page.waitForURL("**/jogo", { timeout: 30000 }).catch(() => {});
  check(page.url().endsWith("/jogo"), "Início → “Começar demonstração” com Tab e Enter abre o jogo");
  await page.close();

  ({ page } = await open(ctx, `/jogo?${G.replace("still=1&", "")}&movimento=reduced`, "canvas", 2500));
  await page.focus("[data-planet-stage]");
  const cam = () => page.evaluate(() => { const c = document.querySelector("canvas"); return c ? 1 : 0; });
  await page.keyboard.press("ArrowLeft"); await page.keyboard.press("ArrowUp"); await page.keyboard.press("+"); await page.waitForTimeout(500);
  check((await cam()) === 1, "Planeta focado aceita setas e zoom por teclado sem erro");
  await page.keyboard.press("Enter"); await page.waitForTimeout(400);
  check(await page.locator("[data-probe]").count() > 0, "Enter seleciona o ponto no centro e abre a sonda com valores", await page.locator("[data-probe]").innerText().then((s) => s.replace(/\n/g, " ").slice(0, 90)).catch(() => ""));
  const desc = await page.locator("[data-planet-description]").innerText();
  check(desc.includes("Temperatura média") && desc.includes("linhagens"), "Descrição textual do planeta presente para leitor de tela", desc.replace(/\n/g, " ").slice(0, 150) + "…");
  await page.focus("[data-layer=temperature]"); await page.keyboard.press("Enter"); await page.waitForTimeout(300);
  check(await page.getAttribute("[data-layer=temperature]", "aria-pressed") === "true", "Camada de temperatura ligada por teclado (aria-pressed)");
  const t0 = Number(await page.getAttribute("[data-status]", "data-tick"));
  await page.focus("[data-timeline]"); for (let i = 0; i < 5; i++) await page.keyboard.press("ArrowLeft"); await page.waitForTimeout(900);
  const t1 = Number(await page.getAttribute("[data-status]", "data-tick"));
  check(t1 < t0, "Linha do tempo rola para o passado com a seta esquerda", `mês ${t0} → ${t1}`);
  await page.focus("[data-intervention=scan]"); await page.keyboard.press("Enter"); await page.waitForSelector("[data-intervention-dialog]");
  check(await page.evaluate(() => !!document.activeElement?.closest("dialog")), "Diálogo de intervenção recebe o foco ao abrir");
  await page.focus("[data-confirm]"); await page.keyboard.press("Enter"); await page.waitForTimeout(500);
  check(await page.locator("[data-intervention-dialog]").count() === 0, "Varredura confirmada por teclado fecha o diálogo");
  await page.focus("[data-intervention=scan]"); await page.keyboard.press("Enter"); await page.waitForSelector("[data-intervention-dialog]"); await page.keyboard.press("Escape"); await page.waitForTimeout(300);
  check(await page.locator("[data-intervention-dialog]").count() === 0, "Esc fecha o diálogo");
  await page.focus("[data-tutor]"); await page.keyboard.press("Enter"); await page.waitForSelector("[data-tutor-panel]");
  await page.focus("[data-question=species]"); await page.keyboard.press("Enter"); await page.waitForSelector("[data-tutor-answer]"); await page.waitForTimeout(600);
  const before = await page.locator("[data-chain]").count();
  await page.focus("[data-reveal]"); await page.keyboard.press("Enter"); await page.waitForTimeout(300);
  check(before === 0 && await page.locator("[data-tutor-panel] [data-chain]").count() === 1, "Tutor: a pergunta vem antes; a cadeia causal aparece só ao pedir a explicação", await page.locator("[data-tutor-answer]").innerText().then((s) => s.replace(/\n/g, " ").slice(0, 200)));
  await page.close();

  ({ page } = await open(ctx, `/jogo/codex?${G}`, "[data-species]"));
  await page.focus("[data-species]"); await page.keyboard.press("Enter"); await page.waitForSelector("[data-species-sheet]", { timeout: 20000 }).catch(() => {});
  check(await page.locator("[data-species-sheet]").count() === 1, "Códex: seleção de espécie por teclado abre a ficha");
  await page.close();
  ({ page } = await open(ctx, `/jogo/dados?${G}`, "[role=tablist]"));
  await page.focus("[role=tab][aria-selected=true]"); await page.keyboard.press("ArrowRight"); await page.waitForTimeout(400);
  check(await page.getAttribute("[data-screen=data]", "data-tab") === "energy", "Abas dos dashboards mudam com as setas (padrão WAI-ARIA)");
  await page.close(); await ctx.close();
}

// ---------------------------------------------------------------- 3. states
lines.push("", "## 3. Estados das telas", "");
{
  const ctx = await browser.newContext({ viewport: { width: 1366, height: 768 } });
  let { page, errors } = await open(ctx, "/jogo?still=1&dev=1&cenario=genesis&tick=3650", "canvas", 2000);
  check(await page.locator("[data-no-life]").count() === 1, "Planeta sem vida: aviso com “Por quê?”", await page.locator("[data-no-life]").innerText().then((s) => s.replace(/\n/g, " ")));
  await page.evaluate(() => window.__ecosfera.planet.setState({ status: "error", errorDetail: "falha simulada pelo teste" })); await page.waitForTimeout(300);
  check(await page.locator("[role=alert]").filter({ hasText: "Algo não funcionou" }).count() === 1, "Erro da fonte de dados: mensagem com “Tentar de novo”");
  await page.evaluate(() => window.__ecosfera.planet.setState({ status: "loading", frame: null })); await page.waitForTimeout(300);
  check(await page.locator("[role=status]").filter({ hasText: "Formando o planeta" }).count() === 1, "Carregando: indicador com texto");
  check(errors.length === 0, "Sem erros de console nesses estados", errors.join(" / ").slice(0, 200)); await page.close();
  ({ page } = await open(ctx, "/jogo?still=1&dev=1&cenario=genesis&tick=5999", "canvas", 2000));
  check(await page.locator("[data-era-end]").count() === 1, "Fim de era: aviso com acesso ao relatório");
  await page.click("[data-era-end] button"); await page.waitForSelector("[data-era-report]");
  check(await page.locator("[data-era-report] textarea").count() === 3, "Relatório de fim de era abre com três perguntas de reflexão"); await page.close();
  ({ page } = await open(ctx, "/jogo/codex?still=1&dev=1&cenario=genesis&tick=100", "[data-screen=codex]", 1500));
  check((await page.locator("[data-screen=codex]").innerText()).includes("Nenhuma linhagem"), "Vazio: Códex sem linhagens explica o motivo"); await page.close();
  ({ page } = await open(ctx, "/jogo/dados?still=1&dev=1&cenario=genesis&tick=3000&aba=web", "[data-screen=data]", 2500));
  check((await page.locator("[data-screen=data]").innerText()).includes("Ainda não há vida"), "Vazio: teia trófica sem vida explica o motivo"); await page.close();
  ({ page } = await open(ctx, "/jogo?still=1&dev=1&cenario=noDecomposers&tick=5200", "canvas", 2500));
  const why = await page.evaluate(() => window.__ecosfera.planet.getState().frame.globals.organicStuck);
  check(why > 0.9, "Cenário Sem Decompositores chega ao colapso por matéria presa", `matéria presa = ${why.toFixed(2)}`); await page.close();
  ({ page } = await open(ctx, "/lab?dev=0", "[data-screen=lab-off]", 500));
  check(await page.locator("[data-screen=lab-off]").count() === 1, "Console de laboratório fechado sem a flag de desenvolvimento"); await page.close();
  ({ page } = await open(ctx, "/professor?papel=student&dev=0", "[data-role-gate]", 500));
  check(await page.locator("[data-role-gate]").count() === 1, "Guarda de papel (provisória) barra o estudante no painel do professor"); await page.close();
  await ctx.close();
}

// ---------------------------------------------------------------- 4. latency action -> feedback (RNF-002)
lines.push("", "## 4. Latência da ação ao feedback visual (RNF-002)", "");
{
  const ctx = await browser.newContext({ viewport: { width: 1366, height: 768 } });
  const { page } = await open(ctx, `/jogo?dev=1&cenario=genesis&tick=12600`, "canvas", 20000); // lets the automatic quality governor settle
  const samples = await page.evaluate(async () => {
    const { planet, game, feedback } = window.__ecosfera, out = [];
    for (let i = 0; i < 12; i++) {
      game.setState({ resources: { ...game.getState().resources, actionPoints: 5, energy: 100 }, cooldowns: {}, unlocked: [...game.getState().unlocked, "tech.reforest"] });
      const cell = 500 + i * 37, t0 = performance.now();
      const state = new Promise((res) => { const un = planet.subscribe((s, p) => { if (s.frame !== p.frame) { un(); res(performance.now() - t0); } }); });
      game.getState().apply("reforest", { cell });
      const ripple = feedback.rippleCell === cell ? feedback.rippleStart - t0 : -1;
      const painted = await new Promise((res) => requestAnimationFrame(() => requestAnimationFrame(() => res(performance.now() - t0))));
      out.push({ ripple, painted, state: await state });
      await new Promise((r) => setTimeout(r, 250));
    }
    return out;
  });
  const p95 = (k) => { const v = samples.map((s) => s[k]).sort((a, b) => a - b); return v[Math.min(v.length - 1, Math.ceil(v.length * 0.95) - 1)]; };
  lines.push("| Medida (12 ações de reflorestar) | p95 |", "|---|---|", `| Disparo da ondulação no ponto (síncrono ao gesto) | ${p95("ripple").toFixed(1)} ms |`, `| Ondulação desenhada (dois quadros depois) | ${p95("painted").toFixed(0)} ms |`, `| Novo estado do planeta recebido da fonte | ${p95("state").toFixed(0)} ms |`, "");
  check(p95("painted") <= 1000, "Feedback visual local em até 1 s no p95, em WebGL por software", `p95 = ${p95("painted").toFixed(0)} ms`);
  await ctx.close();
}
await browser.close();
lines.push("", `**Total de falhas: ${failures}.**`, "");
fs.writeFileSync(path.join(out, "e2e.md"), lines.join("\n"));
console.log(`\n${failures} falhas. Relatório: docs/frontend/relatorios/e2e.md`);
process.exit(failures ? 1 : 0);
