// Exemplos em Vue 3.5. Cada trecho entre "#region nome" e "#endregion" aparece como código na página do exemplo.
// O pacote monta cada componente no elemento [data-exemplo="nome"] que a página tiver.
import { createApp, nextTick, ref, useId } from 'vue';

//#region acordeao-ruim
const AcordeaoRuim = {
  props: ['k'],
  setup() { return { aberto: ref(false) }; },
  // div com @click: sem papel, sem foco, sem Enter/Espaço e sem estado.
  template: `<div>
    <div :id="k + '-gatilho'" class="fake-botao" @click="aberto = !aberto">Prazo de entrega</div>
    <p v-if="aberto" :id="k + '-painel'">Cinco dias úteis.</p>
  </div>`,
};
//#endregion

//#region acordeao-bom
const AcordeaoBom = {
  props: ['k'],
  setup() { return { aberto: ref(false) }; },
  template: `<div>
    <button type="button" :id="k + '-gatilho'" :aria-expanded="aberto" :aria-controls="k + '-painel'" @click="aberto = !aberto">Prazo de entrega</button>
    <div :id="k + '-painel'" :hidden="!aberto"><p>Cinco dias úteis.</p></div>
  </div>`,
};
//#endregion

//#region dialogo-ruim
const DialogoRuim = {
  props: ['k'],
  setup() { return { aberto: ref(false) }; },
  // Aparece na tela, mas não é um diálogo: sem papel, sem nome, sem foco, sem Escape.
  template: `<div>
    <button type="button" :id="k + '-gatilho'" @click="aberto = true">Excluir projeto</button>
    <div v-if="aberto" class="caixa-falsa"><p>Excluir este projeto?</p><button type="button" @click="aberto = false">Cancelar</button></div>
  </div>`,
};
//#endregion

//#region dialogo-bom
const DialogoBom = {
  props: ['k'],
  setup() { return { dialogo: ref(null), titulo: useId() }; },
  // <dialog> + showModal(): papel, foco preso, Escape e devolução do foco vêm do navegador.
  template: `<div>
    <button type="button" :id="k + '-gatilho'" @click="dialogo.showModal()">Excluir projeto</button>
    <dialog ref="dialogo" :aria-labelledby="titulo">
      <h3 :id="titulo">Excluir este projeto?</h3><p>Isso não pode ser desfeito.</p>
      <button type="button" @click="dialogo.close()">Cancelar</button>
    </dialog>
  </div>`,
};
//#endregion

//#region erro-ruim
const ErroRuim = {
  props: ['k'],
  setup() {
    const mensagem = ref('');
    const enviar = (e) => { mensagem.value = e.target.elements.email.value ? '' : 'Informe o e-mail.'; };
    return { mensagem, enviar };
  },
  // Texto vermelho solto: o campo não é marcado, a frase não está ligada a ele, o foco não se move.
  template: `<form novalidate @submit.prevent="enviar">
    <label :for="k + '-email'">E-mail</label>
    <input :id="k + '-email'" name="email" type="email" required> <span class="erro-visual">{{ mensagem }}</span>
    <p><button type="submit" :id="k + '-enviar'">Enviar</button></p>
  </form>`,
};
//#endregion

//#region erro-bom
const ErroBom = {
  props: ['k'],
  setup() {
    const mensagem = ref('');
    const campo = ref(null);
    const idErro = useId();
    const enviar = async () => {
      if (campo.value.value) { mensagem.value = ''; return; }
      mensagem.value = 'Informe o e-mail.';
      await nextTick();
      campo.value.focus(); // o foco vai ao campo com erro
    };
    return { mensagem, campo, idErro, enviar };
  },
  template: `<form novalidate @submit.prevent="enviar">
    <label :for="k + '-email'">E-mail</label>
    <input :id="k + '-email'" ref="campo" type="email" required :aria-invalid="mensagem ? 'true' : null" :aria-describedby="idErro">
    <span :id="idErro" class="erro-visual" role="alert">{{ mensagem }}</span>
    <p><button type="submit" :id="k + '-enviar'">Enviar</button></p>
  </form>`,
};
//#endregion

//#region status-ruim
const StatusRuim = {
  props: ['k'],
  setup() { return { salvo: ref(false) }; },
  // v-if: a região viva só existe quando há texto. Nasce junto com a mensagem e muitos leitores de tela não falam.
  template: `<div>
    <button type="button" :id="k + '-salvar'" @click="salvo = true">Salvar</button>
    <div v-if="salvo" role="status">Salvo com sucesso</div>
  </div>`,
};
//#endregion

//#region status-bom
const StatusBom = {
  props: ['k'],
  setup() { return { salvo: ref(false) }; },
  // A região fica sempre na página; só o texto muda.
  template: `<div>
    <button type="button" :id="k + '-salvar'" @click="salvo = true">Salvar</button>
    <div role="status">{{ salvo ? 'Salvo com sucesso' : '' }}</div>
  </div>`,
};
//#endregion

//#region rota-ruim
const RotaRuim = {
  props: ['k'],
  setup() { return { tela: ref('inicio') }; },
  // O conteúdo troca, mas o título da aba, o foco e o aviso continuam como estavam.
  template: `<div>
    <p><button type="button" :id="k + '-ir'" @click="tela = 'contato'">Contato</button></p>
    <main>
      <template v-if="tela === 'inicio'"><h1>Início</h1><p>Bem-vindo à loja de chás.</p></template>
      <template v-else><h1>Contato</h1><p>Escreva para contato@loja.example.</p></template>
    </main>
  </div>`,
};
//#endregion

//#region rota-bom
const RotaBom = {
  props: ['k'],
  setup() {
    const tela = ref('inicio');
    const titulo = ref(null);
    const ir = async () => {
      tela.value = 'contato';
      await nextTick(); // espera o DOM novo antes de mexer no foco
      document.title = 'Contato | Loja de chás'; // título da aba
      titulo.value.focus(); // foco no novo título
    };
    return { tela, titulo, ir };
  },
  template: `<div>
    <p><button type="button" :id="k + '-ir'" @click="ir">Contato</button></p>
    <main>
      <h1 ref="titulo" tabindex="-1">{{ tela === 'inicio' ? 'Início' : 'Contato' }}</h1>
      <p>{{ tela === 'inicio' ? 'Bem-vindo à loja de chás.' : 'Escreva para contato@loja.example.' }}</p>
    </main>
    <div role="status" class="so-leitor">{{ tela === 'contato' ? 'Página Contato carregada' : '' }}</div>
  </div>`,
};
//#endregion

const componentes = {
  'acordeao-ruim': AcordeaoRuim, 'acordeao-bom': AcordeaoBom,
  'dialogo-ruim': DialogoRuim, 'dialogo-bom': DialogoBom,
  'erro-ruim': ErroRuim, 'erro-bom': ErroBom,
  'status-ruim': StatusRuim, 'status-bom': StatusBom,
  'rota-ruim': RotaRuim, 'rota-bom': RotaBom,
};

document.querySelectorAll('[data-exemplo]').forEach((el) => {
  const Componente = componentes[el.dataset.exemplo];
  if (Componente) createApp(Componente, { k: el.dataset.exemplo }).mount(el);
});
