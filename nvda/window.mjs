// Controla apenas a janela do navegador efemero criado pelo Playwright.
export async function maximizarJanela(page) {
  const cdp = await page.context().newCDPSession(page);
  try {
    const { windowId } = await cdp.send("Browser.getWindowForTarget");
    await cdp.send("Browser.setWindowBounds", { windowId, bounds: { windowState: "maximized" } });
    const { bounds } = await cdp.send("Browser.getWindowBounds", { windowId });
    if (bounds.windowState !== "maximized") throw new Error("O navegador nao confirmou a janela maximizada.");
    const viewport = await page.evaluate(() => ({
      width: window.innerWidth, height: window.innerHeight, deviceScaleFactor: window.devicePixelRatio,
    }));
    return { state: bounds.windowState, viewport };
  } finally {
    await cdp.detach();
  }
}
