<script>
  let { k } = $props();
  let dialogo;
</script>

<!-- <dialog> + showModal(): papel, foco preso, Escape e devolução do foco vêm do navegador. -->
<div>
  <button type="button" id="{k}-gatilho" onclick={() => dialogo.showModal()}>Excluir projeto</button>
  <dialog bind:this={dialogo} aria-labelledby="{k}-titulo">
    <h3 id="{k}-titulo">Excluir este projeto?</h3>
    <p>Isso não pode ser desfeito.</p>
    <button type="button" onclick={() => dialogo.close()}>Cancelar</button>
  </dialog>
</div>
