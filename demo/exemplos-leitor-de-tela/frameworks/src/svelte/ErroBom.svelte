<script>
  import { tick } from 'svelte';
  let { k } = $props();
  let mensagem = $state('');
  let campo;
  async function enviar(e) {
    e.preventDefault();
    if (campo.value) { mensagem = ''; return; }
    mensagem = 'Informe o e-mail.';
    await tick();
    campo.focus(); // o foco vai ao campo com erro
  }
</script>

<form novalidate onsubmit={enviar}>
  <label for="{k}-email">E-mail</label>
  <input id="{k}-email" bind:this={campo} type="email" required aria-invalid={mensagem ? 'true' : undefined} aria-describedby="{k}-erro" />
  <span id="{k}-erro" class="erro-visual" role="alert">{mensagem}</span>
  <p><button type="submit" id="{k}-enviar">Enviar</button></p>
</form>
