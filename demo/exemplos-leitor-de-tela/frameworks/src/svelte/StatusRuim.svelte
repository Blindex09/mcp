<script>
  let { k } = $props();
  let salvo = $state(false);
</script>

<!-- {#if}: a região viva só existe quando há texto. Nasce junto com a mensagem e muitos leitores de tela não falam. -->
<div>
  <button type="button" id="{k}-salvar" onclick={() => (salvo = true)}>Salvar</button>
  {#if salvo}<div role="status">Salvo com sucesso</div>{/if}
</div>
