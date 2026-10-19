// Exemplos em React 19. Cada trecho entre "#region nome" e "#endregion" aparece como código na página do exemplo.
// O pacote monta cada componente no elemento [data-exemplo="nome"] que a página tiver.
import { useEffect, useId, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';

//#region acordeao-ruim
function AcordeaoRuim({ k }) {
  const [aberto, setAberto] = useState(false);
  // div com onClick: sem papel, sem foco, sem Enter/Espaço e sem estado.
  return (
    <div>
      <div id={`${k}-gatilho`} className="fake-botao" onClick={() => setAberto(!aberto)}>Prazo de entrega</div>
      {aberto && <p id={`${k}-painel`}>Cinco dias úteis.</p>}
    </div>
  );
}
//#endregion

//#region acordeao-bom
function AcordeaoBom({ k }) {
  const [aberto, setAberto] = useState(false);
  return (
    <div>
      <button type="button" id={`${k}-gatilho`} aria-expanded={aberto} aria-controls={`${k}-painel`} onClick={() => setAberto(!aberto)}>
        Prazo de entrega
      </button>
      <div id={`${k}-painel`} hidden={!aberto}><p>Cinco dias úteis.</p></div>
    </div>
  );
}
//#endregion

//#region dialogo-ruim
function DialogoRuim({ k }) {
  const [aberto, setAberto] = useState(false);
  // Aparece na tela, mas não é um diálogo: sem papel, sem nome, sem foco, sem Escape.
  return (
    <div>
      <button type="button" id={`${k}-gatilho`} onClick={() => setAberto(true)}>Excluir projeto</button>
      {aberto && (
        <div className="caixa-falsa">
          <p>Excluir este projeto?</p>
          <button type="button" onClick={() => setAberto(false)}>Cancelar</button>
        </div>
      )}
    </div>
  );
}
//#endregion

//#region dialogo-bom
function DialogoBom({ k }) {
  const dialogo = useRef(null);
  const titulo = useId();
  // <dialog> + showModal(): papel, foco preso, Escape e devolução do foco vêm do navegador.
  return (
    <div>
      <button type="button" id={`${k}-gatilho`} onClick={() => dialogo.current.showModal()}>Excluir projeto</button>
      <dialog ref={dialogo} aria-labelledby={titulo}>
        <h3 id={titulo}>Excluir este projeto?</h3>
        <p>Isso não pode ser desfeito.</p>
        <button type="button" onClick={() => dialogo.current.close()}>Cancelar</button>
      </dialog>
    </div>
  );
}
//#endregion

//#region erro-ruim
function ErroRuim({ k }) {
  const [mensagem, setMensagem] = useState('');
  const enviar = (e) => {
    e.preventDefault();
    setMensagem(e.currentTarget.elements.email.value ? '' : 'Informe o e-mail.');
  };
  // Texto vermelho solto: o campo não é marcado, a frase não está ligada a ele, o foco não se move.
  return (
    <form noValidate onSubmit={enviar}>
      <label htmlFor={`${k}-email`}>E-mail</label>
      <input id={`${k}-email`} name="email" type="email" required /> <span className="erro-visual">{mensagem}</span>
      <p><button type="submit" id={`${k}-enviar`}>Enviar</button></p>
    </form>
  );
}
//#endregion

//#region erro-bom
function ErroBom({ k }) {
  const [mensagem, setMensagem] = useState('');
  const campo = useRef(null);
  const idErro = useId();
  const enviar = (e) => {
    e.preventDefault();
    if (campo.current.value) { setMensagem(''); return; }
    setMensagem('Informe o e-mail.');
    campo.current.focus(); // o foco vai ao campo com erro
  };
  return (
    <form noValidate onSubmit={enviar}>
      <label htmlFor={`${k}-email`}>E-mail</label>
      <input id={`${k}-email`} ref={campo} type="email" required aria-invalid={mensagem ? 'true' : undefined} aria-describedby={idErro} />{' '}
      <span id={idErro} className="erro-visual" role="alert">{mensagem}</span>
      <p><button type="submit" id={`${k}-enviar`}>Enviar</button></p>
    </form>
  );
}
//#endregion

//#region status-ruim
function StatusRuim({ k }) {
  const [salvo, setSalvo] = useState(false);
  // A região viva só existe quando há texto: nasce junto com a mensagem e muitos leitores de tela não falam.
  return (
    <div>
      <button type="button" id={`${k}-salvar`} onClick={() => setSalvo(true)}>Salvar</button>
      {salvo && <div role="status">Salvo com sucesso</div>}
    </div>
  );
}
//#endregion

//#region status-bom
function StatusBom({ k }) {
  const [salvo, setSalvo] = useState(false);
  // A região fica sempre na página; só o texto muda.
  return (
    <div>
      <button type="button" id={`${k}-salvar`} onClick={() => setSalvo(true)}>Salvar</button>
      <div role="status">{salvo ? 'Salvo com sucesso' : ''}</div>
    </div>
  );
}
//#endregion

//#region rota-ruim
function RotaRuim({ k }) {
  const [tela, setTela] = useState('inicio');
  // O conteúdo troca, mas o título da aba, o foco e o aviso continuam como estavam.
  return (
    <div>
      <p><button type="button" id={`${k}-ir`} onClick={() => setTela('contato')}>Contato</button></p>
      <main>{tela === 'inicio' ? <><h1>Início</h1><p>Bem-vindo à loja de chás.</p></> : <><h1>Contato</h1><p>Escreva para contato@loja.example.</p></>}</main>
    </div>
  );
}
//#endregion

//#region rota-bom
function RotaBom({ k }) {
  const [tela, setTela] = useState('inicio');
  const titulo = useRef(null);
  const primeira = useRef(true);
  useEffect(() => {
    if (primeira.current) { primeira.current = false; return; }
    document.title = 'Contato | Loja de chás'; // título da aba
    titulo.current.focus(); // foco no novo título
  }, [tela]);
  return (
    <div>
      <p><button type="button" id={`${k}-ir`} onClick={() => setTela('contato')}>Contato</button></p>
      <main>
        <h1 ref={titulo} tabIndex={-1}>{tela === 'inicio' ? 'Início' : 'Contato'}</h1>
        <p>{tela === 'inicio' ? 'Bem-vindo à loja de chás.' : 'Escreva para contato@loja.example.'}</p>
      </main>
      <div role="status" className="so-leitor">{tela === 'contato' ? 'Página Contato carregada' : ''}</div>
    </div>
  );
}
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
  if (Componente) createRoot(el).render(<Componente k={el.dataset.exemplo} />);
});
