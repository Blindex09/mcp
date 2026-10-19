<script>
  import { tick } from 'svelte';
  let { k } = $props();
  let tela = $state('inicio');
  let titulo;
  async function ir() {
    tela = 'contato';
    await tick(); // espera o DOM novo antes de mexer no foco
    document.title = 'Contato | Loja de chás'; // título da aba
    titulo.focus(); // foco no novo título
  }
</script>

<div>
  <p><button type="button" id="{k}-ir" onclick={ir}>Contato</button></p>
  <main>
    <h1 bind:this={titulo} tabindex="-1">{tela === 'inicio' ? 'Início' : 'Contato'}</h1>
    <p>{tela === 'inicio' ? 'Bem-vindo à loja de chás.' : 'Escreva para contato@loja.example.'}</p>
  </main>
  <div role="status" class="so-leitor">{tela === 'contato' ? 'Página Contato carregada' : ''}</div>
</div>
