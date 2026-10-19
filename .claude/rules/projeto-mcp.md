---
paths:
  - "accessibility_mcp/**"
  - "mcp_server.py"
  - "docs/**"
  - "tests/**"
---

# Regras específicas do projeto MCP de acessibilidade

> Carrega quando se mexe no servidor, nas ferramentas, no conteúdo ou nos testes.

### Nicho (regra 5)

Acessibilidade digital (web, mobile, interfaces de IA e agentes). Um pedido fora dela é recusado com educação, como descreve a regra 5; a recusa vem do modelo.

### Interfaces que executam tarefas (regra 14)

As ferramentas do servidor MCP. Toda funcionalidade de comportamento vale em todas elas, na mesma entrega, qualquer que seja o cliente.

### O servidor não chama modelo (decisão do dono de 19/out/2026)

O modelo é o do cliente que usa o servidor (Claude Code, Codex, VS Code, Cursor, Claude Desktop). O servidor não tem provedor, chave, roteador, sampling nem
"usuário autônomo". Os fluxos de trabalho (revisão, tarefa como persona, componente, varredura, comparação, código acessível) são prompts do MCP e a
ferramenta `a11y_workflow`, que entrega o mesmo texto aos clientes que não mostram prompts (paridade, regra 14). O aprendizado é gravado pelo modelo do
cliente com `a11y_learn`, e os achados são registrados por ele com `a11y_finding`; o servidor só confere fatos (passos citados, elemento visto, critério real).
Qualquer ferramenta nova que precise de julgamento devolve fatos ou instruções e deixa o julgamento para o cliente.

### Julgamento é do modelo, medição é do servidor (regras 1 e 2)

O servidor mede fatos (árvore de acessibilidade, foco, contraste, axe-core) e impõe limites (persona sem mouse, aprovação de mutações, segurança,
fechamento da sessão). O que cada elemento é, onde a pessoa trava e o que melhorar são do modelo do cliente. Nada de palavra-chave, regex ou ranking lexical
para escolher guia ou decidir intenção; as descrições do `catalog.json` são escritas por IA e um teste falha se faltar ou sobrar entrada.

### Tempo e laços (regra 8)

Nenhum prazo fixo corta uma sessão, uma operação longa, uma instalação ou um rastreamento que continua avançando. O que encerra é: parar de avançar, o
cancelamento por `a11y_close` ou um orçamento que a própria pessoa configurou. O limite de ociosidade da sessão cresce com o ritmo da conversa e só
libera um navegador abandonado.

### Conhecimento (regra 10 e 18)

O conteúdo de `accessibility_mcp/a11y/content/` vem de fontes oficiais, com a data da consulta e o que não pôde ser lido declarado. Os guias de leitor de tela, ARIA,
frameworks, mobile, documentos e conformidade vieram do Qaaccessibility (mesma pesquisa), e os playbooks dos especialistas também: lá é a fonte, e uma mudança de lá
vem para cá na mesma entrega. O que é próprio do MCP (guias de como conduzir as ferramentas, sondas, fluxos, exemplos do site) nasce aqui e não é espelhado no Qaaccessibility
(decisão do dono de 19/out/2026, depois de comparar os dois projetos: o Qaaccessibility analisa o código com IA e entrega relatórios, correções e tickets; o MCP prova o comportamento no navegador). Mudança de
um guia, de um playbook ou do texto de um fluxo (`prompts.py`) é mudança de instrução ao modelo do cliente e segue o portão da regra 15; sem crédito de modelo para a avaliação ampla, ela é registrada como pendência.

### Edição de arquivos

`a11y_set_workspace`, `a11y_read_file`, `a11y_edit_file` e `a11y_undo_edit` editam só dentro da pasta de trabalho escolhida pela pessoa (escolhida pela pessoa na conversa com `a11y_set_workspace`; nada para configurar antes), com cópia de
segurança antes de cada edição, escrita atômica, conferência de sintaxe do que foi editado e aprovação quando a aprovação está ligada.

### Antes de testar acessibilidade ou mexer nas sondas

Ler o guia `testing-playbook-for-ai` (ordem das ferramentas, o que se pode e não se pode afirmar, erros já cometidos) e a matriz `component-behavior-matrix` (o que cada componente deve e não deve fazer, o que o leitor de tela recebe, qual sonda mede). Sonda nova ou alterada nasce com um par bom e ruim em `tests/test_probes.py` e no site `demo/exemplos-leitor-de-tela/`.

### O que pode e o que não pode, ao testar com o MCP

Pode afirmar o que o servidor mediu: papel, nome e estado na árvore, o efeito de uma tecla, onde ficou o foco, tamanhos, contraste, o que entrou numa região viva. Não pode afirmar a fala exata de um leitor de tela sem rodar o leitor, nem que um `met: null` passou, nem nada sobre Android ou iOS (sem executor aqui), nem que o produto está em conformidade. Não pode chamar um exemplo de ruim por algo que não mediu: usa a categoria "depende do navegador, não medido aqui". Não pode julgar por palavra-chave. Mede o componente como a pessoa o recebe (estilos do site, página já montada pelo framework) e espera a montagem por condição, nunca por tempo fixo. Detalhes e erros já cometidos: guia `testing-playbook-for-ai`.
