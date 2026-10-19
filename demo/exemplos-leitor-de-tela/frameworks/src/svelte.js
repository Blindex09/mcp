// Exemplos em Svelte 5. Cada componente fica em src/svelte/<Nome>.svelte e é montado no elemento [data-exemplo="nome"] da página.
import { mount } from 'svelte';
import AcordeaoRuim from './svelte/AcordeaoRuim.svelte';
import AcordeaoBom from './svelte/AcordeaoBom.svelte';
import DialogoRuim from './svelte/DialogoRuim.svelte';
import DialogoBom from './svelte/DialogoBom.svelte';
import ErroRuim from './svelte/ErroRuim.svelte';
import ErroBom from './svelte/ErroBom.svelte';
import StatusRuim from './svelte/StatusRuim.svelte';
import StatusBom from './svelte/StatusBom.svelte';
import RotaRuim from './svelte/RotaRuim.svelte';
import RotaBom from './svelte/RotaBom.svelte';

const componentes = {
  'acordeao-ruim': AcordeaoRuim, 'acordeao-bom': AcordeaoBom,
  'dialogo-ruim': DialogoRuim, 'dialogo-bom': DialogoBom,
  'erro-ruim': ErroRuim, 'erro-bom': ErroBom,
  'status-ruim': StatusRuim, 'status-bom': StatusBom,
  'rota-ruim': RotaRuim, 'rota-bom': RotaBom,
};

document.querySelectorAll('[data-exemplo]').forEach((el) => {
  const Componente = componentes[el.dataset.exemplo];
  if (Componente) mount(Componente, { target: el, props: { k: el.dataset.exemplo } });
});
