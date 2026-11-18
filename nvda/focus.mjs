import { randomUUID } from "node:crypto";

// Espera a fala assentar: no minimo `minimo` ms, e depois ate o log ficar parado por `estavel` ms
// (ou ate `maximo`, que so existe para nao ficar preso se o NVDA nunca falar). Nao e um tempo fixo por passo.
export async function esperarFalaAssentar(nvda, pause, { minimo = 500, estavel = 400, maximo = 5000, passo = 100 } = {}) {
  let gasto = 0;
  let ultimo = (await nvda.spokenPhraseLog()).length;
  let parado = 0;
  while (gasto < maximo) {
    await pause(passo);
    gasto += passo;
    const agora = (await nvda.spokenPhraseLog()).length;
    parado = agora === ultimo ? parado + passo : 0;
    ultimo = agora;
    if (gasto >= minimo && parado >= estavel) return;
  }
}


// Um identificador ASCII evita ambiguidades entre janelas e impede que o titulo
// fornecido pelo site seja interpolado no VBS/PowerShell do Guidepup.
export function criarControleDeFoco({ nvda, windowsActivate, NVDAKeyCodeCommands, WindowsKeyCodes, WindowsModifiers, pause }, page, prepararJanela = async () => {}) {
  const marcador = `A11yNvda${randomUUID().replaceAll("-", "")}`;
  // O NVDA separa CamelCase e transicoes entre letras e digitos com espacos ao falar
  // (por exemplo "A11yNvda..." vira "A 11y Nvda ..."). Seguindo cleanString.ts do Guidepup,
  // comparamos em minusculas e sem espacos/pontuacao para reconhecer o marcador falado.
  const compactar = (texto) => String(texto ?? "").toLowerCase().replace(/[^a-z0-9]/g, "");
  const marcadorCompacto = compactar(marcador);
  const registros = [];
  const comandos = NVDAKeyCodeCommands ?? nvda.keyboardCommands;
  const alternarAplicativo = WindowsKeyCodes && WindowsModifiers
    ? { keyCode: [WindowsKeyCodes.Escape], modifiers: [WindowsModifiers.Alt] }
    : null;
  const inspecionar = async () => {
    await nvda.clearSpokenPhraseLog();
    await nvda.perform(comandos.reportTitle);
    await esperarFalaAssentar(nvda, pause);
    const frases = await nvda.spokenPhraseLog();
    const confirmado = frases.some((frase) => compactar(frase).includes(marcadorCompacto));
    const assinatura = frases.join(" | ").trim();
    // Nao registrar anuncios de outros aplicativos: podem conter dados pessoais.
    await nvda.clearSpokenPhraseLog();
    registros.push({ confirmado });
    return { confirmado, assinatura };
  };
  const confirmar = async () => (await inspecionar()).confirmado;
  const exigir = async () => {
    if (!(await confirmar())) throw new Error("O NVDA nao confirmou a janela de teste; navegacao interrompida para nao capturar outro aplicativo.");
  };
  let jaAtivou = false;
  const ativar = async () => {
    await page.evaluate((id) => { document.title = id; }, marcador);
    await page.bringToFront();
    if (comandos?.exitFocusMode) {
      await nvda.perform(comandos.exitFocusMode, { capture: false });
      await pause(100);
    }
    if (jaAtivou) {
      await prepararJanela();
      const recheck = await inspecionar();
      if (recheck.confirmado) {
        await nvda.clearSpokenPhraseLog();
        return;
      }
    }
    jaAtivou = true;
    // windowsActivate usa Get-Process internamente, que espera o nome sem .exe.
    await windowsActivate("msedge", marcador);
    await prepararJanela();
    const janelasVistas = new Set();
    let atual = await inspecionar();
    if (!atual.confirmado) {
      if (atual.assinatura) janelasVistas.add(atual.assinatura);
      let usouAtivacaoSecundaria = false;
      let leiturasVazias = atual.assinatura ? 0 : 1;
      // Percorre as janelas abertas com Alt+Escape (SWITCH_APPLICATION com { capture: false }
      // do navigateToWebContent.ts do Guidepup) enquanto cada troca avanca para uma janela nova,
      // parando assim que confirmar o marcador ou repetir uma janela ja vista.
      while (true) {
        if (!usouAtivacaoSecundaria) {
          usouAtivacaoSecundaria = true;
          await windowsActivate("msedge", marcador);
        }
        if (alternarAplicativo) {
          await nvda.perform(alternarAplicativo, { capture: false });
        } else {
          await nvda.press("Alt+Escape", { capture: false });
        }
        await pause(500);
        await prepararJanela();
        atual = await inspecionar();
        if (atual.confirmado) break;
        if (!atual.assinatura) {
          leiturasVazias++;
          if (leiturasVazias >= 3) {
            throw new Error("O NVDA nao confirmou a janela de teste; navegacao interrompida para nao capturar outro aplicativo.");
          }
          continue;
        }
        leiturasVazias = 0;
        if (janelasVistas.has(atual.assinatura)) {
          throw new Error("O NVDA nao confirmou a janela de teste; navegacao interrompida para nao capturar outro aplicativo.");
        }
        janelasVistas.add(atual.assinatura);
      }
      await page.bringToFront();
    }
    await nvda.clearSpokenPhraseLog();
  };
  return { ativar, exigir, registros };
}
