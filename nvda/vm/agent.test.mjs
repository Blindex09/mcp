// Testes sem NVDA, sem navegador e sem VM: tudo simulado. Rodar com: node --test nvda/
import assert from "node:assert/strict";
import { test } from "node:test";
import { criarServidor } from "./agent.mjs";
import { esperarFalaAssentar, percorrer, settingsDeSilencio, validarUrl } from "../walk.mjs";

const TOKEN = "token-de-teste-com-mais-de-16";

async function subir(executar) {
  const servidor = criarServidor({ token: TOKEN, executar });
  await new Promise((r) => servidor.listen(0, "127.0.0.1", r));
  const base = `http://127.0.0.1:${servidor.address().port}`;
  const chamar = (caminho, { metodo = "GET", corpo, token = TOKEN } = {}) =>
    fetch(base + caminho, {
      method: metodo,
      headers: { ...(token ? { authorization: `Bearer ${token}` } : {}), "content-type": "application/json" },
      body: corpo === undefined ? undefined : JSON.stringify(corpo),
    });
  return { servidor, chamar };
}

test("sem token ou com token errado: 401, e nada e executado", async () => {
  let rodou = false;
  const { servidor, chamar } = await subir(async () => { rodou = true; return {}; });
  assert.equal((await chamar("/saude", { token: null })).status, 401);
  assert.equal((await chamar("/saude", { token: "errado-errado-errado" })).status, 401);
  assert.equal((await chamar("/percorrer", { metodo: "POST", corpo: { url: "http://a.com" }, token: "x" })).status, 401);
  assert.equal(rodou, false);
  servidor.close();
});

test("recusa token curto ao criar o servidor", () => {
  assert.throws(() => criarServidor({ token: "curto", executar: async () => ({}) }), /token curto/);
});

test("pedido invalido: 400 (url nao http, limites, silencio)", async () => {
  const { servidor, chamar } = await subir(async () => ({}));
  for (const corpo of [{ url: "file:///c:/x" }, { url: "javascript:alert(1)" }, { url: "http://a.com", tabs: 9999 }, { url: "http://a.com", leituras: -1 }, { url: "http://a.com", silencio: "alto" }, {}]) {
    assert.equal((await chamar("/percorrer", { metodo: "POST", corpo })).status, 400, JSON.stringify(corpo));
  }
  servidor.close();
});

test("aceita na hora (202), mostra o andamento e entrega o resultado; usa silencio por volume se nada for pedido", async () => {
  let liberar;
  const travado = new Promise((r) => { liberar = r; });
  let recebido;
  const { servidor, chamar } = await subir(async (pedido, aoAvancar) => {
    recebido = pedido;
    aoAvancar(3);
    await travado;
    return { url: pedido.url, tab: [{ passo: 1, fala: "botao" }], leitura: [], erro: null };
  });
  const resp = await chamar("/percorrer", { metodo: "POST", corpo: { url: "http://exemplo.com/a" } });
  assert.equal(resp.status, 202);
  const { id } = await resp.json();
  assert.equal(recebido.silencio, "volume");
  const durante = await (await chamar(`/percorrer/${id}`)).json();
  assert.deepEqual([durante.estado, durante.passos, durante.resultado], ["executando", 3, undefined]);
  assert.equal((await (await chamar("/saude")).json()).ocupado, true);
  assert.equal((await chamar("/percorrer", { metodo: "POST", corpo: { url: "http://exemplo.com/b" } })).status, 409);
  liberar();
  await new Promise((r) => setTimeout(r, 20));
  const fim = await (await chamar(`/percorrer/${id}`)).json();
  assert.equal(fim.estado, "concluido");
  assert.equal(fim.resultado.tab[0].fala, "botao");
  assert.equal((await (await chamar("/saude")).json()).ocupado, false);
  servidor.close();
});

test("se a execucao falhar, o trabalho conclui com o erro e libera a VM", async () => {
  const { servidor, chamar } = await subir(async () => { throw new Error("o NVDA nao subiu"); });
  const { id } = await (await chamar("/percorrer", { metodo: "POST", corpo: { url: "http://exemplo.com" } })).json();
  await new Promise((r) => setTimeout(r, 20));
  const fim = await (await chamar(`/percorrer/${id}`)).json();
  assert.equal(fim.estado, "concluido");
  assert.match(fim.resultado.erro, /NVDA nao subiu/);
  assert.equal((await (await chamar("/saude")).json()).ocupado, false);
  servidor.close();
});

test("silencio: volume zera a voz, sem-fala troca o sintetizador, outro valor e erro", () => {
  assert.deepEqual(settingsDeSilencio("volume"), { speech: { oneCore: { volume: 0 } } });
  assert.deepEqual(settingsDeSilencio("sem-fala"), { speech: { synth: "silence" } });
  assert.equal(settingsDeSilencio(null), undefined);
  assert.throws(() => settingsDeSilencio("alto"));
  assert.throws(() => validarUrl("ftp://x"));
});

test("esperar a fala assentar acompanha o NVDA em vez de um tempo fixo por passo", async () => {
  // a fala demora 6 ciclos para terminar de chegar; depois fica parada
  let ciclos = 0;
  const nvda = { spokenPhraseLog: async () => Array.from({ length: Math.min(ciclos, 6) }, (_, i) => `f${i}`) };
  const gastos = [];
  const pause = async (ms) => { ciclos++; gastos.push(ms); };
  await esperarFalaAssentar(nvda, pause, { minimo: 200, estavel: 300, maximo: 5000, passo: 100 });
  const total = gastos.reduce((a, b) => a + b, 0);
  assert.ok(total >= 900 && total < 5000, `esperou ${total} ms`); // acabou quando parou de mudar, nao no maximo
  // se o NVDA nunca fala, para no maximo e nao fica preso
  const mudo = { spokenPhraseLog: async () => [] };
  let g = 0;
  await esperarFalaAssentar(mudo, async (ms) => { g += ms; }, { minimo: 200, estavel: 300, maximo: 1000, passo: 100 });
  assert.ok(g <= 1000);
});

test("percorrer: Tab e leitura gravam a fala de cada passo, avisam o andamento e sempre desligam o NVDA e o navegador", async () => {
  const eventos = [];
  let falas = [];
  const nvda = {
    start: async (o) => eventos.push(["start", o]),
    stop: async () => eventos.push(["stop"]),
    clearSpokenPhraseLog: async () => { falas = []; },
    spokenPhraseLog: async () => falas,
    press: async (k) => { eventos.push(["press", k]); falas = [`fala de ${k}`]; },
    next: async () => { eventos.push(["next"]); falas = ["proximo item"]; },
  };
  const page = { goto: async () => {}, reload: async () => {}, bringToFront: async () => {}, title: async () => "Casa do Chá" };
  const chromium = { launch: async () => ({ newPage: async () => page, close: async () => eventos.push(["fechou navegador"]) }) };
  const avancos = [];
  const r = await percorrer({ url: "http://exemplo.com", tabs: 2, leituras: 1, silencio: "volume" }, { nvda, chromium, windowsActivate: async () => {}, pause: async () => {} }, (n) => avancos.push(n));
  assert.equal(r.erro, null);
  assert.deepEqual(r.tab.map((x) => x.fala), ["fala de Tab", "fala de Tab"]);
  assert.deepEqual(r.leitura.map((x) => x.fala), ["proximo item"]);
  assert.deepEqual(avancos, [1, 2, 3]);
  assert.deepEqual(eventos.find((e) => e[0] === "start")[1], { settings: { speech: { oneCore: { volume: 0 } } } });
  assert.deepEqual(eventos.slice(-2).map((e) => e[0]), ["stop", "fechou navegador"]);
});

test("percorrer: se algo falhar no meio, devolve o que ja foi falado, o erro, e ainda desliga tudo", async () => {
  const eventos = [];
  const nvda = {
    start: async () => {}, stop: async () => eventos.push("stop"), clearSpokenPhraseLog: async () => {},
    spokenPhraseLog: async () => ["x"],
    press: async () => { if (eventos.length >= 1) throw new Error("NVDA parou de responder"); eventos.push("press"); },
    next: async () => {},
  };
  const page = { goto: async () => {}, reload: async () => {}, bringToFront: async () => {}, title: async () => "T" };
  const chromium = { launch: async () => ({ newPage: async () => page, close: async () => eventos.push("fechou") }) };
  const r = await percorrer({ url: "http://exemplo.com", tabs: 3, leituras: 0 }, { nvda, chromium, windowsActivate: async () => {}, pause: async () => {} });
  assert.equal(r.tab.length, 1);
  assert.match(r.erro, /parou de responder/);
  assert.deepEqual(eventos.slice(-2), ["stop", "fechou"]);
});
