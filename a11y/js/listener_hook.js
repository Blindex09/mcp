(() => {
  // Instalado antes dos scripts da pagina (todos os frames): registra QUEM tem listener de acao, para os navegadores
  // sem CDP (Firefox/WebKit) e para dizer quando a acao e' delegada a um ancestral (document/body/raiz).
  if (window.__a11yHooked) return;
  window.__a11yHooked = true;
  const ACTION = new Set(['click', 'mousedown', 'mouseup', 'pointerdown', 'pointerup', 'touchstart', 'touchend', 'dblclick', 'keydown', 'keyup', 'keypress']);
  // Proveniencia como FATO: o endereco do script que fez o registro (ultimo trecho "url:linha:coluna" da pilha, o
  // primeiro fora deste gancho). Codigo avaliado, sem endereco (o proprio Playwright ao agir na pagina, ou HTML passado
  // direto no Chromium), fica com source null: quem le decide o que fazer com isso, nada e filtrado aqui.
  const LOCATION = /(?:https?|file):\/\/[^\s)]+?:\d+:\d+|about:blank:\d+:\d+/;
  const sourceOfCaller = () => {
    const m = String(new Error().stack || '').match(LOCATION);
    return m ? m[0] : null;
  };
  window.__a11yDelegated = [];
  const orig = EventTarget.prototype.addEventListener;
  EventTarget.prototype.addEventListener = function (type, fn, opts) {
    try {
      if (ACTION.has(type)) {
        if (this instanceof Element && this !== document.documentElement && this !== document.body) {
          (this.__a11yL = this.__a11yL || new Set()).add(type);
        } else {
          const where = this === window ? 'window' : this === document ? 'document' : (this.tagName || 'node').toLowerCase();
          const seen = window.__a11yDelegated.find(d => d.on === where && d.type === type);
          const source = sourceOfCaller();
          if (!seen) window.__a11yDelegated.push({on: where, type: type, source: source});
          else if (!seen.source && source) seen.source = source;  // o mesmo par ja existia sem origem: agora tem
        }
      }
    } catch (e) {}
    return orig.call(this, type, fn, opts);
  };
})();
