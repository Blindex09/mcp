// Agente com um NVDA SIMULADO, so para o teste automatico provar o contrato entre o MCP (Python) e o agente (Node).
// Nao liga o NVDA, nao abre navegador. Imprime "PORTA <n>" quando pronto.
import { criarServidor } from "./agent.mjs";

const token = process.env.NVDA_AGENT_TOKEN;
const servidor = criarServidor({
  token,
  executar: async (pedido, aoAvancar) => {
    const resultado = { url: pedido.url, silencio: pedido.silencio, tab: [], leitura: [], erro: null };
    for (let i = 1; i <= pedido.tabs; i++) {
      resultado.tab.push({ passo: i, fala: `Tab ${i} em ${new URL(pedido.url).hostname}` });
      aoAvancar(i);
      await new Promise((r) => setTimeout(r, 30));
    }
    for (let i = 1; i <= pedido.leituras; i++) resultado.leitura.push({ passo: i, fala: `item ${i}` });
    return resultado;
  },
});
servidor.listen(0, "127.0.0.1", () => console.log(`PORTA ${servidor.address().port}`));
