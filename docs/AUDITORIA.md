# Auditoria do MCP de acessibilidade

Estado da arquitetura em 20/10/2026

Atualização de 21/10/2026

A demonstração agora inclui documentos.html, com nove assuntos, 12 DOCX e 18 PDFs bons e ruins de propósito. Os contratos e fontes oficiais ficam em content/assets/document-examples.json e geram o guia document-behavior-matrix, acessível no catálogo MCP. A base contém 72 guias. A página distingue medidas estruturais, comportamento esperado e fala real, que ainda não foi capturada nos aplicativos de documentos. A entrega e as evidências estão em docs/modules/galeria_documentos.md e galeria_documentos_evidencias.json.

O uso real encontrou e corrigiu uma falha no validador de PDF: o retorno nulo de um título vazio era convertido no texto None e escapava da checagem. O caso agora está na regressão. A nova galeria foi conferida por teclado, download e inspeção visual dos arquivos, sem alterar as proteções de download do servidor.

Verificação da atualização: ruff e mypy passaram; regressão conjunta com 345 testes aprovados e um ignorado; rodada específica final com 79 aprovados. A matriz permanece em 11 cobertos, um parcial e duas lacunas declaradas. O guia teve 48/48 decisões aceitas com ele e 48/48 sem ele no conjunto sintético, sem ganho demonstrado. O limite da tentativa adicional de Firefox pelo MCP e da navegação WebKit está documentado no módulo.

O servidor fornece conhecimento, medições e operações de acessibilidade pelo protocolo MCP. O modelo do cliente escolhe os guias, conduz os testes, interpreta os fatos e propõe correções. O servidor não chama modelo e não exige chave de API.

Arquitetura vigente

O ponto de entrada mcp_server.py carrega accessibility_mcp/server.py. O servidor registra ferramentas e prompts, prepara o navegador em segundo plano e fecha a sessão ao encerrar. A comunicação usa stdio; os registros vão para stderr.

Os módulos tools.py, tools_ux.py e tools_files.py expõem conhecimento, medições, operações de navegador e edição de arquivos. session.py mantém a sessão e as restrições de persona. As sondas de probes.py e os scripts de js/ medem comportamento; o julgamento fica com o cliente. Nenhuma medição isolada certifica conformidade.

Os sete fluxos de prompts.py também estão disponíveis por a11y_workflow para clientes que não mostram prompts. Revisão, execução de tarefas e criação de documentos são instruções para o modelo do cliente. O catálogo é entregue por a11y_list_content, com leitura de conteúdo sob demanda.

Os achados registrados pelo cliente citam passos do rastro. verify.py confere evidências objetivas; sem evidência válida, o achado permanece cantTell. As execuções podem ser guardadas, exportadas em JSON, EARL ou SARIF e comparadas. O aprendizado é gravado pelo cliente, com origem registrada, e pode ser listado ou removido.

A ferramenta a11y_check_page abre uma sessão descartável, mede o comportamento, executa as sondas solicitadas e fecha a sessão. Ela atende clientes que iniciam um novo processo do servidor em cada chamada. Recusa uma sessão persistente já aberta; pedidos de alteração de dados ficam retidos e são descartados ao encerrar.

Proteções

As personas limitam as ações disponíveis. Em sites externos, alterações de dados dependem do modo de aprovação da sessão. O editor fica dentro da pasta escolhida pela pessoa, protege arquivos sensíveis, mantém cópia de segurança e verifica a sintaxe das edições. A preparação do navegador e as esperas acompanham o progresso; cancelamento e falta de progresso encerram operações.

A instrumentação de telemetria registra a execução de ferramentas sem argumentos nem resultados. A configuração é opcional. O servidor não tem provedor, resolução de modelos, roteador de modelos ou laço próprio de raciocínio.

Evidências e limites

Os contratos das ferramentas e dos sete prompts são verificados em tests/test_server.py. O teste tests/test_e2e_protocol.py usa o protocolo MCP real e remove as chaves de provedores do ambiente do processo. Os testes de sondas, sessão, edição, achados e chamada única estão nas respectivas suítes de tests/. A matriz em docs/COBERTURA_2026.json registra a data e o resultado da sua própria execução; ela não equivale à aprovação de todos os conceitos.

Continuam pendentes a avaliação ampla dos guias e fluxos com modelos de clientes e a revisão do harness a cada geração de modelo. O guia de conformidade teve uma avaliação delimitada com oito cenários, três repetições e ablação, registrada em docs/modules/documentos_evidencias.json; ela não cobre os demais guias e modelos. O projeto não implementa cliente MCP nem delegação A2A. Não há executor Android ou iOS, nem prova de Safari com VoiceOver. O NVDA real depende de uma VM configurada; a árvore do navegador não prova a fala exata de um leitor de tela.

A integração com o Qaaccessibility usa a11y_check_page para provar comportamento. A decisão do roteador daquele projeto, seu custo de contexto e a avaliação das instruções dele precisam ser comprovados naquele projeto. Os playbooks de especialistas e guias de leitor de tela têm o Qaaccessibility como fonte; os roteiros e sondas próprios do MCP permanecem aqui.

Documentos em 20/10/2026

tools_documents.py expõe geração de DOCX e PDF com tags, validação estrutural e relatórios dos achados e da cobertura, com recursos MCP para baixar os bytes. O veraPDF verifica os requisitos automáticos PDF/UA-1; a revisão semântica, visual e com leitor de tela continua necessária. Contratos, evidências e limites estão em docs/modules/documentos_acessiveis.md. A geração foi chamada no Codex real e nesta conversa. Não há ainda galeria de documentos bons e ruins nem sonda da fala real do NVDA dentro do Word ou de um leitor de PDF.

Verificação: ruff e mypy aprovados; regressão completa com 329 testes aprovados e um ignorado; rodada específica final com 40 testes aprovados. A matriz registra 11 conceitos cobertos, um parcial e duas lacunas. Os três PDFs do roteiro ao vivo passaram no veraPDF; os DOCX também foram abertos e renderizados no Word para revisão visual.

Limpeza de 20/10/2026

A documentação da arquitetura anterior foi retirada deste arquivo e da demonstração da loja. Os módulos de provedor, roteamento e execução autônoma já não faziam parte do código versionado. A regra de interface deixou de apontar para o módulo removido. Os registros históricos anteriores continuam disponíveis no Git.

Esta limpeza altera documentação e o escopo de uma regra local; não altera ferramentas, prompts nem comportamento do servidor. Verificação desta entrega: ruff check . e mypy passaram (27 arquivos de código verificados pelo mypy); os sete testes de tests/test_server.py e tests/test_e2e_protocol.py passaram em 33,52 segundos, incluindo o protocolo MCP real. A suíte completa de 303 testes foi iniciada, mas interrompida depois de deixar de produzir resultados nas verificações com navegador; não foi concluída. A matriz foi executada: 11 de 14 conceitos cobertos e três lacunas declaradas; o comando retornou código 1 por essas lacunas. Não houve mudança de código, de guia ou de texto de fluxo.
