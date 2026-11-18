// Percorre uma pagina com o NVDA real e devolve o que ele FALA, em texto. Sem modelo de IA.
// As dependencias (NVDA, navegador, janela) entram por parametro: o teste automatico usa simulacoes e nunca liga o NVDA.
import { criarControleDeFoco, esperarFalaAssentar } from "./focus.mjs";
import { maximizarJanela } from "./window.mjs";
export { esperarFalaAssentar } from "./focus.mjs";

export const ATALHOS_NAVEGACAO = {
  titulos: { tecla: "H", comando: "moveToNextHeading", limite: 50 },
  marcos: { tecla: "D", comando: "moveToNextLandmark", limite: 30 },
  links: { tecla: "K", comando: "moveToNextLink", limite: 60 },
  campos: { tecla: "F", comando: "moveToNextFormField", limite: 30, sairDeFocoEmEdicao: true },
  botoes: { tecla: "B", comando: "moveToNextButton", limite: 30 },
  listas: { tecla: "L", comando: "moveToNextList", limite: 30 },
  tabelas: { tecla: "T", comando: "moveToNextTable", limite: 20 },
  graficos: { tecla: "G", comando: "moveToNextGraphic", limite: 30 },
};

export const LIMITES = {
  tabs: 60,
  leituras: 80,
  teclas: 60,
  atalhos: Object.fromEntries(Object.entries(ATALHOS_NAVEGACAO).map(([k, v]) => [k, v.limite])),
};

// Mapeia teclas de navegacao rapida do modo de navegacao do NVDA para os comandos oficiais do Guidepup
// (em @guidepup/guidepup, parseKey("H") vira Shift+H; usar keyboardCommands envia a tecla exata sem Shift indevido).
// Fim de lista = a mesma fala este numero de vezes SEGUIDAS depois da primeira (3 falas iguais no total). Uma unica repeticao
// acontece em listas legitimas (varios "Leia mais, link" seguidos) e cortaria a leitura antes do fim.
export const REPETICOES_PARA_FIM = 2;

export const COMANDOS_TECLA_NVDA = {
  h: "moveToNextHeading",
  "shift+h": "moveToPreviousHeading",
  "shift-h": "moveToPreviousHeading",
  1: "moveToNextHeadingLevel1",
  "shift+1": "moveToPreviousHeadingLevel1",
  "shift-1": "moveToPreviousHeadingLevel1",
  2: "moveToNextHeadingLevel2",
  "shift+2": "moveToPreviousHeadingLevel2",
  "shift-2": "moveToPreviousHeadingLevel2",
  3: "moveToNextHeadingLevel3",
  "shift+3": "moveToPreviousHeadingLevel3",
  "shift-3": "moveToPreviousHeadingLevel3",
  4: "moveToNextHeadingLevel4",
  "shift+4": "moveToPreviousHeadingLevel4",
  "shift-4": "moveToPreviousHeadingLevel4",
  5: "moveToNextHeadingLevel5",
  "shift+5": "moveToPreviousHeadingLevel5",
  "shift-5": "moveToPreviousHeadingLevel5",
  6: "moveToNextHeadingLevel6",
  "shift+6": "moveToPreviousHeadingLevel6",
  "shift-6": "moveToPreviousHeadingLevel6",
  d: "moveToNextLandmark",
  "shift+d": "moveToPreviousLandmark",
  "shift-d": "moveToPreviousLandmark",
  k: "moveToNextLink",
  "shift+k": "moveToPreviousLink",
  "shift-k": "moveToPreviousLink",
  f: "moveToNextFormField",
  "shift+f": "moveToPreviousFormField",
  "shift-f": "moveToPreviousFormField",
  e: "moveToNextEditField",
  "shift+e": "moveToPreviousEditField",
  "shift-e": "moveToPreviousEditField",
  b: "moveToNextButton",
  "shift+b": "moveToPreviousButton",
  "shift-b": "moveToPreviousButton",
  l: "moveToNextList",
  "shift+l": "moveToPreviousList",
  "shift-l": "moveToPreviousList",
  i: "moveToNextListItem",
  "shift+i": "moveToPreviousListItem",
  "shift-i": "moveToPreviousListItem",
  t: "moveToNextTable",
  "shift+t": "moveToPreviousTable",
  "shift-t": "moveToPreviousTable",
  g: "moveToNextGraphic",
  "shift+g": "moveToPreviousGraphic",
  "shift-g": "moveToPreviousGraphic",
  x: "moveToNextCheckbox",
  "shift+x": "moveToPreviousCheckbox",
  "shift-x": "moveToPreviousCheckbox",
  c: "moveToNextComboBox",
  "shift+c": "moveToPreviousComboBox",
  "shift-c": "moveToPreviousComboBox",
  r: "moveToNextRadioButton",
  "shift+r": "moveToPreviousRadioButton",
  "shift-r": "moveToPreviousRadioButton",
  q: "moveToNextBlockQuote",
  "shift+q": "moveToPreviousBlockQuote",
  "shift-q": "moveToPreviousBlockQuote",
  s: "moveToNextSeparator",
  "shift+s": "moveToPreviousSeparator",
  "shift-s": "moveToPreviousSeparator",
  m: "moveToNextFrame",
  "shift+m": "moveToPreviousFrame",
  "shift-m": "moveToPreviousFrame",
  o: "moveToNextEmbeddedObject",
  "shift+o": "moveToPreviousEmbeddedObject",
  "shift-o": "moveToPreviousEmbeddedObject",
  u: "moveToNextUnvisitedLink",
  "shift+u": "moveToPreviousUnvisitedLink",
  "shift-u": "moveToPreviousUnvisitedLink",
  v: "moveToNextVisitedLink",
  "shift+v": "moveToPreviousVisitedLink",
  "shift-v": "moveToPreviousVisitedLink",
  n: "moveToNextNonLinkedText",
  "shift+n": "moveToPreviousNonLinkedText",
  "shift-n": "moveToPreviousNonLinkedText",
  a: "moveToNextAnnotation",
  "shift+a": "moveToPreviousAnnotation",
  "shift-a": "moveToPreviousAnnotation",
  w: "moveToNextSpellingError",
  "shift+w": "moveToPreviousSpellingError",
  "shift-w": "moveToPreviousSpellingError",
  // Celulas de tabela: mapeadas, mas NAO confirmadas no NVDA real da VM (o Edge as recebeu e o foco saiu da pagina). Prefira T + setas.
  "ctrl+alt+down": "moveToNextRow",
  "ctrl+alt+arrowdown": "moveToNextRow",
  "ctrl+alt+seta_baixo": "moveToNextRow",
  "control+alt+arrowdown": "moveToNextRow",
  "ctrl+alt+up": "moveToPreviousRow",
  "ctrl+alt+arrowup": "moveToPreviousRow",
  "ctrl+alt+seta_cima": "moveToPreviousRow",
  "control+alt+arrowup": "moveToPreviousRow",
  "ctrl+alt+right": "moveToNextColumn",
  "ctrl+alt+arrowright": "moveToNextColumn",
  "ctrl+alt+seta_direita": "moveToNextColumn",
  "control+alt+arrowright": "moveToNextColumn",
  "ctrl+alt+left": "moveToPreviousColumn",
  "ctrl+alt+arrowleft": "moveToPreviousColumn",
  "ctrl+alt+seta_esquerda": "moveToPreviousColumn",
  "control+alt+arrowleft": "moveToPreviousColumn",
  ",": "movePastEndOfContainer",
  "shift+,": "moveToStartOfContainer",
  "shift-,": "moveToStartOfContainer",
  escape: "exitFocusMode",
  "nvda+space": "toggleBetweenBrowseAndFocusMode",
  "nvda+espaco": "toggleBetweenBrowseAndFocusMode",
  "nvda+espaço": "toggleBetweenBrowseAndFocusMode",
  "nvda-space bar": "toggleBetweenBrowseAndFocusMode",
};

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

export function validarAtalhos(atalhos) {
  if (atalhos === undefined || atalhos === null) return {};
  if (typeof atalhos !== "object" || Array.isArray(atalhos)) {
    throw new Error("atalhos deve ser um objeto com contagens por categoria");
  }
  const limpo = {};
  for (const [chave, valor] of Object.entries(atalhos)) {
    const config = ATALHOS_NAVEGACAO[chave];
    if (!config) {
      throw new Error(`atalho desconhecido: ${chave} (use ${Object.keys(ATALHOS_NAVEGACAO).join(", ")})`);
    }
    if (!Number.isInteger(valor) || valor < 0 || valor > config.limite) {
      throw new Error(`atalhos.${chave} deve ser um inteiro de 0 a ${config.limite}`);
    }
    if (valor > 0) limpo[chave] = valor;
  }
  return limpo;
}

export function validarTeclas(teclas) {
  if (teclas === undefined || teclas === null) return [];
  if (!Array.isArray(teclas) || teclas.length > LIMITES.teclas) {
    throw new Error(`teclas deve ser uma lista de ate ${LIMITES.teclas} itens`);
  }
  return teclas.map((item) => {
    if (typeof item !== "string" || !item.trim() || item.trim().length > 40) {
      throw new Error("cada tecla deve ser um texto nao vazio de ate 40 caracteres");
    }
    return item.trim();
  });
}

export const TECLAS_ESPECIAIS = {
  seta_baixo: "ArrowDown",
  "seta-baixo": "ArrowDown",
  "seta para baixo": "ArrowDown",
  "seta baixo": "ArrowDown",
  down: "ArrowDown",
  arrowdown: "ArrowDown",
  seta_cima: "ArrowUp",
  "seta-cima": "ArrowUp",
  "seta para cima": "ArrowUp",
  "seta cima": "ArrowUp",
  up: "ArrowUp",
  arrowup: "ArrowUp",
  seta_direita: "ArrowRight",
  "seta-direita": "ArrowRight",
  "seta para direita": "ArrowRight",
  "seta direita": "ArrowRight",
  right: "ArrowRight",
  arrowright: "ArrowRight",
  seta_esquerda: "ArrowLeft",
  "seta-esquerda": "ArrowLeft",
  "seta para esquerda": "ArrowLeft",
  "seta esquerda": "ArrowLeft",
  left: "ArrowLeft",
  arrowleft: "ArrowLeft",
  enter: "Enter",
  retorno: "Enter",
  espaco: "Space",
  espaço: "Space",
  space: "Space",
  esc: "Escape",
  escape: "Escape",
  tab: "Tab",
  home: "Home",
  end: "End",
  pageup: "PageUp",
  page_up: "PageUp",
  pagedown: "PageDown",
  page_down: "PageDown",
  "alt+seta_baixo": "Alt+ArrowDown",
  "alt+seta-baixo": "Alt+ArrowDown",
  "alt+down": "Alt+ArrowDown",
  "alt+seta_cima": "Alt+ArrowUp",
  "alt+seta-cima": "Alt+ArrowUp",
  "alt+up": "Alt+ArrowUp",
};

export async function executarTeclaNvda(nvda, tecla, comandoExplicito = null) {
  const limpa = String(tecla).trim().toLowerCase();
  const nomeComando = comandoExplicito ?? COMANDOS_TECLA_NVDA[limpa];
  if (nomeComando && nvda.keyboardCommands?.[nomeComando] && typeof nvda.perform === "function") {
    await nvda.perform(nvda.keyboardCommands[nomeComando]);
    return;
  }
  const teclaReal = TECLAS_ESPECIAIS[limpa] ?? tecla;
  await nvda.press(teclaReal);
}

const dormir = (ms) => new Promise((r) => setTimeout(r, ms));

export async function carregarDependencias() {
  const { nvda, windowsActivate, NVDAKeyCodeCommands, WindowsKeyCodes, WindowsModifiers } = await import("@guidepup/guidepup");
  const { chromium } = await import("playwright");
  return { nvda, windowsActivate, NVDAKeyCodeCommands, WindowsKeyCodes, WindowsModifiers, chromium, pause: dormir };
}

async function falasDoPasso(nvda, pause) {
  await esperarFalaAssentar(nvda, pause);
  const frases = await nvda.spokenPhraseLog();
  await nvda.clearSpokenPhraseLog();
  return frases.filter(Boolean).join(" | ") || "(nada falado)";
}

async function voltarAoTopoModoNavegacao(nvda, page, foco, pause) {
  await foco.exigir();
  if (nvda.keyboardCommands?.exitFocusMode && typeof nvda.perform === "function") {
    await nvda.perform(nvda.keyboardCommands.exitFocusMode);
  }
  await page.evaluate(() => {
    if (typeof document === "undefined") return;
    const el = document.activeElement;
    if (el && el !== document.body && typeof el.blur === "function") el.blur();
    document.body?.focus?.();
    if (typeof window !== "undefined" && typeof window.scrollTo === "function") window.scrollTo(0, 0);
  });
  await nvda.press("Control+Home");
  await pause(500);
  await nvda.clearSpokenPhraseLog();
}

async function sairDeModoFocoSeEmCampoEditavel(nvda, page, pause) {
  const emEdicao = await page.evaluate(() => {
    if (typeof document === "undefined") return false;
    const el = document.activeElement;
    if (!el) return false;
    const tag = (el.tagName || "").toUpperCase();
    return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || Boolean(el.isContentEditable);
  });
  if (emEdicao) {
    await executarTeclaNvda(nvda, "Escape", "exitFocusMode");
    await pause(150);
    await nvda.clearSpokenPhraseLog();
  }
}

export async function percorrer(
  { url, tabs = 15, leituras = 20, atalhos, teclas, silencio } = {},
  deps,
  aoAvancar = () => {},
) {
  const alvo = validarUrl(url);
  if (!Number.isInteger(tabs) || tabs < 0 || tabs > LIMITES.tabs) throw new Error(`tabs deve ser um inteiro de 0 a ${LIMITES.tabs}`);
  if (!Number.isInteger(leituras) || leituras < 0 || leituras > LIMITES.leituras) {
    throw new Error(`leituras deve ser um inteiro de 0 a ${LIMITES.leituras}`);
  }
  const atalhosValidos = validarAtalhos(atalhos);
  const teclasValidas = validarTeclas(teclas);
  const settings = settingsDeSilencio(silencio);
  const { nvda, chromium, pause } = deps;

  const resultado = {
    url: alvo,
    silencio: silencio ?? null,
    iniciado: new Date().toISOString(),
    tab: [],
    leitura: [],
    atalhos: {},
    teclas: [],
    erro: null,
  };
  let passosConcluidos = 0;
  const registrarAvanco = () => {
    passosConcluidos += 1;
    aoAvancar(passosConcluidos);
  };
  let navegador;
  let nvdaLigado = false;

  try {
    navegador = await chromium.launch({
      channel: "msedge",
      headless: false,
      args: ["--force-renderer-accessibility", "--start-maximized", "--no-first-run", "--no-default-browser-check"],
    });
    const page = await navegador.newPage({ viewport: null });
    await page.goto(alvo, { waitUntil: "load" });
    const foco = criarControleDeFoco(deps, page, async () => { resultado.janela = await maximizarJanela(page); });
    resultado.foco = foco.registros;
    resultado.tituloTemporario = true;
    await nvda.start({ capture: true, ...(settings ? { settings } : {}) });
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
      registrarAvanco();
    }

    const precisaModoNavegacao =
      leituras > 0 || Object.keys(atalhosValidos).length > 0 || teclasValidas.length > 0;
    if (precisaModoNavegacao && tabs > 0) {
      await page.reload({ waitUntil: "load" });
      await foco.ativar();
    }

    // 2) como quem le a pagina com o leitor de tela (modo leitura), do topo, item a item (Seta para baixo)
    if (leituras > 0) {
      await voltarAoTopoModoNavegacao(nvda, page, foco, pause);
      for (let i = 1; i <= leituras; i++) {
        await foco.exigir();
        await nvda.next();
        const fala = await falasDoPasso(nvda, pause);
        await foco.exigir();
        resultado.leitura.push({ passo: i, fala });
        registrarAvanco();
      }
    }

    // 3) navegacao rapida por teclas de uma letra no modo de navegacao do NVDA (H, D, K, F, B, L, T, G)
    for (const [categoria, quantidade] of Object.entries(atalhosValidos)) {
      const info = ATALHOS_NAVEGACAO[categoria];
      resultado.atalhos[categoria] = [];
      await voltarAoTopoModoNavegacao(nvda, page, foco, pause);
      let anterior = null;
      let iguais = 0;
      for (let i = 1; i <= quantidade; i++) {
        await foco.exigir();
        await executarTeclaNvda(nvda, info.tecla, info.comando);
        const fala = await falasDoPasso(nvda, pause);
        await foco.exigir();
        resultado.atalhos[categoria].push({ passo: i, tecla: info.tecla, fala });
        registrarAvanco();
        // Fato objetivo, sem interpretar o texto: a mesma fala repetida REPETICOES_PARA_FIM vezes seguidas = o NVDA nao saiu do lugar (fim da lista).
        iguais = anterior !== null && fala === anterior ? iguais + 1 : 0;
        if (iguais >= REPETICOES_PARA_FIM) break;
        anterior = fala;
        if (info.sairDeFocoEmEdicao && i < quantidade) {
          await sairDeModoFocoSeEmCampoEditavel(nvda, page, pause);
        }
      }
    }

    // 4) sequencia explicita de teclas/comandos do NVDA a partir do topo em modo de navegacao
    if (teclasValidas.length > 0) {
      await voltarAoTopoModoNavegacao(nvda, page, foco, pause);
      for (let i = 0; i < teclasValidas.length; i++) {
        const tecla = teclasValidas[i];
        await foco.exigir();
        await executarTeclaNvda(nvda, tecla);
        const fala = await falasDoPasso(nvda, pause);
        await foco.exigir();
        resultado.teclas.push({ passo: i + 1, tecla, fala });
        registrarAvanco();
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
