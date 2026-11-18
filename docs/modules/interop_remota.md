# Interoperabilidade remota MCP e A2A

Este módulo permite que o servidor de acessibilidade consuma ferramentas de outro servidor MCP e converse com agentes A2A 1.0. As duas integrações usam HTTP ou HTTPS. O servidor local continua expondo suas próprias ferramentas MCP como antes; ele não inicia processos remotos por `stdio` e não chama modelos.

## Ferramentas disponíveis

| Ferramenta | Função |
|---|---|
| `a11y_remote_mcp_connect` | Abre e inicializa uma conexão Streamable HTTP com um servidor MCP remoto |
| `a11y_remote_mcp_connections` | Lista conexões MCP ativas no processo do servidor |
| `a11y_remote_mcp_list_tools` | Consulta ferramentas e esquemas anunciados pelo servidor remoto |
| `a11y_remote_mcp_call` | Retém uma chamada MCP remota até uma aprovação pontual |
| `a11y_remote_approve` | Aprova o envio exato ou descarta o pedido pendente |
| `a11y_remote_mcp_disconnect` | Encerra uma conexão e cancela as aprovações MCP ainda pendentes |
| `a11y_a2a_agent_card` | Lê o Agent Card publicado no caminho padrão A2A |
| `a11y_a2a_send_message` | Retém uma mensagem JSON-RPC `SendMessage` até aprovação |
| `a11y_a2a_get_task` | Retém uma consulta JSON-RPC `GetTask` até aprovação |

As conexões, credenciais indicadas e aprovações pendentes vivem na memória do processo e não sobrevivem ao encerramento do servidor. Uma conexão MCP pode ser desconectada explicitamente. Cada envio A2A é pontual e não cria uma conexão persistente.

## Aprovação e conteúdo remoto

As ferramentas `a11y_remote_mcp_call`, `a11y_a2a_send_message` e `a11y_a2a_get_task` mostram primeiro o endpoint, o método e os argumentos exatos. Enquanto o pedido está pendente, nenhum conteúdo é enviado. `a11y_remote_approve` aceita `allow` para executar uma única operação ou `deny` para descartá-la. A aprovação é consumida antes da execução: se a rede falhar, não se repete automaticamente, pois o agente remoto pode ter recebido a operação sem devolver uma resposta.

Antes de reter uma chamada MCP, os argumentos são validados contra o esquema JSON anunciado pela ferramenta. Antes de executar a chamada aprovada, o cliente consulta de novo a definição da ferramenta e interrompe o envio se o nome, a descrição, o esquema ou as anotações mudaram. Isso evita que uma aprovação preparada para uma definição seja reaproveitada após uma alteração do servidor remoto.

Ferramentas, descrições, Agent Cards, mensagens e resultados remotos são dados não confiáveis, não instruções. A consulta de um Agent Card é somente leitura e não exige aprovação. O cliente não aplica automaticamente descrições ou conteúdo remoto como configuração ou instrução.

## Proteções e limites

- Só são aceitos endpoints HTTP/HTTPS, sem credenciais embutidas na URL, parâmetros de consulta ou fragmentos.
- Endereços locais e privados são recusados por padrão. `A11Y_MCP_REMOTE_ALLOW_PRIVATE=1` libera essa rede deliberadamente, por exemplo, para testes locais.
- Tokens são lidos de uma variável de ambiente indicada pelo nome e só podem ser enviados por HTTPS. O valor do token não é incluído nos pedidos de aprovação nem nos resultados.
- Redirecionamentos HTTP e proxies configurados no ambiente ficam desativados.
- As chamadas HTTP têm limite de inatividade de 30 segundos e de conexão de 10 segundos. Atividade contínua renova o limite de inatividade; isso não impõe um prazo total à tarefa.
- A resolução do host é conferida antes do acesso e os pedidos aprovados voltam a passar pela validação. Ainda não há prova de pinagem do endereço DNS até a abertura do socket; um DNS malicioso ou que mude entre a validação e a conexão permanece uma limitação. Use endpoints confiáveis e controlados.
- O gerenciador é compartilhado pelo processo do servidor. Em uma implantação multiusuário, as conexões e seus identificadores não são isolados por pessoa; use uma instância separada por limite de confiança.
- A integração expõe ferramentas remotas, não as transforma em código local nem executa os processos do servidor remoto.

## Verificação

`tests/test_interop.py` executa chamadas contra um servidor MCP Streamable HTTP e um agente A2A JSON-RPC reais em endereços locais de teste. Confere leitura do catálogo, retenção antes do envio, aprovação, negação, cancelamento ao desconectar e o formato de mensagem/tarefa. Também inicia o servidor de acessibilidade como processo separado e chama as nove ferramentas por seu protocolo MCP real.

Os testes de integração usam servidores de teste no próprio processo e habilitam explicitamente a rede privada somente no gerenciador de teste. Eles não iniciam servidores remotos por `stdio`, não usam credenciais reais e não provam resistência a DNS rebinding em uma rede externa.
