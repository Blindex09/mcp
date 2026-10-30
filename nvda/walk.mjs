// Percorre uma pagina com o NVDA real e devolve o que ele FALA, em texto. Sem modelo de IA.
// As dependencias (NVDA, navegador, janela) entram por parametro: o teste automatico usa simulacoes e nunca liga o NVDA.
import { criarControleDeFoco, esperarFalaAssentar } from "./focus.mjs";
export { esperarFalaAssentar } from "./focus.mjs";

export const LIMITES = { tabs: 60, leituras: 80 };

export function settingsDeSilencio(silencio) {
  if (!silencio) return undefined;
  // As chaves seguem o nvda.ini do Guidepup: [speech] synth e [[oneCore]] volume (o start() mistura isto na sessao).
  if (silencio === "volume") return { speech: { oneCore: { volume: 0 } } };
  if (silencio === "sem-fala") return { speech: { synth: "silence" } };
  throw new Error('silencio invalido: use "volume" ou "sem-fala"');
}

export function validarUrl(url) {
  let u;
  try {
    u = new URL(url);
  } catch {
    throw new Error("url invalida");
  }
  if (u.protocol !== "http:" && u.protocol !== "https:") throw new Error("so URLs http:// ou https:// sao permitidas");
  return u.href;
}

const dormir = (ms) => new Promise((r) => setTimeout(r, ms));

export async function carregarDependencias() {
  const { nvda, windowsActivate } = await import("@guidepup/guidepup");
  const { chromium } = await import("playwright");
  return { nvda, windowsActivate, chromium, pause: dormir };
}

async function falasDoPasso(nvda, pause) {
  await esperarFalaAssentar(nvda, pause);
  const frases = await nvda.spokenPhraseLog();
  await nvda.clearSpokenPhraseLog();
  return frases.filter(Boolean).join(" | ") || "(nada falado)";
}

export async function percorrer({ url, tabs = 15, leituras = 20, silencio } = {}, deps, aoAvancar = () => {}) {
  const alvo = validarUrl(url);
  if (!Number.isInteger(tabs) || tabs < 0 || tabs > LIMITES.tabs) throw new Error(`tabs deve ser um inteiro de 0 a ${LIMITES.tabs}`);
  if (!Number.isInteger(leituras) || leituras < 0 || leituras > LIMITES.leituras) {
    throw new Error(`leituras deve ser um inteiro de 0 a ${LIMITES.leituras}`);
  }
  const settings = settingsDeSilencio(silencio);
  const { nvda, chromium, pause } = deps;

  const resultado = { url: alvo, silencio: silencio ?? null, iniciado: new Date().toISOString(), tab: [], leitura: [], erro: null };
  let navegador;
  let nvdaLigado = false;

  try {
    navegador = await chromium.launch({ channel: "msedge", headless: false, args: ["--force-renderer-accessibility"] });
    const page = await navegador.newPage();
    await page.goto(alvo, { waitUntil: "load" });
    const foco = criarControleDeFoco(deps, page);
    resultado.foco = foco.registros;
    resultado.tituloTemporario = true;
    await nvda.start(settings ? { settings } : undefined);
    nvdaLigado = true;
    await pause(2500);
    await foco.ativar();
    await nvda.clearSpokenPhraseLog();

    // 1) como quem usa so o teclado: Tab, e o que o NVDA fala a cada parada
    for (let i = 1; i <= tabs; i++) {
      await foco.exigir();
      await nvda.press("Tab");
      const fala = await falasDoPasso(nvda, pause);
      await foco.exigir();
      resultado.tab.push({ passo: i, fala });
      aoAvancar(resultado.tab.length + resultado.leitura.length);
    }

    // 2) como quem le a pagina com o leitor de tela (modo leitura), do topo, item a item
    if (leituras > 0) {
      await page.reload({ waitUntil: "load" });
      await foco.ativar();
      await nvda.press("Control+Home");
      await pause(1000);
      await nvda.clearSpokenPhraseLog();
      for (let i = 1; i <= leituras; i++) {
        await foco.exigir();
        await nvda.next();
        const fala = await falasDoPasso(nvda, pause);
        await foco.exigir();
        resultado.leitura.push({ passo: i, fala });
        aoAvancar(resultado.tab.length + resultado.leitura.length);
      }
    }
  } catch (e) {
    resultado.erro = String(e?.message ?? e);
  } finally {
    if (nvdaLigado) {
      try {
        await nvda.stop();
      } catch (e) {
        resultado.erroAoParar = String(e?.message ?? e);
      }
    }
    if (navegador) await navegador.close();
    resultado.terminado = new Date().toISOString();
  }
  return resultado;
}
