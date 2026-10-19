<script>
  let { k } = $props();
  let aberto = $state(false);
</script>

<!-- div com on:click: sem papel, sem foco, sem Enter/Espaço e sem estado. O compilador do Svelte avisa. -->
<div>
  <div id="{k}-gatilho" class="fake-botao" onclick={() => (aberto = !aberto)}>Prazo de entrega</div>
  {#if aberto}<p id="{k}-painel">Cinco dias úteis.</p>{/if}
</div>
