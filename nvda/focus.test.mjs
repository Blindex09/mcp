import assert from "node:assert/strict";
import { test } from "node:test";
import { criarControleDeFoco } from "./focus.mjs";
import { percorrer } from "./walk.mjs";

function ambiente({ ativacoesNecessarias = 1, perderNoTab = false } = {}) {
  let marcador, falas = [], ativacoes = 0, perdido = false;
  const eventos = [];
  const nvda = {
    keyboardCommands: { reportTitle: "titulo" },
    start: async () => {}, stop: async () => eventos.push("parou"),
    clearSpokenPhraseLog: async () => { falas = []; },
    spokenPhraseLog: async () => falas,
    perform: async () => { falas = [ativacoes >= ativacoesNecessarias && !perdido ? marcador : "Outro aplicativo privado"]; },
    press: async (tecla) => {
      eventos.push(tecla);
      if (tecla === "Tab") { perdido = perderNoTab; falas = ["conteudo nao confirmado"]; }
    },
    next: async () => { eventos.push("leitura"); },
  };
  const page = {
    goto: async () => {}, reload: async () => {}, bringToFront: async () => {},
    context: () => ({ newCDPSession: async () => ({ send: async (method) => method === "Browser.getWindowForTarget" ? { windowId: 1 } : { bounds: { windowState: "maximized" } }, detach: async () => {} }) }), evaluate: async (_, id) => { if (id) marcador = id; else return { width: 1920, height: 980, deviceScaleFactor: 1 }; },
    title: async () => "Titulo com ' aspas e comandos $(nao executar)",
  };
  const deps = {
    nvda, pause: async () => {},
    windowsActivate: async (processo, titulo) => {
      assert.equal(processo, "msedge");
      assert.match(titulo, /^A11yNvda[0-9a-f]{32}$/);
      ativacoes++;
    },
    chromium: { launch: async () => ({ newPage: async () => page, close: async () => eventos.push("fechou") }) },
  };
  return { page, deps, eventos, ativacoes: () => ativacoes };
}

test("foco confirmado usa identificador proprio, nao interpola titulo do site nem vaza a sonda", async () => {
  const a = ambiente();
  const foco = criarControleDeFoco(a.deps, a.page);
  await foco.ativar();
  assert.deepEqual(foco.registros, [{ confirmado: true }]);
  assert.deepEqual(await a.deps.nvda.spokenPhraseLog(), []);
  assert.equal(a.ativacoes(), 1);
});

test("reconhece o marcador mesmo quando o NVDA separa CamelCase e digitos com espacos ao falar", async () => {
  const a = ambiente();
  let marcadorCapturado = "";
  let falas = [];
  const origEvaluate = a.page.evaluate;
  a.page.evaluate = async (_, id) => {
    if (id) marcadorCapturado = id;
    return origEvaluate(_, id);
  };
  a.deps.nvda.clearSpokenPhraseLog = async () => { falas = []; };
  a.deps.nvda.spokenPhraseLog = async () => falas;
  a.deps.nvda.perform = async () => {
    const separado = marcadorCapturado.replace(/([a-zA-Z])(\d)/g, "$1 $2").replace(/(\d)([a-zA-Z])/g, "$1 $2").replace(/([a-z])([A-Z])/g, "$1 $2");
    falas = [`${separado} - Pessoal — Microsoft Edge`];
  };
  const foco = criarControleDeFoco(a.deps, a.page);
  await foco.ativar();
  assert.deepEqual(foco.registros, [{ confirmado: true }]);
});

test("uma ativacao recusada tenta recuperacao por Alt e exige confirmacao", async () => {
  const a = ambiente({ ativacoesNecessarias: 2 });
  const foco = criarControleDeFoco(a.deps, a.page);
  await foco.ativar();
  assert.deepEqual(a.eventos, ["Alt+Escape"]);
  assert.deepEqual(foco.registros, [{ confirmado: false }, { confirmado: true }]);
});

test("foco nunca obtido termina sem enviar Tab ou leitura, limpa fala privada e fecha recursos", async () => {
  const a = ambiente({ ativacoesNecessarias: Infinity });
  const r = await percorrer({ url: "https://example.org/", tabs: 2, leituras: 2 }, a.deps);
  assert.match(r.erro, /nao confirmou/);
  assert.deepEqual(r.tab, []);
  assert.deepEqual(r.leitura, []);
  assert.deepEqual(a.eventos, ["Alt+Escape", "parou", "fechou"]);
  assert.equal(a.ativacoes(), 2);
  assert.ok(!JSON.stringify(r).includes("privado"));
  assert.deepEqual(await a.deps.nvda.spokenPhraseLog(), []);
});

test("perda de foco durante um passo descarta esse passo e impede os seguintes", async () => {
  const a = ambiente({ perderNoTab: true });
  const r = await percorrer({ url: "https://example.org/", tabs: 3, leituras: 2 }, a.deps);
  assert.match(r.erro, /nao confirmou/);
  assert.deepEqual(r.tab, []);
  assert.deepEqual(a.eventos, ["Tab", "parou", "fechou"]);
  assert.ok(!JSON.stringify(r).includes("conteudo nao confirmado"));
});

test("percorre multiplas janelas com Alt+Escape usando capture:false ate encontrar a janela ou repetir ciclo", async () => {
  const janelas = ["Janela A", "Janela B", "Janela C"];
  let indice = 0;
  let falas = [];
  const comandos = [];
  const nvda = {
    keyboardCommands: {
      reportTitle: "reportTitle",
      exitFocusMode: "exitFocusMode",
      readNextFocusableItem: "readNextFocusableItem",
      toggleBetweenBrowseAndFocusMode: "toggleBetweenBrowseAndFocusMode",
    },
    clearSpokenPhraseLog: async () => { falas = []; },
    spokenPhraseLog: async () => falas,
    perform: async (cmd, opts) => {
      comandos.push([cmd, opts]);
      if (cmd === "reportTitle") {
        falas = [janelas[indice % janelas.length]];
      } else if (cmd?.keyCode) {
        indice++;
      }
    },
  };
  let focouBody = false;
  const page = {
    bringToFront: async () => {},
    evaluate: async () => {},
    locator: (sel) => {
      assert.equal(sel, "body");
      return {
        waitFor: async () => {},
        focus: async () => { focouBody = true; },
        click: async () => {},
        blur: async () => {},
      };
    },
  };
  const deps = {
    nvda,
    WindowsKeyCodes: { Escape: "Esc" },
    WindowsModifiers: { Alt: "Alt" },
    windowsActivate: async () => {},
    pause: async () => {},
  };
  // Caso 1: ciclo fecha na repeticao de Janela A sem achar o marcador
  const focoFalho = criarControleDeFoco(deps, page);
  await assert.rejects(focoFalho.ativar(), /nao confirmou/);
  assert.equal(focoFalho.registros.length, 4); // Janela A, B, C e repeticao de A

  // Caso 2: o marcador esta na 3a janela e confirma apos 2 Alt+Escape
  indice = 0;
  const focoSucesso = criarControleDeFoco(deps, page);
  page.evaluate = async (_, id) => {
    janelas[2] = `${id} - Microsoft Edge`;
  };
  await focoSucesso.ativar();
  assert.deepEqual(focoSucesso.registros, [{ confirmado: false }, { confirmado: false }, { confirmado: true }]);
  assert.ok(comandos.some(([c, o]) => c?.keyCode?.[0] === "Esc" && o?.capture === false));
});
