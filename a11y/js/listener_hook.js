(() => {
  // Instalado antes dos scripts da pagina (todos os frames): registra QUEM tem listener de acao, para os navegadores
  // sem CDP (Firefox/WebKit) e para dizer quando a acao e' delegada a um ancestral (document/body/raiz).
  if (window.__a11yHooked) return;
  window.__a11yHooked = true;
  const ACTION = new Set(['click', 'mousedown', 'mouseup', 'pointerdown', 'pointerup', 'touchstart', 'touchend', 'dblclick', 'keydown', 'keyup', 'keypress']);
  window.__a11yDelegated = [];
  const orig = EventTarget.prototype.addEventListener;
  EventTarget.prototype.addEventListener = function (type, fn, opts) {
    try {
      if (ACTION.has(type)) {
        if (this instanceof Element && this !== document.documentElement && this !== document.body) {
          (this.__a11yL = this.__a11yL || new Set()).add(type);
        } else {
          const where = this === window ? 'window' : this === document ? 'document' : (this.tagName || 'node').toLowerCase();
          if (!window.__a11yDelegated.some(d => d.on === where && d.type === type)) window.__a11yDelegated.push({on: where, type: type});
        }
      }
    } catch (e) {}
    return orig.call(this, type, fn, opts);
  };
})();
