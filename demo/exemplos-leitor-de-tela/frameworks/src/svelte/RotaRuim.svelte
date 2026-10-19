<script>
  let { k } = $props();
  let tela = $state('inicio');
</script>

<!-- O conteúdo troca, mas o título da aba, o foco e o aviso continuam como estavam. -->
<div>
  <p><button type="button" id="{k}-ir" onclick={() => (tela = 'contato')}>Contato</button></p>
  <main>
    {#if tela === 'inicio'}<h1>Início</h1><p>Bem-vindo à loja de chás.</p>
    {:else}<h1>Contato</h1><p>Escreva para contato@loja.example.</p>{/if}
  </main>
</div>
