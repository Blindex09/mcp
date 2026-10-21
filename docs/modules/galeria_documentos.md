# Galeria de documentos acessíveis

Entrega de 21 de outubro de 2026

A seção documentos.html faz parte de demo/exemplos-leitor-de-tela. O início e a navegação das páginas existentes apontam para ela. São nove assuntos e 30 arquivos para baixar: seis pares em DOCX e nove pares em PDF. Cada par explica o que fazer, evitar, o defeito introduzido, a medição feita, o comportamento esperado e os passos de revisão no aplicativo.

Os assuntos são títulos, alternativas de imagens, cabeçalhos de tabelas, listas, propósito dos links, título e idioma do arquivo, tags de PDF, ordem de leitura e digitalização sem texto. Os arquivos ruins têm defeitos deliberados; não são documentos de produção. Bom indica que a propriedade demonstrada foi preservada, não que o documento inteiro recebeu certificação.

Fontes e conhecimento compartilhado

As páginas oficiais de Microsoft, W3C e Adobe foram consultadas em 21/10/2026. As URLs e a data estão em accessibility_mcp/a11y/content/assets/document-examples.json. O exercício do governo de Illinois também é uma referência listada. Nenhum arquivo de terceiros foi copiado para a galeria.

O gerador documentos.py usa essa fonte para montar a página e o guia document-behavior-matrix, que fica acessível no catálogo MCP. O conjunto de contratos também pode ser lido como template assets/document-examples.json. É conhecimento próprio de condução dos exemplos e ferramentas deste MCP, não alteração dos guias espelhados do Qaaccessibility. A base passa a conter 72 guias; ferramentas e prompts permanecem 47 e sete.

O guia orienta a criar arquivos reais com as ferramentas existentes, avaliar o arquivo efetivo e separar estrutura, julgamento semântico e fala capturada. Inclui os limites de OCR, diferença entre PDF/UA-1 e PDF/UA-2, imagens decorativas, contexto dos links e exportação do Word para PDF. Técnicas W3C são formas de atender critérios, não implementações obrigatórias isoladas.

Geração e medição

Para regenerar esta seção e atualizar a navegação sem repetir as medidas dos componentes web: python demo/exemplos-leitor-de-tela/documentos.py. O build completo construir.py também chama o gerador. Os exemplos usam o gerador existente de documentos do servidor; os defeitos são introduzidos somente nas cópias didáticas. A nova moldura das páginas web preserva o corpo e as medições anteriores desses exemplos.

Os 15 arquivos bons passaram nas checagens estruturais; os nove PDFs bons passaram nas verificações automáticas PDF/UA-1 do veraPDF. As cópias ruins não executam veraPDF nessa rodada. Em listas, links e ordem lógica a página explica que o validador genérico pode não detectar o defeito. A verificação específica dos pares confere listas estruturadas contra parágrafos, o nome do link e a inversão dos itens na árvore de tags. Nada disso equivale a capturar a fala do leitor.

O registro reproduzível fica em demo/exemplos-leitor-de-tela/documentos/medicoes.json. Os 12 DOCX foram abertos somente para leitura numa instância oculta do Word e exportados para revisão; os 18 PDFs originais e os 12 PDFs renderizados do Word foram convertidos em imagens e as 30 páginas foram conferidas visualmente. O renderizador empacotado falhou porque LibreOffice não está no PATH; a falha foi diagnosticada antes de usar o Word instalado como alternativa. Não houve cortes ou sobreposição não intencionais; diferenças deliberadas dos exemplos ruins foram mantidas.

Correções encontradas

A inspeção da página revelou que um título PDF vazio era interpretado como a string None, escapando da detecção. A causa era converter o retorno nulo de metadata.title em texto antes de conferir se estava vazio. O validador agora normaliza o valor ausente para texto vazio. tests/test_documents.py inclui regressão com um PDF real cujo título foi esvaziado, além da verificação do par de metadados.

O teste de download inicialmente reutilizou o contexto do servidor, que bloqueia downloads por segurança. O teste agora abre um contexto separado para os arquivos locais da galeria e mantém a proteção do servidor. O conteúdo estruturado compartilhado foi colocado em assets para ficar disponível pelo próprio catálogo, em vez de existir como arquivo inatingível na raiz da base.

Avaliação das instruções

scripts/eval_document_examples.py executa 16 cenários sintéticos no Codex autenticado, sem ferramentas, três vezes com o guia e três sem o guia. A primeira rodada revelou categorias sobrepostas do avaliador: não testado e precisa de revisão eram ambas respostas corretas para um PDF exportado não inspecionado; OCR incompleto permitia classificar falta de evidência ou revisão necessária. As justificativas foram lidas antes de corrigir as alternativas aceitas. O guia não mudou para acomodar rótulos do teste.

Após a correção do avaliador, uma nova execução completa obteve 48 de 48 decisões aceitas com o guia e 48 de 48 sem ele. Isso não demonstra melhora causada pelo guia, apenas ausência de regressão nesse conjunto. O cliente registrou gpt-6.1-sol. As respostas e os eventos originais ficaram fora do repositório; o resumo está em galeria_documentos_evidencias.json. O registro inicial de rótulos rejeitados foi preservado. Outros modelos e a observação de uso em produção continuam pendentes.

Interface e limites

tests/test_demo_documents.py confere os arquivos efetivos, paridade do guia com os contratos, links em todas as páginas, ausência de certificação automática, navegação por Tab, download por Enter e ausência de rolagem horizontal a 320 pixels. A página servida foi conferida também no navegador do Codex e pelas ferramentas MCP desta conversa. O guia novo foi lido por essa conexão; a sonda de teclado registrou 69 paradas, nenhuma prisão de foco e nenhum foco coberto no Chromium.

Não houve captura de fala real do NVDA no Word nem em leitor de PDF. A seção distingue comportamento esperado de fala observada. A sonda existente para páginas continua sem abrir aplicativos de documentos. Os pares não cobrem formulários interativos, matemática, todas as tabelas complexas, contraste de todo conteúdo ou todos os leitores e aplicativos. Esses limites são exibidos na página e no guia.

A tentativa adicional no Firefox pelo MCP preparou o navegador, mas falhou ao iniciar: a execução direta do binário instalado reproduziu BrowserType.launch: spawn UNKNOWN. Não há causa raiz comprovada nem aprovação dessa combinação. O WebKit no modo escuro abriu a página, registrou sete paradas sem prisão ou foco coberto e nenhum alvo abaixo de 24 pixels entre os 99 medidos; a navegação dessa configuração não percorreu os links. WebKit do Playwright não prova Safari com VoiceOver. A confirmação de todos os downloads por teclado desta entrega vale para Chromium.

Verificação final

Ruff check . e mypy passaram; o mypy verificou 32 arquivos do servidor. A regressão conjunta terminou com 345 testes aprovados e um ignorado em 1115,69 segundos. A rodada específica final teve 79 aprovados em 96,38 segundos, incluindo o caso de título PDF vazio acrescentado depois da coleta da regressão conjunta. Os testes existentes de Firefox passaram no ambiente da suíte, distinto da tentativa adicional de inicialização pelo MCP registrada acima.

A matriz de cobertura foi executada: 11 conceitos cobertos, um parcial e duas lacunas; retornou código 1 pelas pendências declaradas. O pacote wheel foi construído e inspecionado: contém tanto o guia novo quanto os contratos compartilhados. A navegação da galeria e o protocolo MCP real passaram; isso não estabelece a fala real de leitores de tela nem valida todos os clientes de IDE.
