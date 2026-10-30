import assert from "node:assert/strict";
import { test } from "node:test";
import { maximizarJanela } from "./window.mjs";

test("maximiza a janela da pagina e registra a area real sem impor viewport", async () => {
  const chamadas = [];
  const page = {
    context: () => ({ newCDPSession: async (alvo) => {
      assert.equal(alvo, page);
      return {
        send: async (metodo, dados) => {
          chamadas.push([metodo, dados]);
          if (metodo === "Browser.getWindowForTarget") return { windowId: 7 };
          return { bounds: { windowState: "maximized" } };
        },
        detach: async () => chamadas.push(["detach"]),
      };
    } }),
    evaluate: async () => ({ width: 1536, height: 790, deviceScaleFactor: 1.25 }),
  };
  assert.deepEqual(await maximizarJanela(page), {
    state: "maximized", viewport: { width: 1536, height: 790, deviceScaleFactor: 1.25 },
  });
  assert.deepEqual(chamadas, [
    ["Browser.getWindowForTarget", undefined],
    ["Browser.setWindowBounds", { windowId: 7, bounds: { windowState: "maximized" } }],
    ["Browser.getWindowBounds", { windowId: 7 }], ["detach"],
  ]);
});

test("recusa janela nao maximizada e desconecta a sessao mesmo na falha", async () => {
  let desligou = false;
  const page = { context: () => ({ newCDPSession: async () => ({
    send: async (metodo) => metodo === "Browser.getWindowForTarget" ? { windowId: 1 } : { bounds: { windowState: "normal" } },
    detach: async () => { desligou = true; },
  }) }) };
  await assert.rejects(maximizarJanela(page), /nao confirmou/);
  assert.equal(desligou, true);
});
