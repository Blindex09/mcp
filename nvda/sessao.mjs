// Sessao do NVDA que FICA ABERTA na VM: quem decide cada passo e' quem usa o MCP (o modelo de IA do cliente), nao um roteiro fixo.
// Cada comando navega no ponto em que o anterior parou, entao nao ha "limite da pagina": pagina grande, muitas imagens ou
// muitos titulos sao percorridos em varias chamadas, sem recomecar. O limite por chamada so existe para uma resposta nao
// ficar gigante; o resultado diz se o fim foi atingido (parou_por) para quem chama continuar ou parar.
import { ATALHOS_NAVEGACAO, COMANDOS_TECLA_NVDA, REPETICOES_PARA_FIM, executarTeclaNvda, settingsDeSilencio, validarUrl } from "./walk.mjs";
import { criarControleDeFoco, esperarFalaAssentar } from "./focus.mjs";
import { maximizarJanela } from "./window.mjs";

export const LIMITE_POR_CHAMADA = 500;
export const PADRAO_POR_CHAMADA = 100;
export const ACOES = ["ir", "topo", "tab", "tecla", "ativar", "digitar", "esperar", "modo", "estado"];
const ATALHOS_POR_CATEGORIA = Object.fromEntries(Object.entries(ATALHOS_NAVEGACAO).map(([nome, v]) => [nome, v.tecla]));

export function validarComando(c) {
  if (!c || typeof c !== "object" || Array.isArray(c)) throw new Error("comando deve ser um objeto");
  if (!ACOES.includes(c.acao)) throw new Error(`acao invalida: use ${ACOES.join(", ")}`);
  const comando = { acao: c.acao };
  if (c.acao === "ir") comando.url = validarUrl(c.url);
  if (c.acao === "tab") {
    comando.reverso = Boolean(c.reverso);
  }
  if (c.acao === "tab" || c.acao === "tecla") {
    comando.repetir = c.repetir ?? 1;
    if (!Number.isInteger(comando.repetir) || comando.repetir < 1 || comando.repetir > LIMITE_POR_CHAMADA) {
      throw new Error(`repetir deve ser um inteiro de 1 a ${LIMITE_POR_CHAMADA}`);
    }
    comando.ate_fim = Boolean(c.ate_fim);
    if (comando.ate_fim) {
      comando.maximo = c.maximo ?? PADRAO_POR_CHAMADA;
      if (!Number.isInteger(comando.maximo) || comando.maximo < 1 || comando.maximo > LIMITE_POR_CHAMADA) {
        throw new Error(`maximo deve ser um inteiro de 1 a ${LIMITE_POR_CHAMADA}`);
      }
    }
  }
  if (c.acao === "tecla") {
    const tecla = typeof c.tecla === "string" ? c.tecla.trim() : "";
    if (!tecla || tecla.length > 40) throw new Error("tecla deve ser um texto de 1 a 40 caracteres");
    comando.tecla = ATALHOS_POR_CATEGORIA[tecla.toLowerCase()] ?? tecla;
  }
  if (c.acao === "esperar") {
    comando.tempo_ms = c.tempo_ms ?? 1000;
    if (!Number.isInteger(comando.tempo_ms) || comando.tempo_ms < 50 || comando.tempo_ms > 30000) {
      throw new Error("tempo_ms deve ser um inteiro de 50 a 30000");
    }
  }
  if (c.acao === "modo") {
    const modoBruto = String(c.modo ?? "alternar").trim().toLowerCase();
    const mapaModo = {
      navegacao: "navegacao",
      navegação: "navegacao",
      browse: "navegacao",
      foco: "foco",
      focus: "foco",
      alternar: "alternar",
      toggle: "alternar",
    };
    if (!mapaModo[modoBruto]) throw new Error('modo invalido: use "navegacao", "foco" ou "alternar"');
    comando.modo = mapaModo[modoBruto];
  }
  if (c.acao === "ativar" || c.acao === "digitar") {
    // Ativar/digitar pode mudar dados do site: so com autorizacao explicita da pessoa, repassada por quem chama.
    if (c.autorizado !== true) throw new Error(`${c.acao} muda o estado do site e exige autorizado=true (pergunte antes a quem pediu o teste)`);
    comando.autorizado = true;
  }
  if (c.acao === "digitar") {
    if (typeof c.texto !== "string" || !c.texto || c.texto.length > 200) throw new Error("texto deve ter de 1 a 200 caracteres");
    comando.texto = c.texto;
  }
  return comando;
}

async function falasDoPasso(nvda, pause) {
  await esperarFalaAssentar(nvda, pause);
  const frases = await nvda.spokenPhraseLog();
  await nvda.clearSpokenPhraseLog();
  return frases.filter(Boolean).join(" | ") || "(nada falado)";
}

export async function abrirSessao({ url, silencio } = {}, deps) {
  const alvo = validarUrl(url);
  const settings = settingsDeSilencio(silencio);
  const { nvda, chromium, pause } = deps;
  const navegador = await chromium.launch({
    channel: "msedge",
    headless: false,
    args: ["--force-renderer-accessibility", "--start-maximized", "--no-first-run", "--no-default-browser-check"],
  });
  let nvdaLigado = false;
  try {
    const page = await navegador.newPage({ viewport: null });
    await page.goto(alvo, { waitUntil: "load" });
    const info = { janela: null, titulo: null };
    const foco = criarControleDeFoco(deps, page, async () => { info.janela = await maximizarJanela(page); });
    await nvda.start({ capture: true, ...(settings ? { settings } : {}) });
    nvdaLigado = true;
    await pause(2500);
    info.titulo = await page.title();
    await foco.ativar();
    await nvda.clearSpokenPhraseLog();

    const topo = async () => {
      await foco.exigir();
      if (nvda.keyboardCommands?.exitFocusMode) await nvda.perform(nvda.keyboardCommands.exitFocusMode);
      await page.evaluate(() => {
        const el = document.activeElement;
        if (el && el !== document.body && typeof el.blur === "function") el.blur();
        window.scrollTo(0, 0);
      });
      await nvda.press("Control+Home");
      await pause(500);
      await nvda.clearSpokenPhraseLog();
    };
    const estado = async () => ({ url: page.url(), titulo_original: info.titulo });

    const repetir = async (comando, aoAvancar, enviar) => {
      const total = comando.ate_fim ? comando.maximo : comando.repetir;
      const passos = [];
      let anterior = null;
      let iguais = 0;
      let parouPor = "quantidade";
      for (let i = 1; i <= total; i++) {
        await foco.exigir();
        await enviar();
        const fala = await falasDoPasso(nvda, pause);
        await foco.exigir();
        iguais = anterior !== null && fala === anterior ? iguais + 1 : 0;
        const repetiu = iguais >= REPETICOES_PARA_FIM;
        passos.push({ passo: i, fala });
        aoAvancar(1);
        if (comando.ate_fim && repetiu) {
          parouPor = "repetiu";
          break;
        }
        anterior = fala;
        if (i === total) parouPor = comando.ate_fim ? "maximo" : "quantidade";
      }
      // continua=true: o limite da chamada acabou antes do fim da pagina; chame de novo e a navegacao segue de onde parou.
      return { passos, parou_por: parouPor, continua: parouPor === "maximo", ...(await estado()) };
    };

    return {
      info,
      async executar(entrada, aoAvancar = () => {}) {
        const c = validarComando(entrada);
        if (c.acao === "estado") return estado();
        if (c.acao === "topo") { await topo(); return { ok: true, ...(await estado()) }; }
        if (c.acao === "ir") {
          await page.goto(c.url, { waitUntil: "load" });
          info.titulo = await page.title();
          await foco.ativar();
          await topo();
          return { ok: true, ...(await estado()) };
        }
        if (c.acao === "tab") return repetir(c, aoAvancar, () => nvda.press(c.reverso ? "Shift+Tab" : "Tab"));
        if (c.acao === "tecla") return repetir(c, aoAvancar, () => executarTeclaNvda(nvda, c.tecla));
        if (c.acao === "esperar") {
          await pause(c.tempo_ms);
          const fala = await falasDoPasso(nvda, pause);
          return { fala, tempo_esperado_ms: c.tempo_ms, ...(await estado()) };
        }
        if (c.acao === "modo") {
          await foco.exigir();
          if (c.modo === "navegacao") {
            if (nvda.keyboardCommands?.exitFocusMode && typeof nvda.perform === "function") {
              await nvda.perform(nvda.keyboardCommands.exitFocusMode);
            } else {
              await nvda.press("Escape");
            }
          } else if (c.modo === "foco") {
            if (nvda.keyboardCommands?.toggleBetweenBrowseAndFocusMode && typeof nvda.perform === "function") {
              await nvda.perform(nvda.keyboardCommands.toggleBetweenBrowseAndFocusMode);
            } else {
              await nvda.press("Enter");
            }
          } else if (c.modo === "alternar") {
            if (nvda.keyboardCommands?.toggleBetweenBrowseAndFocusMode && typeof nvda.perform === "function") {
              await nvda.perform(nvda.keyboardCommands.toggleBetweenBrowseAndFocusMode);
            } else {
              await nvda.press("Escape");
            }
          }
          const fala = await falasDoPasso(nvda, pause);
          return { fala, modo: c.modo, ...(await estado()) };
        }
        if (c.acao === "ativar") {
          await foco.exigir();
          const antes = page.url();
          await nvda.act();
          const fala = await falasDoPasso(nvda, pause);
          await pause(800);
          const depois = page.url();
          if (depois !== antes) {
            // A pagina mudou: o marcador de janela some junto com o titulo; reconfirma antes de seguir.
            info.titulo = await page.title();
            await foco.ativar();
          }
          return { fala, url_antes: antes, ...(await estado()) };
        }
        if (c.acao === "digitar") {
          await foco.exigir();
          await nvda.type(c.texto);
          const fala = await falasDoPasso(nvda, pause);
          return { fala, ...(await estado()) };
        }
        throw new Error("acao nao tratada");
      },
      async fechar() {
        let erro = null;
        if (nvdaLigado) {
          try { await nvda.stop(); } catch (e) { erro = String(e?.message ?? e); }
          nvdaLigado = false;
        }
        await navegador.close();
        return { fechada: true, erroAoParar: erro };
      },
    };
  } catch (e) {
    if (nvdaLigado) { try { await nvda.stop(); } catch { /* melhor esforco */ } }
    await navegador.close();
    throw e;
  }
}

export { COMANDOS_TECLA_NVDA };
