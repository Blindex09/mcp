// Teste de fumaca: abre uma pagina no navegador, liga o NVDA portatil do Guidepup e grava o que ele FALA.
// Sem modelo de IA: so teclas (Tab e navegacao do NVDA) e o log de fala real.
// Uso: node spike.mjs <url> <rotulo> [tabs=15] [setas=15]
import { mkdirSync, writeFileSync } from "node:fs";
import { nvda, windowsActivate } from "@guidepup/guidepup";
import { chromium } from "playwright";

const [url, label = "pagina", tabsArg = "15", nextArg = "15"] = process.argv.slice(2);
if (!url) {
  console.error("uso: node spike.mjs <url> <rotulo> [tabs] [setas]");
  process.exit(2);
}
const tabs = Number(tabsArg);
const nexts = Number(nextArg);
const pause = (ms) => new Promise((r) => setTimeout(r, ms));
// bringToFront do Playwright so troca a aba dentro do navegador; quem da o foco do sistema a janela e' o Windows.
const focarJanela = async (page) => {
  await page.bringToFront();
  const parte = ((await page.title()).split(/[^ -~]/)[0] || "Edge").trim();
  await windowsActivate("msedge.exe", parte);
  await pause(1200);
};

// Todas as frases que o NVDA falou desde o passo anterior (a "ultima frase" perde as rapidas), e zera o log.
const falasDoPasso = async () => {
  const frases = await nvda.spokenPhraseLog();
  await nvda.clearSpokenPhraseLog();
  return frases.filter(Boolean).join(" | ") || "(nada falado)";
};

mkdirSync("out", { recursive: true });
const result = { url, label, startedAt: new Date().toISOString(), tab: [], browse: [], error: null };
let browser;
let nvdaStarted = false;

try {
  browser = await chromium.launch({ channel: "msedge", headless: false, args: ["--force-renderer-accessibility"] });
  const page = await browser.newPage();
  await page.goto(url, { waitUntil: "load" });

  await nvda.start();
  nvdaStarted = true;
  await pause(2500);
  await focarJanela(page);
  await nvda.clearSpokenPhraseLog();

  // 1) como um usuario de teclado: Tab, e o que o NVDA fala a cada parada
  for (let i = 1; i <= tabs; i++) {
    await nvda.press("Tab");
    await pause(900);
    result.tab.push({ passo: i, fala: await falasDoPasso() });
  }

  // 2) como um usuario de leitor de tela lendo a pagina (modo navegacao): item a item
  await page.reload({ waitUntil: "load" });
  await focarJanela(page);
  await nvda.press("Control+Home"); // modo leitura: comeca do topo do documento
  await pause(1000);
  await nvda.clearSpokenPhraseLog();
  for (let i = 1; i <= nexts; i++) {
    await nvda.next();
    await pause(700);
    result.browse.push({ passo: i, fala: await falasDoPasso() });
  }
} catch (e) {
  result.error = String(e?.message ?? e);
} finally {
  if (nvdaStarted) {
    try {
      await nvda.stop();
    } catch (e) {
      result.stopError = String(e?.message ?? e);
    }
  }
  if (browser) await browser.close();
  result.finishedAt = new Date().toISOString();
  writeFileSync(`out/${label}.json`, JSON.stringify(result, null, 2));
  const linhas = [
    `# ${label} - ${url}`,
    result.error ? `ERRO: ${result.error}` : "",
    "## Tab",
    ...result.tab.map((x) => `${x.passo}. ${x.fala}`),
    "## Navegacao (modo leitura)",
    ...result.browse.map((x) => `${x.passo}. ${x.fala}`),
  ].filter(Boolean);
  writeFileSync(`out/${label}.txt`, linhas.join("\n"));
  console.log(linhas.join("\n"));
}
