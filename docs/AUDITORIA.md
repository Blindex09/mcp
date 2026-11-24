# Auditoria do MCP de acessibilidade

## Relatório com nome estável e elemento sempre identificado em 24/11/2026

Dois defeitos vistos na planilha da /contato da WeCover. Primeiro, cada geração com conteúdo novo criava uma pasta nova e deixava dois arquivos do mesmo relatório: agora o identificador vem do título, do idioma e do grupo de formato, e gerar de novo substitui o anterior (o mais recente prevalece). Segundo, as três linhas saíram com "Elemento não identificado", porque `a11y_finding` só resolvia o elemento de alvos do dossiê: agora lê o elemento de qualquer alvo `css:` pelo navegador, recusa alvo que não existe, e a conferência do relatório passa a bloquear qualquer célula de lacuna desse tipo. Detalhes, provas e limite em [relatorios_qa_acessibilidade.md](modules/relatorios_qa_acessibilidade.md). Rodada completa anterior: 499 aprovados e um reprovado, `test_every_tool_over_the_real_protocol`, porque a ferramenta nova `a11y_inspect` não era exercitada pelo protocolo real; corrigido no teste.

## Inspeção do elemento pelo CDP em 24/11/2026

Pedido do dono depois de um teste real na WeCover: a medição do código da página tinha de ser a do painel de inspeção do navegador. Antes, `a11y_source_of` lia o `outerHTML` pela página, retirava os atributos `style`, resumia os svg e listava só as regras de CSS que casam com o elemento, sem a cascata nem o estado. Isso escondeu um falso zero no foco do cartão de WhatsApp (estilo aplicado por `onFocus` em React) e o estilo inline de páginas montadas no servidor.

Nova ferramenta `a11y_inspect` (módulo `inspect_dom.py`, só Chromium): `outerHTML` completo, atributos, estilo inline, regras aplicadas e herdadas com folha, linha, coluna e texto original da regra, estilo calculado, mudanças sob `:hover`, `:focus`, `:focus-visible` e `:active` forçados, ouvintes com arquivo, linha e trecho do código (`Debugger.getScriptSource`), caixa, entrada de acessibilidade e tecnologias (marcas de React, Vue, Angular, Svelte, Next, jQuery e web components, e arquivos que declaram source map). O alvo é resolvido por `Session.cdp_node`, extraído de `focus_style` para os dois usarem o mesmo caminho (atravessa iframes e Shadow DOM quando o dossiê numerou o elemento). Cada chamada grava um passo no rastro.

Limites registrados, sem esconder: estado forçado não dispara eventos da página, então estilo aplicado por JavaScript em `onFocus` ou `onMouseEnter` não aparece e exige Tab real com `a11y_screenshot`; React delega ouvintes ao elemento raiz; o CDP situa a função do ouvinte na lista de parâmetros, então o trecho começa ali; marca de biblioteca é vestígio, e ausência de marca não prova que ela não é usada; Firefox e WebKit não têm CDP e a ferramenta diz isso. Testes em `tests/test_inspect_dom.py`, com página real e Chromium real. `a11y_inspect` passou a ser citada nos textos que ensinam o modelo: `testing-playbook-for-ai` (passo 5, passo 8 e duas linhas na tabela de erros já cometidos), `report-writing-style` (regra 0), o fluxo `a11y_deliver_audit` em `prompts.py` e as instruções do servidor. Pendente, no sentido da regra 15: mudança numa instrução ao modelo tem portão de avaliação (conjunto amplo, tentativas repetidas, ablação, observação), que exige um modelo e não foi rodado. O que rodou sem modelo e passou: a bancada `bench facts`, os testes do servidor, de ferramentas sob demanda, de evidência, de achados e de cobertura.

## Roteiro e reprodução acessíveis em 29/10/2026

Corrigida a orientação antiga que tratava Roteiro como journey, apesar de a geração já usar problem_location. O registro de achados e o contexto de relatórios aceitam rotas declaradas por visão, teclado e leitor de tela; o formatador compartilhado mantém as ações numeradas em XLSX e na narrativa Word/PDF. Não há inferência de comandos nem declaração de fala real baseada só na árvore. Contrato, compatibilidade, testes reais dos arquivos e limites estão em [relatorios_qa_acessibilidade.md](modules/relatorios_qa_acessibilidade.md). Evidências da revisão qualitativa de 18 cenários em três rodadas e ablação em [roteiros_reproducao_evidencias.json](modules/roteiros_reproducao_evidencias.json), sem ganho demonstrado e sem alegar validação ampla de todos os modelos.

## Precisão de testes e confronto com fontes oficiais em 28/10/2026

Revisão e fontes em [precisao_testes_acessibilidade.md](modules/precisao_testes_acessibilidade.md); respostas da avaliação do guia em [precisao_testes_evidencias.json](modules/precisao_testes_evidencias.json). Foram corrigidos cortes de resultados de axe, inventário, mapa, tabulação, comparação, anúncios, árvore e reflow; reconhecimento de foco em alvo CSS sem inventário prévio; propagação prematura do envio de formulário retido; arredondamento de tamanho de alvo e limiar de texto grande. A matriz de componentes passou a distinguir recomendações de implementação e requisitos WCAG, com fontes W3C/WAI consultadas nesta data.

MCP real no BlindHelp: 26 alertas de contraste com 26 exemplos devolvidos; busca NVDA autorizada chegou a Search results após aprovação exclusiva do formulário. Estatísticas não foram liberadas. Isso confirma esse fluxo observado, sem aprovar todos os resultados, páginas ou leitores de tela. NVDA real continua sem VM configurada e o Hyper-V recusou a consulta por permissão.

Ruff e mypy passaram. Suíte geral: 401 aprovados e um ignorado; regressão posterior dos módulos afetados: 152 aprovados; recortes finais de cobertura e protocolo: 18 e 11 aprovados. Execuções têm sobreposição, sem soma de testes únicos. Matriz: 12 cobertos, um parcial, uma lacuna preexistentes. Guia: 24 cenários, três repetições e ablação; após revisão documentada das ambiguidades de rótulos no gabarito, 72/72 aceitos com guia e 72/72 sem guia, sem ganho demonstrado. Não há aprovação ampla de todos os guias/modelos. Alterações locais sem misturar em commit o trabalho anterior já modificado; nenhuma publicação.

## Estrutura dos relatórios de QA de acessibilidade em 27/10/2026

A pesquisa e as decisões de organização estão em `docs/modules/relatorios_qa_acessibilidade.md`.
O relatório aceita contexto explícito da auditoria, reprodução e reteste por ocorrência,
e resultados por critério com escopo e evidência. Excel segue a ordem Resumo,
Escopo e ambiente, Achados, Matriz WCAG, Correções e retestes, Evidências e referências.
O registro principal contém uma linha completa por ocorrência, sem perder dados específicos
das páginas de um grupo. Word/PDF seguem as oito seções do modelo W3C e incluem
identificação inicial, sumário, fichas na mesma sequência editorial e índice de evidências.
Inconclusivo não vira declaração VPAT, e prioridade não estabelece prazo automático.
O servidor valida os dados e preserva sua origem; a decisão normativa continua com o avaliador.
A revisão seguinte acrescenta campos próprios para alvo, base de suporte, tecnologias,
ferramentas e versões, exploração, amostra aleatória, idiomas da equipe e acompanhamento.
Os resumos de Word/PDF e Excel listam dados não registrados, inclusive reprodução por ID.
O alvo deixa de ser presumido como AA; a matriz padrão A/AA é identificada separadamente.
Os 49 testes específicos e de protocolo passaram, assim como ruff e mypy (38 arquivos).
A regressão ampliada passou com 332 aprovados, um ignorado e seis desmarcados; o
recorte e as exclusões estão descritos no documento do módulo e não são a suíte integral.
Os três arquivos BlindHelp foram gerados pelo protocolo real e conferidos, mantendo os
12 achados históricos sem revalidar seus enquadramentos. A matriz mantém 12 conceitos
cobertos, um parcial e uma lacuna; não equivale à aprovação integral do módulo.
A validação com tecnologias assistivas e a avaliação ampla da descrição atualizada pelos
modelos clientes permanecem pendentes. O módulo não está declarado concluído.

## Atualização de interoperabilidade MCP e A2A

O servidor agora consome servidores MCP por Streamable HTTP e agentes A2A 1.0 por JSON-RPC HTTP/HTTPS, sem iniciar processos remotos por `stdio` e sem chamar modelos. As nove ferramentas novas são registradas em `tools_interop.py` e usam o cliente isolado em `interop.py`. Chamadas MCP remotas, envio A2A e consulta de tarefa só são enviados depois da aprovação pontual do pedido exato. A consulta pública do Agent Card é somente leitura.

Endereços locais e privados são recusados por padrão; `A11Y_MCP_REMOTE_ALLOW_PRIVATE=1` é uma liberação deliberada. Tokens só podem ser usados em HTTPS e vêm de uma variável de ambiente. Redirecionamentos e proxies de ambiente ficam desativados. As requisições têm limite de inatividade de 30 segundos e conexão de 10 segundos, sem prazo total fixo. A validação de DNS não fixa o IP até a abertura do socket, portanto DNS rebinding continua uma limitação; os endpoints devem ser confiáveis. As conexões são compartilhadas no processo e não têm isolamento multiusuário. Contrato, verificações e limites: `docs/modules/interop_remota.md`.

A matriz executada após a implementação registrou 12 de 14 conceitos cobertos, um parcial e uma lacuna. O cliente MCP remoto/A2A foi exercitado por nove ferramentas tipadas, e o padrão de bloqueio de rede privada foi conferido no protocolo do servidor. A matriz terminou com código 1 pela lacuna declarada da revisão do harness em novas gerações de modelo, não por falha na interoperabilidade. Os testes de integração reais estão em `tests/test_interop.py`.

Estado da arquitetura em 21/10/2026

A versão 2.3.0 acrescenta controles nativos de formulário, sumário e links internos aos documentos. document_controls.py monta SDT, TOC e bookmarks no Word; pdf_forms.py monta AcroForm, aparências e vínculo Form/OBJR/ParentTree no PDF. O contrato e as verificações atuais estão em docs/modules/formularios_sumario.md. O guia ampliado teve 66/66 decisões aceitas em três rodadas e 66/66 na ablação, sem ganho demonstrado nesse conjunto.

Atualização de 21/10/2026

A demonstração agora inclui documentos.html, com 12 assuntos, 18 DOCX e 24 PDFs bons e ruins de propósito. Os contratos e fontes oficiais ficam em content/assets/document-examples.json e geram o guia document-behavior-matrix, acessível no catálogo MCP. A base contém 72 guias. A página distingue medidas estruturais, comportamento esperado e fala real, que ainda não foi capturada nos aplicativos de documentos. A entrega e as evidências estão em docs/modules/galeria_documentos.md e galeria_documentos_evidencias.json.

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

Continuam pendentes a avaliação ampla dos guias e fluxos com modelos de clientes e a revisão do harness a cada geração de modelo. O guia de conformidade teve uma avaliação delimitada com oito cenários, três repetições e ablação, registrada em docs/modules/documentos_evidencias.json; ela não cobre os demais guias e modelos. A interoperabilidade MCP e A2A está disponível por HTTP/HTTPS, com as limitações registradas acima. Não há executor Android ou iOS, nem prova de Safari com VoiceOver. O NVDA real depende de uma VM configurada; a árvore do navegador não prova a fala exata de um leitor de tela.

A integração com o Qaaccessibility usa a11y_check_page para provar comportamento. A decisão do roteador daquele projeto, seu custo de contexto e a avaliação das instruções dele precisam ser comprovados naquele projeto. Os playbooks de especialistas e guias de leitor de tela têm o Qaaccessibility como fonte; os roteiros e sondas próprios do MCP permanecem aqui.

Documentos em 20/10/2026

tools_documents.py expõe geração de DOCX e PDF com tags, validação estrutural e relatórios dos achados e da cobertura, com recursos MCP para baixar os bytes. O veraPDF verifica os requisitos automáticos PDF/UA-1; a revisão semântica, visual e com leitor de tela continua necessária. Contratos, evidências e limites estão em docs/modules/documentos_acessiveis.md. A geração foi chamada no Codex real e nesta conversa. Não há ainda galeria de documentos bons e ruins nem sonda da fala real do NVDA dentro do Word ou de um leitor de PDF.

Verificação: ruff e mypy aprovados; regressão completa com 329 testes aprovados e um ignorado; rodada específica final com 40 testes aprovados. A matriz registra 11 conceitos cobertos, um parcial e duas lacunas. Os três PDFs do roteiro ao vivo passaram no veraPDF; os DOCX também foram abertos e renderizados no Word para revisão visual.

Limpeza de 20/10/2026

A documentação da arquitetura anterior foi retirada deste arquivo e da demonstração da loja. Os módulos de provedor, roteamento e execução autônoma já não faziam parte do código versionado. A regra de interface deixou de apontar para o módulo removido. Os registros históricos anteriores continuam disponíveis no Git.

Esta limpeza altera documentação e o escopo de uma regra local; não altera ferramentas, prompts nem comportamento do servidor. Verificação desta entrega: ruff check . e mypy passaram (27 arquivos de código verificados pelo mypy); os sete testes de tests/test_server.py e tests/test_e2e_protocol.py passaram em 33,52 segundos, incluindo o protocolo MCP real. A suíte completa de 303 testes foi iniciada, mas interrompida depois de deixar de produzir resultados nas verificações com navegador; não foi concluída. A matriz foi executada: 11 de 14 conceitos cobertos e três lacunas declaradas; o comando retornou código 1 por essas lacunas. Não houve mudança de código, de guia ou de texto de fluxo.


29/10/2026 — Coerência de documentos e exemplos

Listas de reprodução nativas no DOCX/PDF; validação XLSX genérica separada do contrato de relatórios; quatro exemplos Excel; distinção entre congelamento e cabeçalhos; títulos válidos dentro de listas; diferenças esperadas entre modos de navegação. Origem Qaaccessibility sincronizada. Evidências, testes e limites em docs/modules/coerencia_documentos.md e coerencia_documentos_evidencias.json. Relatórios BlindHelp substituídos em C:\relatórioss sem nova auditoria integral.


30/10/2026 — Relatórios com Roteiro como localização única, sem coluna Área da página; justificativas BlindHelp corrigidas e separadas do esperado. Contrato XLSX com 30 colunas. Ver docs/modules/relatorios_qa_acessibilidade.md e roteiro_campos_evidencias.json para testes, avaliação dos textos e limites.


30/10/2026 — Relatórios com percurso visual e orientação proposta de leitor de tela, separados dos percursos executados. Novo argumento nos achados e no contexto de relatórios; rótulo de não execução explícito em XLSX/DOCX/PDF. Ver docs/modules/relatorios_qa_acessibilidade.md e percursos_leitor_evidencias.json para testes, avaliação e limites. Entrega BlindHelp atualizada nos três nomes principais em C:\relatórioss.
