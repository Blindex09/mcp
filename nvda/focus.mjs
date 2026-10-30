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
export function criarControleDeFoco({ nvda, windowsActivate, pause }, page) {
  const marcador = `A11yNvda${randomUUID().replaceAll("-", "")}`;
  const registros = [];
  const confirmar = async () => {
    await nvda.clearSpokenPhraseLog();
    await nvda.perform(nvda.keyboardCommands.reportTitle);
    await esperarFalaAssentar(nvda, pause);
    const frases = await nvda.spokenPhraseLog();
    const confirmado = frases.some((frase) => frase.includes(marcador));
    // Nao registrar anuncios de outros aplicativos: podem conter dados pessoais.
    await nvda.clearSpokenPhraseLog();
    registros.push({ confirmado });
    return confirmado;
  };
  const exigir = async () => {
    if (!(await confirmar())) throw new Error("O NVDA nao confirmou a janela de teste; navegacao interrompida para nao capturar outro aplicativo.");
  };
  const ativar = async () => {
    await page.evaluate((id) => { document.title = id; }, marcador);
    await page.bringToFront();
    // windowsActivate usa Get-Process internamente, que espera o nome sem .exe.
    await windowsActivate("msedge", marcador);
    if (await confirmar()) return;
    // Recuperacao unica, sem laço: ALT permite ao Windows aceitar uma nova
    // ativacao de janela. Nenhuma tecla de navegacao e enviada antes da prova.
    await nvda.press("Alt");
    await windowsActivate("msedge", marcador);
    await exigir();
  };
  return { ativar, exigir, registros };
}
