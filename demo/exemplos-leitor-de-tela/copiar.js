// Botao "Copiar codigo": leva o texto do bloco de codigo para a area de transferencia e avisa uma vez, numa regiao de status que ja esta na pagina.
(function () {
  var aviso = document.getElementById('aviso-copia');
  function dizer(texto) {
    aviso.textContent = '';
    requestAnimationFrame(function () { aviso.textContent = texto; });
  }
  function copiar(texto) {
    if (navigator.clipboard && window.isSecureContext) return navigator.clipboard.writeText(texto);
    return new Promise(function (ok, falha) {
      var area = document.createElement('textarea');
      area.value = texto;
      area.setAttribute('readonly', '');
      area.style.position = 'fixed';
      area.style.opacity = '0';
      document.body.appendChild(area);
      area.select();
      var copiou = false;
      try { copiou = document.execCommand('copy'); } catch (e) { copiou = false; }
      document.body.removeChild(area);
      if (copiou) ok(); else falha(new Error('copy'));
    });
  }
  function esconderSelos() {
    Array.prototype.forEach.call(document.querySelectorAll('.selo'), function (s) { s.hidden = true; });
  }
  document.addEventListener('click', function (e) {
    var botao = e.target.closest('[data-copiar]');
    if (!botao) return;
    var alvo = document.getElementById(botao.getAttribute('data-copiar'));
    esconderSelos();
    copiar(alvo.textContent).then(function () {
      botao.nextElementSibling.hidden = false;
      dizer('Código copiado');
    }, function () {
      dizer('Não foi possível copiar o código. Selecione o texto do bloco e copie com Control mais C.');
    });
  });
  document.addEventListener('focusout', function (e) {
    if (e.target.closest && e.target.closest('[data-copiar]')) esconderSelos();
  });
})();
