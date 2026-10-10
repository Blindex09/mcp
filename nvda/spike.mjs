// Linha de comando do teste com o NVDA real (sem modelo de IA). Grava a fala em nvda/out/<rotulo>.txt e .json.
// Uso: node spike.mjs <url> <rotulo> [tabs=15] [leituras=15]
// Silencio (para rodar numa VM sem ninguem ouvir): NVDA_SILENCIO=volume (voz em 0) ou NVDA_SILENCIO=sem-fala (sintetizador "Sem fala").
import { mkdirSync, writeFileSync } from "node:fs";
import { carregarDependencias, percorrer } from "./walk.mjs";

const [url, rotulo = "pagina", tabsArg = "15", leiturasArg = "15"] = process.argv.slice(2);
if (!url) {
  console.error("uso: node spike.mjs <url> <rotulo> [tabs] [leituras]");
  process.exit(2);
}

const resultado = await percorrer(
  { url, tabs: Number(tabsArg), leituras: Number(leiturasArg), silencio: process.env.NVDA_SILENCIO || undefined },
  await carregarDependencias(),
);

mkdirSync("out", { recursive: true });
writeFileSync(`out/${rotulo}.json`, JSON.stringify(resultado, null, 2));
const linhas = [
  `# ${rotulo} - ${resultado.url}`,
  resultado.erro ? `ERRO: ${resultado.erro}` : "",
  "## Tab",
  ...resultado.tab.map((x) => `${x.passo}. ${x.fala}`),
  "## Leitura (modo leitura)",
  ...resultado.leitura.map((x) => `${x.passo}. ${x.fala}`),
].filter(Boolean);
writeFileSync(`out/${rotulo}.txt`, linhas.join("\n"));
console.log(linhas.join("\n"));
