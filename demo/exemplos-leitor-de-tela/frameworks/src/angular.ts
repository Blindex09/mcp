// Exemplos em Angular 20 (componentes standalone, compilação JIT no pacote). Cada trecho entre "#region nome" e "#endregion"
// aparece como código na página do exemplo. O pacote monta cada componente no elemento [data-exemplo="nome"] da página.
import '@angular/compiler';
import { Component, ElementRef, Input, createComponent, inject, provideZonelessChangeDetection, signal } from '@angular/core';
import type { ComponentRef, EnvironmentInjector, Type } from '@angular/core';
import { createApplication } from '@angular/platform-browser';
import { LiveAnnouncer } from '@angular/cdk/a11y';

//#region acordeao-ruim
@Component({
  selector: 'acordeao-ruim',
  standalone: true,
  // div com (click): sem papel, sem foco, sem Enter/Espaço e sem estado.
  template: `<div>
    <div [id]="k + '-gatilho'" class="fake-botao" (click)="aberto.set(!aberto())">Prazo de entrega</div>
    @if (aberto()) { <p [id]="k + '-painel'">Cinco dias úteis.</p> }
  </div>`,
})
class AcordeaoRuim { @Input() k = 'acordeao-ruim'; aberto = signal(false); }
//#endregion

//#region acordeao-bom
@Component({
  selector: 'acordeao-bom',
  standalone: true,
  template: `<div>
    <button type="button" [id]="k + '-gatilho'" [attr.aria-expanded]="aberto()" [attr.aria-controls]="k + '-painel'" (click)="aberto.set(!aberto())">Prazo de entrega</button>
    <div [id]="k + '-painel'" [hidden]="!aberto()"><p>Cinco dias úteis.</p></div>
  </div>`,
})
class AcordeaoBom { @Input() k = 'acordeao-bom'; aberto = signal(false); }
//#endregion

//#region dialogo-ruim
@Component({
  selector: 'dialogo-ruim',
  standalone: true,
  // Aparece na tela, mas não é um diálogo: sem papel, sem nome, sem foco, sem Escape.
  template: `<div>
    <button type="button" [id]="k + '-gatilho'" (click)="aberto.set(true)">Excluir projeto</button>
    @if (aberto()) { <div class="caixa-falsa"><p>Excluir este projeto?</p><button type="button" (click)="aberto.set(false)">Cancelar</button></div> }
  </div>`,
})
class DialogoRuim { @Input() k = 'dialogo-ruim'; aberto = signal(false); }
//#endregion

//#region dialogo-bom
@Component({
  selector: 'dialogo-bom',
  standalone: true,
  // <dialog> + showModal(): papel, foco preso, Escape e devolução do foco vêm do navegador.
  template: `<div>
    <button type="button" [id]="k + '-gatilho'" (click)="abrir()">Excluir projeto</button>
    <dialog [attr.aria-labelledby]="k + '-titulo'">
      <h3 [id]="k + '-titulo'">Excluir este projeto?</h3><p>Isso não pode ser desfeito.</p>
      <button type="button" (click)="fechar()">Cancelar</button>
    </dialog>
  </div>`,
})
class DialogoBom {
  @Input() k = 'dialogo-bom';
  private raiz: HTMLElement = inject(ElementRef).nativeElement;
  abrir() { (this.raiz.querySelector('dialog') as HTMLDialogElement).showModal(); }
  fechar() { (this.raiz.querySelector('dialog') as HTMLDialogElement).close(); }
}
//#endregion

//#region erro-ruim
@Component({
  selector: 'erro-ruim',
  standalone: true,
  // Texto vermelho solto: o campo não é marcado, a frase não está ligada a ele, o foco não se move.
  template: `<form novalidate (submit)="enviar($event)">
    <label [for]="k + '-email'">E-mail</label>
    <input [id]="k + '-email'" name="email" type="email" required> <span class="erro-visual">{{ mensagem() }}</span>
    <p><button type="submit" [id]="k + '-enviar'">Enviar</button></p>
  </form>`,
})
class ErroRuim {
  @Input() k = 'erro-ruim';
  mensagem = signal('');
  enviar(e: Event) {
    e.preventDefault();
    const campo = (e.target as HTMLFormElement).elements.namedItem('email') as HTMLInputElement;
    this.mensagem.set(campo.value ? '' : 'Informe o e-mail.');
  }
}
//#endregion

//#region erro-bom
@Component({
  selector: 'erro-bom',
  standalone: true,
  template: `<form novalidate (submit)="enviar($event)">
    <label [for]="k + '-email'">E-mail</label>
    <input [id]="k + '-email'" name="email" type="email" required [attr.aria-invalid]="mensagem() ? 'true' : null" [attr.aria-describedby]="k + '-erro'">
    <span [id]="k + '-erro'" class="erro-visual" role="alert">{{ mensagem() }}</span>
    <p><button type="submit" [id]="k + '-enviar'">Enviar</button></p>
  </form>`,
})
class ErroBom {
  @Input() k = 'erro-bom';
  mensagem = signal('');
  enviar(e: Event) {
    e.preventDefault();
    const campo = (e.target as HTMLFormElement).elements.namedItem('email') as HTMLInputElement;
    if (campo.value) { this.mensagem.set(''); return; }
    this.mensagem.set('Informe o e-mail.');
    campo.focus(); // o foco vai ao campo com erro
  }
}
//#endregion

//#region status-ruim
@Component({
  selector: 'status-ruim',
  standalone: true,
  // @if: a região viva só existe quando há texto. Nasce junto com a mensagem e muitos leitores de tela não falam.
  template: `<div>
    <button type="button" [id]="k + '-salvar'" (click)="salvo.set(true)">Salvar</button>
    @if (salvo()) { <div role="status">Salvo com sucesso</div> }
  </div>`,
})
class StatusRuim { @Input() k = 'status-ruim'; salvo = signal(false); }
//#endregion

//#region status-bom
@Component({
  selector: 'status-bom',
  standalone: true,
  // A região fica sempre na página; só o texto muda.
  template: `<div>
    <button type="button" [id]="k + '-salvar'" (click)="salvo.set(true)">Salvar</button>
    <div role="status">{{ salvo() ? 'Salvo com sucesso' : '' }}</div>
  </div>`,
})
class StatusBom { @Input() k = 'status-bom'; salvo = signal(false); }
//#endregion

//#region rota-ruim
@Component({
  selector: 'rota-ruim',
  standalone: true,
  // O conteúdo troca, mas o título da aba, o foco e o aviso continuam como estavam.
  template: `<div>
    <p><button type="button" [id]="k + '-ir'" (click)="tela.set('contato')">Contato</button></p>
    <main>
      @if (tela() === 'inicio') { <h1>Início</h1><p>Bem-vindo à loja de chás.</p> }
      @else { <h1>Contato</h1><p>Escreva para contato@loja.example.</p> }
    </main>
  </div>`,
})
class RotaRuim { @Input() k = 'rota-ruim'; tela = signal('inicio'); }
//#endregion

//#region rota-bom
@Component({
  selector: 'rota-bom',
  standalone: true,
  template: `<div>
    <p><button type="button" [id]="k + '-ir'" (click)="ir()">Contato</button></p>
    <main>
      <h1 tabindex="-1">{{ tela() === 'inicio' ? 'Início' : 'Contato' }}</h1>
      <p>{{ tela() === 'inicio' ? 'Bem-vindo à loja de chás.' : 'Escreva para contato@loja.example.' }}</p>
    </main>
  </div>`,
})
class RotaBom {
  @Input() k = 'rota-bom';
  tela = signal('inicio');
  private raiz: HTMLElement = inject(ElementRef).nativeElement;
  private anunciador = inject(LiveAnnouncer); // cria a região aria-live na criação do serviço, antes de qualquer texto
  ir() {
    this.tela.set('contato');
    // Depois que o Angular atualizar o DOM: título da aba, foco no novo título e aviso para o leitor de tela.
    setTimeout(() => {
      document.title = 'Contato | Loja de chás';
      (this.raiz.querySelector('h1') as HTMLElement).focus();
      void this.anunciador.announce('Página Contato carregada', 'polite');
    });
  }
}
//#endregion

const componentes: Record<string, Type<unknown>> = {
  'acordeao-ruim': AcordeaoRuim, 'acordeao-bom': AcordeaoBom,
  'dialogo-ruim': DialogoRuim, 'dialogo-bom': DialogoBom,
  'erro-ruim': ErroRuim, 'erro-bom': ErroBom,
  'status-ruim': StatusRuim, 'status-bom': StatusBom,
  'rota-ruim': RotaRuim, 'rota-bom': RotaBom,
};

createApplication({ providers: [provideZonelessChangeDetection()] }).then((app) => {
  const injetor = app.injector as EnvironmentInjector;
  document.querySelectorAll<HTMLElement>('[data-exemplo]').forEach((el) => {
    const Componente = componentes[el.dataset.exemplo ?? ''];
    if (!Componente) return;
    const ref: ComponentRef<unknown> = createComponent(Componente, { hostElement: el, environmentInjector: injetor });
    ref.setInput('k', el.dataset.exemplo);
    app.attachView(ref.hostView);
  });
});
