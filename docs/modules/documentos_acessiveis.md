# Documentos e relatórios acessíveis

Entrega de 20 de outubro de 2026

Versão do pacote: 2.2.0. Catálogo medido: 47 ferramentas, sete prompts, 71 guias e 44 exemplos de componentes.

O servidor gera arquivos DOCX e PDF a partir do conteúdo escrito pelo modelo do cliente. Não chama outro modelo, não exige chave de IA e não depende de Word ou LibreOffice para gerar os documentos. A mesma ferramenta MCP atende IDEs, Claude e Codex; não há um gerador diferente por cliente.

Contrato das ferramentas

a11y_create_document recebe document e formats. Document contém title, language, author, subject, blocks e, opcionalmente, assessments. Formats aceita docx, pdf ou both. O título é o nível 1. Blocos heading usam level de 2 a 6; paragraph contém text; list contém items e ordered; table contém text como legenda, headers e rows; image contém source e alt; link contém text e url. Os esquemas tipados aparecem no catálogo de ferramentas do próprio cliente.

O DOCX usa estilos de título e seções, idioma padrão, listas numeradas reais, cabeçalho de tabela repetido, legenda, texto alternativo e links com nome. O PDF preserva a estrutura de títulos, listas, tabelas, figuras e links. O gerador completa metadados XMP, descrição dos links e marcação de pintura decorativa que o exportador Chromium deixa incompletos. Texto não é convertido em artefato. As fontes são incorporadas pelo navegador e sua presença é verificada.

a11y_create_report usa os achados e a cobertura da sessão atual ou de uma execução salva. O relatório inclui escopo, resultados registrados, passos de evidência e lacunas. Execuções antigas que não guardaram cobertura são identificadas dessa forma. Nenhum achado registrado não significa aprovação dos critérios. Para uma avaliação por critério, o cliente escreve assessments e usa a ferramenta de criação de documento.

Em assessments, criterion deve ser um identificador WCAG existente; status deve ser Supports, Partially Supports, Does Not Support, Not Applicable ou Not Evaluated; coverage indica complete, partial ou not_evaluated. Uma conclusão diferente de Not Evaluated exige cobertura completa declarada e evidência. O modelo decide o significado e a situação normativa; o código apenas confere esse contrato. A qualidade ou a veracidade da justificativa não pode ser provada pela existência de texto no campo.

Validação

O gerador de DOCX mantém cada linha de tabela na mesma página e limita as imagens à área útil, preservando a proporção. O relatório automático usa texto em português e restringe seus metadados a variantes desse idioma. Para outros idiomas, o modelo escreve o conteúdo na ferramenta de documentos, evitando marcar texto português como se fosse inglês.

a11y_validate_document confere arquivos efetivos, gerados pelo servidor ou dentro da pasta escolhida pela pessoa. No DOCX verifica título, idioma, títulos e saltos de nível, alternativas das imagens, cabeçalhos de tabela, tabelas complexas e links sem texto. No PDF verifica título, idioma, presença e conteúdo da árvore de tags, títulos, figuras, tabelas, fontes incorporadas, mapeamento Unicode, texto extraível e associação de links à estrutura.

A validação externa usa o veraPDF 1.30.1 com perfil PDF/UA-1. Havendo Java no PATH, a instalação automática baixa o pacote oficial fixado por SHA-256 e instala na pasta do usuário. A11Y_MCP_AUTO_INSTALL=0 desliga o preparo automático. A11Y_MCP_VERAPDF pode indicar outra instalação confiável. O processo não usa shell para validar arquivos, inclusive no Windows. Ausência, falha de instalação ou saída inválida não vira aprovação. O relatório XML original fica no resultado de validação.

Nenhuma dessas checagens estabelece uma avaliação completa de acessibilidade. Texto alternativo correto em significado, ordem de leitura adequada, contraste de imagens, documentos complexos e uso com tecnologia assistiva exigem revisão. Complete_validation permanece falso e conformance permanece not_determined, inclusive quando o veraPDF aprova os requisitos automáticos do perfil.

Segurança e entrega dos arquivos

Os documentos recebem identificador único e ficam em A11Y_MCP_HOME/documents, com padrão na pasta pessoal .a11y-mcp. Não sobrescrevem o projeto e não usam a aprovação de edição de fonte para criar um arquivo novo no armazenamento do servidor. As aprovações do cliente MCP continuam valendo. Os recursos a11y://document/{document_id}/document.docx e document.pdf devolvem os bytes com tipo MIME próprio.

Imagens são apenas PNG ou JPEG locais dentro da pasta de trabalho escolhida. O gerador não aceita HTML, CSS nem JavaScript arbitrário; texto é escapado, protocolos de links são validados e o navegador de impressão não busca recursos externos. O leitor de DOCX usa XML sem entidades externas e limite de descompressão. Identificadores de documentos não podem virar caminhos arbitrários.

Uso no Codex

O cadastro deve ter required = true para o Codex aguardar o MCP antes de preparar o catálogo inicial. O instalador aplica essa opção somente ao servidor accessibility. Isso foi necessário no teste real: o servidor opcional não apareceu no primeiro turno, enquanto o servidor obrigatório foi descoberto e chamado. O teste sem aprovação de ferramentas também foi recusado pelo cliente; autorização específica das ferramentas de documentos permitiu a geração. O instalador não altera a política de aprovação de outras ferramentas. Reiniciar uma sessão continua necessário para carregar alterações de cadastro; ferramentas novas não são injetadas em uma conversa já iniciada.

Provas reproduzíveis

Verificação final desta entrega: ruff check . e mypy passaram, com 32 arquivos de código verificados. A regressão completa terminou com 329 testes aprovados e um ignorado em 1081,14 segundos. Os 40 testes específicos de documentos, cadastro e protocolo foram executados novamente após os ajustes finais e passaram em 59,36 segundos; essa rodada inclui casos adicionados depois da coleta da regressão completa. A matriz de cobertura registrou 11 conceitos cobertos, um parcial e duas lacunas; retornou código 1 por essas pendências, sem ocultá-las.

tests/test_documents.py usa DOCX e PDF reais, planta defeitos e verifica a detecção, a preservação de texto Unicode, imagens, títulos, tabelas, listas e links, além das fronteiras de arquivo e de XML. tests/test_e2e_protocol.py cria e valida documentos e gera um relatório de achados medidos pelo protocolo MCP, sem chave de modelo. tests/test_setup.py cobre o cadastro do Codex sem alterar os outros servidores. tests/test_server.py confere a paridade entre o prompt de documentos e a11y_workflow.

scripts/verify_documents_live.py sobe o servidor pelo protocolo MCP, gera três pares de arquivos, incluindo tabela em várias páginas, imagem com alternativa, duas listas numeradas, links e relatório de uma sessão. Reabre e valida os arquivos, exige aprovação PDF/UA-1 pelo veraPDF e confere os bytes lidos pelos recursos MCP. Os resultados ficam fora do repositório em .a11y-mcp/documents/live-verification.json.

scripts/eval_document_guidance.py avalia oito cenários sintéticos no cliente Codex autenticado, em três repetições, e repete com ablação da seção corrigida do guia. A rodada de 20/10/2026 obteve 24 de 24 decisões esperadas com a correção e 18 de 24 com a ablação. Sem a seção corrigida, as três rodadas aprovaram a violação de baixa gravidade e não preservaram a situação de avaliação incompleta no caso correspondente. As justificativas foram lidas; esses resultados valem para esse conjunto e esse cliente, não para todo modelo ou relatório.

O teste em linguagem natural no Codex chamou o MCP, consultou o guia, gerou DOCX/PDF e validou os arquivos. As ferramentas também foram chamadas diretamente na conversa do Codex Desktop, gerando os dois formatos e validando o PDF com veraPDF. A verificação visual foi feita a partir do PDF produzido diretamente e do DOCX aberto e renderizado no Word instalado. O renderizador empacotado não pôde usar LibreOffice, ausente neste Windows; essa falha foi registrada antes de usar o Word para a confirmação visual. A revisão visual revelou uma borda herdada do estilo Title, uma legenda azul e linhas partidas entre páginas; as correções foram aplicadas e as seis páginas finais da tabela no Word foram conferidas novamente.

Correção na fonte do conhecimento

O guia specialist-vpat-reporter deixou de aprovar automaticamente ausência de achados ou falhas leves. A mesma seção foi corrigida nos dois prompts do especialista no Qaaccessibility, de onde esse conteúdo é originário. Os testes daquele especialista foram executados separadamente; isso não representa validação de todos os provedores do Qaaccessibility.

Pesquisa de exemplos didáticos em 20/10/2026

O projeto ainda não oferece uma galeria de documentos bons e ruins equivalente à demonstração web. As referências externas localizadas foram o exercício oficial de Word do governo de Illinois, com versões acessíveis e inacessíveis do mesmo conteúdo em DOCX e PDF (https://doit.illinois.gov/initiatives/accessibility/guides/word/word-accessibility-exercise.html), a coleção de PDFs de referência da PDF Association (https://pdfa.org/resource/pdfua-reference-suite/) e o corpus de testes PDF/UA do veraPDF (https://github.com/veraPDF/veraPDF-corpus). As páginas foram consultadas; os arquivos de terceiros não foram executados nem incorporados ao projeto.

Uma futura galeria pode comparar títulos navegáveis, alternativas de imagens, cabeçalhos de tabelas, listas, nomes de links e ordem de leitura. Para comprovar a experiência, a sonda precisa abrir os arquivos no Word e em um leitor de PDF identificado, registrar as versões e capturar a fala real do NVDA. Expectativa de anúncio e fala observada devem ficar separadas. A sonda atual de páginas não prova esse comportamento em aplicativos de documentos.

Limites ainda não comprovados

O guia de conformidade foi avaliado com gpt-6.1-sol no Codex CLI 0.163.0-alpha.10.2, conforme os registros do cliente. A correção correspondente na fonte Qaaccessibility está no commit local 4aa7bd0; não foi enviada ao remoto daquele projeto.

Não houve leitura dos arquivos finais com NVDA real ou outro leitor de tela nesta entrega. Não foram executados os chats do Claude, Cursor e VS Code; foram conferidos os contratos MCP compartilhados e o cliente Codex real. A avaliação de instruções cobre oito casos sintéticos, não todos os critérios WCAG nem todos os modelos. A observação de regressões em uso real continua necessária. A validação normativa depende de Java e do veraPDF disponível. Tabelas complexas, formulários de documento e arquivos protegidos não são gerados pelo contrato atual.
