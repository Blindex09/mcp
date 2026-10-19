<script>
  let { k } = $props();
  let aberto = $state(false);
</script>

<!-- Aparece na tela, mas não é um diálogo: sem papel, sem nome, sem foco, sem Escape. -->
<div>
  <button type="button" id="{k}-gatilho" onclick={() => (aberto = true)}>Excluir projeto</button>
  {#if aberto}
    <div class="caixa-falsa">
      <p>Excluir este projeto?</p>
      <button type="button" onclick={() => (aberto = false)}>Cancelar</button>
    </div>
  {/if}
</div>
