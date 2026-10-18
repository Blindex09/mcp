(() => {
  // Contador de atividade da pagina (mutacoes do DOM): sinal de PROGRESSO para as esperas adaptativas.
  if (window.__a11yMutations !== undefined) return;
  window.__a11yMutations = 0;
  new MutationObserver((records) => { window.__a11yMutations += records.length; })
    .observe(document, {subtree: true, childList: true, attributes: true, characterData: true});
})()
