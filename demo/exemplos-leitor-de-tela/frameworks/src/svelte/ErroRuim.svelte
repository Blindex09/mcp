<script>
  let { k } = $props();
  let mensagem = $state('');
  function enviar(e) {
    e.preventDefault();
    mensagem = e.currentTarget.elements.email.value ? '' : 'Informe o e-mail.';
  }
</script>

<!-- Texto vermelho solto: o campo não é marcado, a frase não está ligada a ele, o foco não se move. -->
<form novalidate onsubmit={enviar}>
  <label for="{k}-email">E-mail</label>
  <input id="{k}-email" name="email" type="email" required /> <span class="erro-visual">{mensagem}</span>
  <p><button type="submit" id="{k}-enviar">Enviar</button></p>
</form>
