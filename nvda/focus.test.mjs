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
    evaluate: async (_, id) => { marcador = id; },
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

test("uma ativacao recusada tenta recuperacao por Alt e exige confirmacao", async () => {
  const a = ambiente({ ativacoesNecessarias: 2 });
  const foco = criarControleDeFoco(a.deps, a.page);
  await foco.ativar();
  assert.deepEqual(a.eventos, ["Alt"]);
  assert.deepEqual(foco.registros, [{ confirmado: false }, { confirmado: true }]);
});

test("foco nunca obtido termina sem enviar Tab ou leitura, limpa fala privada e fecha recursos", async () => {
  const a = ambiente({ ativacoesNecessarias: Infinity });
  const r = await percorrer({ url: "https://example.org/", tabs: 2, leituras: 2 }, a.deps);
  assert.match(r.erro, /nao confirmou/);
  assert.deepEqual(r.tab, []);
  assert.deepEqual(r.leitura, []);
  assert.deepEqual(a.eventos, ["Alt", "parou", "fechou"]);
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
