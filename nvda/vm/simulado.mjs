// Agente com um NVDA SIMULADO, so para o teste automatico provar o contrato entre o MCP (Python) e o agente (Node).
// Nao liga o NVDA, nao abre navegador. Imprime "PORTA <n>" quando pronto.
import { ATALHOS_NAVEGACAO } from "../walk.mjs";
import { validarComando } from "../sessao.mjs";
import { criarServidor } from "./agent.mjs";

const token = process.env.NVDA_AGENT_TOKEN;
const servidor = criarServidor({
  token,
  validarComando,
  // pagina simulada com 7 titulos: o comando "tecla H ate_fim" anda por eles e depois "sem proximo titulo"
  abrirSessao: async ({ url }) => {
    let titulo = 0;
    return {
      info: { janela: null, titulo: "simulada" },
      executar: async (entrada, aoAvancar) => {
        const c = validarComando(entrada);
        if (c.acao === "esperar") return { fala: "conteudo dinamico carregado", tempo_esperado_ms: c.tempo_ms, url };
        if (c.acao === "modo") return { fala: `modo alternado para ${c.modo}`, modo: c.modo, url };
        if (c.acao !== "tecla") return { ok: true, url };
        const passos = [];
        let parou = "quantidade";
        const total = c.ate_fim ? c.maximo : c.repetir;
        for (let i = 1; i <= total; i++) {
          titulo += 1;
          const fala = titulo > 7 ? "sem proximo titulo" : `titulo ${titulo}`;
          passos.push({ passo: i, fala });
          aoAvancar(1);
          if (c.ate_fim && titulo > 9) { parou = "repetiu"; break; }
          if (i === total) parou = c.ate_fim ? "maximo" : "quantidade";
        }
        return { passos, parou_por: parou, continua: parou === "maximo", url };
      },
      fechar: async () => ({ fechada: true }),
    };
  },
  executar: async (pedido, aoAvancar) => {
    const resultado = { url: pedido.url, silencio: pedido.silencio, tab: [], leitura: [], atalhos: {}, teclas: [], erro: null };
    let passos = 0;
    for (let i = 1; i <= pedido.tabs; i++) {
      resultado.tab.push({ passo: i, fala: `Tab ${i} em ${new URL(pedido.url).hostname}` });
      passos += 1;
      aoAvancar(passos);
      await new Promise((r) => setTimeout(r, 30));
    }
    for (let i = 1; i <= pedido.leituras; i++) resultado.leitura.push({ passo: i, fala: `item ${i}` });
    for (const [cat, qtd] of Object.entries(pedido.atalhos ?? {})) {
      const tecla = ATALHOS_NAVEGACAO[cat]?.tecla ?? cat;
      resultado.atalhos[cat] = [];
      for (let i = 1; i <= qtd; i++) resultado.atalhos[cat].push({ passo: i, tecla, fala: `${cat} ${i}` });
    }
    for (let i = 0; i < (pedido.teclas ?? []).length; i++) resultado.teclas.push({ passo: i + 1, tecla: pedido.teclas[i], fala: `tecla ${pedido.teclas[i]}` });
    return resultado;
  },
});
servidor.listen(0, "127.0.0.1", () => console.log(`PORTA ${servidor.address().port}`));