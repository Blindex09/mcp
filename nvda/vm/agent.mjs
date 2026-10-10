// Servidor que roda DENTRO da maquina virtual: recebe "percorra esta pagina com o NVDA" e devolve a fala em texto.
// So aceita quem mandar o token. Um trabalho por vez. O pedido e' aceito na hora e consultado depois: nenhuma
// chamada fica presa num relogio fixo, e um pedido lento nunca e' repetido (repetir religaria o NVDA).
//
//   POST /percorrer        {url, tabs, leituras, silencio}  ->  202 {id}
//   GET  /percorrer/<id>   ->  {estado: "executando"|"concluido", passos, resultado?}
//   GET  /saude            ->  {ok, ocupado}
import { randomUUID, timingSafeEqual } from "node:crypto";
import { createServer } from "node:http";
import { pathToFileURL } from "node:url";
import { LIMITES, carregarDependencias, percorrer, settingsDeSilencio, validarUrl } from "../walk.mjs";

const TAMANHO_MAXIMO_CORPO = 10_000;
const TRABALHOS_GUARDADOS = 5;

function tokenConfere(recebido, esperado) {
  const a = Buffer.from(recebido ?? "");
  const b = Buffer.from(esperado);
  return a.length === b.length && timingSafeEqual(a, b);
}

function responder(res, status, corpo) {
  const dados = JSON.stringify(corpo);
  res.writeHead(status, { "content-type": "application/json; charset=utf-8", "content-length": Buffer.byteLength(dados) });
  res.end(dados);
}

async function lerCorpo(req) {
  let total = 0;
  const partes = [];
  for await (const parte of req) {
    total += parte.length;
    if (total > TAMANHO_MAXIMO_CORPO) throw Object.assign(new Error("corpo grande demais"), { status: 413 });
    partes.push(parte);
  }
  try {
    return JSON.parse(Buffer.concat(partes).toString("utf8") || "{}");
  } catch {
    throw Object.assign(new Error("JSON invalido"), { status: 400 });
  }
}

function validarPedido(corpo, silencioPadrao) {
  const pedido = {
    url: validarUrl(corpo.url),
    tabs: corpo.tabs ?? 15,
    leituras: corpo.leituras ?? 20,
    silencio: corpo.silencio === undefined ? silencioPadrao : corpo.silencio,
  };
  if (!Number.isInteger(pedido.tabs) || pedido.tabs < 0 || pedido.tabs > LIMITES.tabs) throw new Error(`tabs deve ser um inteiro de 0 a ${LIMITES.tabs}`);
  if (!Number.isInteger(pedido.leituras) || pedido.leituras < 0 || pedido.leituras > LIMITES.leituras) {
    throw new Error(`leituras deve ser um inteiro de 0 a ${LIMITES.leituras}`);
  }
  settingsDeSilencio(pedido.silencio); // valida o valor
  return pedido;
}

export function criarServidor({ token, executar, silencioPadrao = "volume" }) {
  if (!token || token.length < 16) throw new Error("token curto demais: use pelo menos 16 caracteres");
  const trabalhos = new Map();
  let ocupado = false;

  const servidor = createServer(async (req, res) => {
    try {
      const autorizacao = req.headers.authorization ?? "";
      if (!autorizacao.startsWith("Bearer ") || !tokenConfere(autorizacao.slice(7), token)) {
        return responder(res, 401, { erro: "token ausente ou errado" });
      }
      const caminho = new URL(req.url, "http://x").pathname;

      if (req.method === "GET" && caminho === "/saude") return responder(res, 200, { ok: true, ocupado });

      if (req.method === "POST" && caminho === "/percorrer") {
        const corpo = await lerCorpo(req);
        let pedido;
        try {
          pedido = validarPedido(corpo, silencioPadrao);
        } catch (e) {
          return responder(res, 400, { erro: e.message });
        }
        if (ocupado) return responder(res, 409, { erro: "ja ha um teste em andamento nesta VM" });
        ocupado = true;
        const id = randomUUID();
        const trabalho = { estado: "executando", passos: 0 };
        trabalhos.set(id, trabalho);
        while (trabalhos.size > TRABALHOS_GUARDADOS) trabalhos.delete(trabalhos.keys().next().value);
        executar(pedido, (passos) => { trabalho.passos = passos; })
          .then((resultado) => { trabalho.resultado = resultado; })
          .catch((e) => { trabalho.resultado = { url: pedido.url, tab: [], leitura: [], erro: String(e?.message ?? e) }; })
          .finally(() => { trabalho.estado = "concluido"; ocupado = false; });
        return responder(res, 202, { id });
      }

      const consulta = req.method === "GET" && caminho.match(/^\/percorrer\/([0-9a-f-]{36})$/);
      if (consulta) {
        const trabalho = trabalhos.get(consulta[1]);
        if (!trabalho) return responder(res, 404, { erro: "trabalho desconhecido" });
        return responder(res, 200, trabalho);
      }
      return responder(res, 404, { erro: "rota desconhecida" });
    } catch (e) {
      return responder(res, e.status ?? 500, { erro: e.message });
    }
  });
  return servidor;
}

async function iniciar() {
  const token = process.env.NVDA_AGENT_TOKEN;
  const porta = Number(process.env.NVDA_AGENT_PORT ?? 8765);
  const endereco = process.env.NVDA_AGENT_HOST ?? "0.0.0.0";
  const silencioPadrao = process.env.NVDA_SILENCIO === "" ? null : (process.env.NVDA_SILENCIO ?? "volume");
  const deps = await carregarDependencias();
  const servidor = criarServidor({ token, silencioPadrao, executar: (pedido, aoAvancar) => percorrer(pedido, deps, aoAvancar) });
  servidor.listen(porta, endereco, () => console.log(`agente do NVDA em http://${endereco}:${porta} (silencio padrao: ${silencioPadrao ?? "nenhum"})`));
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  iniciar().catch((e) => {
    console.error(e.message);
    process.exit(1);
  });
}
