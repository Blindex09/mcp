# Sessão aberta do NVDA e navegação por atalhos

Registro de 13/11/2026. Código em `nvda/sessao.mjs`, `nvda/walk.mjs`, `nvda/vm/agent.mjs`, `accessibility_mcp/a11y/nvda_vm.py` e `accessibility_mcp/a11y/tools_ux.py`.

## Por que existe

O percurso fixo (`a11y_nvda_speech`) tem limites por chamada e roteiro decidido antes de ouvir a página. Em página grande, com muitas imagens, títulos ou campos, ele para no limite e não deixa quem usa o MCP decidir o próximo passo. A sessão aberta resolve isso: o modelo do cliente conduz o NVDA passo a passo, como uma pessoa, e decide cada movimento pelo que o NVDA acabou de falar. O servidor não julga nada; mede e limita.

## Ferramentas

- `a11y_nvda_open(url)`: liga o NVDA e o navegador na VM e mantém a sessão. Uma sessão por vez. Fecha sozinha após 10 minutos sem comandos (inatividade, não duração da tarefa).
- `a11y_nvda_do(action, ...)`: um passo. Ações:
  - `tab`: Tab, ou Shift+Tab com `reverse`.
  - `key`: tecla de navegação do modo leitura (H, D, K, F, B, L, T, G, E, X, C, R, I, U, V, N, Q, S, M, O, A, W, vírgula para sair de contêiner, 1 a 6, Shift+letra para voltar), navegação por células de tabela (`ctrl+alt+down`/`up`/`left`/`right` ou `ctrl+alt+seta_baixo`/`seta_cima`/`seta_esquerda`/`seta_direita`), nomes de categoria (headings, links, fields etc.) ou teclas como setas, Enter, Espaço, Escape, Home, End, PageUp, PageDown, Alt+seta para baixo.
  - `wait`: espera de 50 a 30000 ms e devolve a fala que assentou, para AJAX, regiões ativas e mensagens que aparecem depois.
  - `mode`: navegação, foco ou alternar.
  - `top`, `go` (outra URL na mesma sessão, para cobrir várias páginas) e `state`.
  - `activate` e `type`: mudam o site; exigem `authorized=true`, que só se passa com o sim da pessoa.
- `a11y_nvda_close`: encerra NVDA e navegador.

Com `until_end`, a tecla se repete até o limite da chamada (`maximum`, no máximo 500) ou até a mesma fala se repetir duas vezes seguidas depois da primeira (`REPETICOES_PARA_FIM = 2`, totalizando 3 falas idênticas consecutivas). A resposta traz `parou_por` (`repetiu`, `maximo` ou `quantidade`) e `continua=true` quando o limite acabou antes do fim: chamando de novo, a navegação segue exatamente de onde parou.

## Decisão de projeto: sem julgar o texto

A parada por fim de lista usa só um fato: o NVDA falou a mesma coisa três vezes consecutivas (duas repetições seguidas após a primeira), ou seja, o cursor não saiu do lugar, sem cortar listas legítimas que tenham dois itens vizinhos com o mesmo rótulo (como dois links "Leia mais" seguidos). Uma versão anterior procurava trechos como "sem próximo" na fala. Foi removida, porque julgar sentido por palavra-chave contraria a regra 2 do CLAUDE.md (e no NVDA em português o anúncio real observado na VM foi "sem marco seguinte"). Quem interpreta a fala é o modelo do cliente.

## Limites conhecidos

- A ação `mode` com `focus` usa a tecla que alterna (NVDA+Espaço). Se o NVDA já estiver em modo foco, volta ao modo navegação. O servidor não detecta o modo atual: confira a fala do NVDA no retorno.
- Se a fala nunca repetir (página com conteúdo que muda a cada passo), o limite `maximum` encerra a chamada.

## Verificação realizada

- Node: 20 testes em `nvda/focus.test.mjs` e `nvda/vm/agent.test.mjs`, com NVDA e navegador simulados.
- Python: 10 testes em `tests/test_nvda_vm.py` (agente simulado real, sessão retomada, duas repetições seguidas para fim, autorização, espera e modo) e `tests/test_server.py` (lista de ferramentas), mais ruff e mypy limpos.
- Verificação ao vivo na VM Windows 11 (o agente em `A11Y_MCP_NVDA_VM`) com o NVDA real sobre `https://blindhelp.net/`:
  - `session_open` abriu a sessão, maximizou a janela (`1358x636`) e devolveu o título original da página.
  - Primeiro lote com `tecla: "H"`, `ate_fim: true`, `maximo: 5` percorreu os 5 primeiros títulos (`Search form, título, nível 2` até `Welcome, título, nível 1`) e devolveu `parou_por: "maximo"` e `continua: true`.
  - Segundo lote com `tecla: "H"`, `ate_fim: true`, `maximo: 3` retomou exatamente do 6º título (`Help keep Blind Help Project going, título, nível 2`, `Introducing Free Membership of Book Share for Pakistanis...`, `Popular on BHP, título, nível 2`), sem recomeçar do topo.
  - `topo` seguido de `tecla: "D"`, `ate_fim: true`, `maximo: 5` anunciou `Main navigation, navegação marco, Main navigation` e depois `sem marco seguinte` três vezes seguidas, encerrando sozinho no passo 4 com `parou_por: "repetiu"` e `continua: false`.
  - `esperar` (500 ms), `modo` (`navegacao`) e `session_close` executaram sem erro (`fechada: true`, `erroAoParar: null`).
