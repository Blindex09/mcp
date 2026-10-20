# Auditoria do MCP de acessibilidade

Estado da arquitetura em 20/10/2026

O servidor fornece conhecimento, medições e operações de acessibilidade pelo protocolo MCP. O modelo do cliente escolhe os guias, conduz os testes, interpreta os fatos e propõe correções. O servidor não chama modelo e não exige chave de API.

Arquitetura vigente

O ponto de entrada mcp_server.py carrega accessibility_mcp/server.py. O servidor registra ferramentas e prompts, prepara o navegador em segundo plano e fecha a sessão ao encerrar. A comunicação usa stdio; os registros vão para stderr.

Os módulos tools.py, tools_ux.py e tools_files.py expõem conhecimento, medições, operações de navegador e edição de arquivos. session.py mantém a sessão e as restrições de persona. As sondas de probes.py e os scripts de js/ medem comportamento; o julgamento fica com o cliente. Nenhuma medição isolada certifica conformidade.

Os seis fluxos de prompts.py também estão disponíveis por a11y_workflow para clientes que não mostram prompts. Revisão e execução de tarefas são instruções para o modelo do cliente. O catálogo é entregue por a11y_list_content, com leitura de conteúdo sob demanda.

Os achados registrados pelo cliente citam passos do rastro. verify.py confere evidências objetivas; sem evidência válida, o achado permanece cantTell. As execuções podem ser guardadas, exportadas em JSON, EARL ou SARIF e comparadas. O aprendizado é gravado pelo cliente, com origem registrada, e pode ser listado ou removido.

A ferramenta a11y_check_page abre uma sessão descartável, mede o comportamento, executa as sondas solicitadas e fecha a sessão. Ela atende clientes que iniciam um novo processo do servidor em cada chamada. Recusa uma sessão persistente já aberta; pedidos de alteração de dados ficam retidos e são descartados ao encerrar.

Proteções

As personas limitam as ações disponíveis. Em sites externos, alterações de dados dependem do modo de aprovação da sessão. O editor fica dentro da pasta escolhida pela pessoa, protege arquivos sensíveis, mantém cópia de segurança e verifica a sintaxe das edições. A preparação do navegador e as esperas acompanham o progresso; cancelamento e falta de progresso encerram operações.

A instrumentação de telemetria registra a execução de ferramentas sem argumentos nem resultados. A configuração é opcional. O servidor não tem provedor, resolução de modelos, roteador de modelos ou laço próprio de raciocínio.

Evidências e limites

Os contratos das ferramentas e dos seis prompts são verificados em tests/test_server.py. O teste tests/test_e2e_protocol.py usa o protocolo MCP real e remove as chaves de provedores do ambiente do processo. Os testes de sondas, sessão, edição, achados e chamada única estão nas respectivas suítes de tests/. A matriz em docs/COBERTURA_2026.json registra a data e o resultado da sua própria execução; ela não equivale à aprovação de todos os conceitos.

Continuam pendentes a avaliação ampla dos guias e fluxos com modelos de clientes, com tentativas repetidas e ablação, e a revisão do harness a cada geração de modelo. O projeto não implementa cliente MCP nem delegação A2A. Não há executor Android ou iOS, nem prova de Safari com VoiceOver. O NVDA real depende de uma VM configurada; a árvore do navegador não prova a fala exata de um leitor de tela.

A integração com o Qaaccessibility usa a11y_check_page para provar comportamento. A decisão do roteador daquele projeto, seu custo de contexto e a avaliação das instruções dele precisam ser comprovados naquele projeto. Os playbooks de especialistas e guias de leitor de tela têm o Qaaccessibility como fonte; os roteiros e sondas próprios do MCP permanecem aqui.

Limpeza de 20/10/2026

A documentação da arquitetura anterior foi retirada deste arquivo e da demonstração da loja. Os módulos de provedor, roteamento e execução autônoma já não faziam parte do código versionado. A regra de interface deixou de apontar para o módulo removido. Os registros históricos anteriores continuam disponíveis no Git.

Esta limpeza altera documentação e o escopo de uma regra local; não altera ferramentas, prompts nem comportamento do servidor. Verificação desta entrega: ruff check . e mypy passaram (27 arquivos de código verificados pelo mypy); os sete testes de tests/test_server.py e tests/test_e2e_protocol.py passaram em 33,52 segundos, incluindo o protocolo MCP real. A suíte completa de 303 testes foi iniciada, mas interrompida depois de deixar de produzir resultados nas verificações com navegador; não foi concluída. A matriz foi executada: 11 de 14 conceitos cobertos e três lacunas declaradas; o comando retornou código 1 por essas lacunas. Não houve mudança de código, de guia ou de texto de fluxo.
