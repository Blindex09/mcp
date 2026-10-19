<script>
  let { k } = $props();
  let salvo = $state(false);
</script>

<!-- A região fica sempre na página; só o texto muda. -->
<div>
  <button type="button" id="{k}-salvar" onclick={() => (salvo = true)}>Salvar</button>
  <div role="status">{salvo ? 'Salvo com sucesso' : ''}</div>
</div>
