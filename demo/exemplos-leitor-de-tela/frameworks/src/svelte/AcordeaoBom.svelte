<script>
  let { k } = $props();
  let aberto = $state(false);
</script>

<div>
  <button type="button" id="{k}-gatilho" aria-expanded={aberto} aria-controls="{k}-painel" onclick={() => (aberto = !aberto)}>
    Prazo de entrega
  </button>
  <div id="{k}-painel" hidden={!aberto}><p>Cinco dias úteis.</p></div>
</div>
