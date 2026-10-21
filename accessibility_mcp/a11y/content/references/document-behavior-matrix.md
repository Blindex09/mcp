# Document behavior matrix: Word DOCX and PDF examples

Origem: este MCP. Contratos dos exemplos de documentos e uso das ferramentas deste servidor.
Fontes oficiais consultadas em 2026-10-21. Textos sintetizados; arquivos de terceiros não foram incorporados.

## Como usar e o que pode afirmar

Escolha os assuntos pelo significado da tarefa. A galeria está em demo/exemplos-leitor-de-tela/documentos.html.
Para produzir arquivos, escreva o conteúdo e use a11y_create_document; para relatório dos achados, a11y_create_report. Valide o arquivo efetivo com a11y_validate_document.
O MCP mede estrutura; o modelo do cliente julga significado, qualidade e cobertura. Não escolha casos por palavras-chave nem converta ausência de erros em conformidade.
As técnicas W3C são formas de atender critérios, não uma lista de implementações obrigatórias. A galeria ensina casos delimitados; Bom significa que a propriedade exemplificada foi preservada, não certificação do arquivo.
A inspeção DOCX verifica metadados, títulos, alternativas, cabeçalhos de tabela e links sem texto. PDF acrescenta tags, fontes, Unicode e texto extraível. Listas simuladas, propósito de links, sentido da alternativa e ordem lógica exigem julgamento e revisão no aplicativo.
Uma imagem decorativa corretamente marcada não exige a mesma descrição de uma figura informativa. O validador DOCX atual não distingue decoração e pode pedir revisão; o gerador exige alt para as imagens que aceita.
PDF/UA-1 e PDF/UA-2 são perfis distintos. O gerador atual é verificado automaticamente com veraPDF PDF/UA-1; não declare PDF/UA-2. Aprovação automática não comprova todos os requisitos nem WCAG.
A sonda a11y_nvda_speech é para páginas na VM configurada, não abre Word ou leitor de PDF. Não invente fala literal nem declare teste real de documentos sem capturar o leitor no aplicativo. Registre versões, comandos, resultado e limitações. OCR do leitor não torna o arquivo acessível.

## Títulos que permitem navegar

Fazer: Dê estrutura às seções com estilos de título no Word e tags de título no PDF. Organize os níveis pelo conteúdo.
Evitar: Não transforme parágrafos em falsos títulos apenas aumentando a fonte e aplicando negrito.
Comportamento esperado, não fala capturada: A estrutura deve expor os títulos e seus níveis para navegação. A frase anunciada depende do aplicativo e do leitor.
Verificação no aplicativo: Compare os títulos visuais com o painel de navegação do Word ou a lista de títulos do leitor no PDF. Percorra cada seção e registre o resultado.
Defeito demonstrado: Os títulos visuais foram mantidos, mas sua estrutura foi trocada por parágrafos comuns.
Medição automática: missing_heading_one.
Fontes: [Microsoft — Acessibilidade no Word](https://support.microsoft.com/en-gb/accessibility/word/make-your-word-documents-accessible-to-people-with-disabilities); [W3C — PDF9 Títulos](https://www.w3.org/WAI/WCAG22/Techniques/pdf/PDF9)

## Imagens com significado em texto

Fazer: Descreva a informação relevante das imagens. Para gráficos complexos, ofereça também dados e explicação no corpo do documento.
Evitar: Não deixe uma imagem informativa sem alternativa nem use o nome do arquivo como descrição. Conteúdo decorativo deve ser marcado como tal no aplicativo de autoria.
Comportamento esperado, não fala capturada: O leitor deve ter acesso ao significado da figura; encontrar um campo de alternativa preenchido não prova que a descrição seja adequada.
Verificação no aplicativo: Chegue à imagem usando o leitor. Compare a descrição com a informação visual e confira se a informação continua compreensível sem enxergar a figura.
Defeito demonstrado: A alternativa da imagem informativa foi removida; a figura continua visível.
Medição automática: image_missing_alt.
Fontes: [Microsoft — Acessibilidade no Word](https://support.microsoft.com/en-gb/accessibility/word/make-your-word-documents-accessible-to-people-with-disabilities); [W3C — PDF1 Alternativas de imagens](https://www.w3.org/WAI/WCAG22/Techniques/pdf/PDF1)

## Tabelas com cabeçalhos

Fazer: Use tabelas para dados, identifique os cabeçalhos e preserve suas relações com as células. Prefira estrutura simples; confira tabelas que atravessam páginas.
Evitar: Não simule uma tabela com espaços nem confie só no negrito da primeira linha. Células mescladas ou estruturas complexas exigem revisão específica.
Comportamento esperado, não fala capturada: Ao percorrer os dados, a associação com o cabeçalho deve continuar disponível. A repetição visual do cabeçalho no Word não prova sozinha a experiência no leitor.
Verificação no aplicativo: Entre na tabela e navegue por linhas e colunas com os comandos do leitor. Confira cabeçalhos, valores e transições de página no aplicativo escolhido.
Defeito demonstrado: O cabeçalho continua visualmente destacado, mas sua marcação foi removida.
Medição automática: table_missing_header.
Fontes: [Microsoft — Acessibilidade no Word](https://support.microsoft.com/en-gb/accessibility/word/make-your-word-documents-accessible-to-people-with-disabilities); [W3C — PDF6 Tabelas](https://www.w3.org/WAI/WCAG22/Techniques/pdf/PDF6)

## Listas reconhecidas como listas

Fazer: Crie listas com o recurso de listas do editor e mantenha a estrutura de lista e itens ao exportar.
Evitar: Não substitua a lista por parágrafos com números ou marcadores digitados à mão.
Comportamento esperado, não fala capturada: A relação entre os itens deve estar disponível à tecnologia assistiva. A lista de exemplo tem duas etapas em sequência.
Verificação no aplicativo: Use a navegação de listas e itens disponível no leitor e aplicativo. Confira sequência, quantidade e conteúdo sem depender do marcador visual.
Defeito demonstrado: A numeração visual permanece, mas os itens foram convertidos em parágrafos comuns.
Medição automática: o validador estrutural pode não detectar este defeito; revisar o conteúdo e a estrutura específica.
Fontes: [Microsoft — Acessibilidade no Word](https://support.microsoft.com/en-gb/accessibility/word/make-your-word-documents-accessible-to-people-with-disabilities); [W3C — PDF21 Listas](https://www.w3.org/WAI/WCAG22/Techniques/pdf/PDF21)

## Links com destino compreensível

Fazer: Escreva um nome que explique a finalidade do link, considerando o contexto. Mantenha o link utilizável pelo teclado.
Evitar: Não use um link isolado chamado apenas Clique aqui sem contexto que explique o destino. Uma URL ou um texto preenchido não prova clareza.
Comportamento esperado, não fala capturada: A pessoa deve conseguir decidir se quer abrir o destino. Texto alternativo adicional para todo link PDF não é obrigatório por si só.
Verificação no aplicativo: Percorra os links pelo teclado e consulte a lista de links do leitor. Leia também o contexto antes de decidir se o propósito é compreensível.
Defeito demonstrado: O link isolado perdeu seu nome descritivo e passou a se chamar Clique aqui.
Medição automática: o validador estrutural pode não detectar este defeito; revisar o conteúdo e a estrutura específica.
Fontes: [Microsoft — Acessibilidade no Word](https://support.microsoft.com/en-gb/accessibility/word/make-your-word-documents-accessible-to-people-with-disabilities); [W3C — PDF13 Propósito dos links](https://www.w3.org/WAI/WCAG22/Techniques/pdf/PDF13)

## Título e idioma do arquivo

Fazer: Informe um título descritivo e o idioma principal correto. Marque mudanças de idioma quando necessário.
Evitar: Não confunda o nome do arquivo com o título nos metadados nem marque texto em português como se fosse inglês.
Comportamento esperado, não fala capturada: O aplicativo e o leitor devem receber identificação e idioma coerentes com o conteúdo. A pronúncia também depende da voz e da configuração.
Verificação no aplicativo: Confira propriedades e idioma do texto no editor; no PDF, confira título, idioma e preferências de exibição. Ouça trechos em cada idioma usado.
Defeito demonstrado: O título e o idioma padrão foram removidos dos metadados, mantendo o conteúdo visual.
Medição automática: missing_language.
Fontes: [W3C — PDF16 Idioma](https://www.w3.org/WAI/WCAG22/Techniques/pdf/PDF16); [W3C — PDF18 Título do documento](https://www.w3.org/WAI/WCAG22/Techniques/pdf/PDF18); [Adobe — Criar e verificar PDFs acessíveis](https://helpx.adobe.com/acrobat/using/create-verify-pdf-accessibility.html)

## PDF com estrutura preservada

Fazer: Exporte PDF com tags e confira a estrutura resultante, além da aparência. Corrija o arquivo fonte sempre que possível.
Evitar: Não suponha que um PDF seja acessível por ser selecionável, abrir no navegador ou ter sido produzido por uma impressora PDF.
Comportamento esperado, não fala capturada: Tags devem representar o conteúdo e suas relações. Presença de tags ou aprovação automática não garante qualidade semântica.
Verificação no aplicativo: Inspecione a árvore de tags e percorra o PDF com teclado e leitor. Compare os elementos encontrados com o documento visível.
Defeito demonstrado: A árvore de tags foi retirada, sem alterar o texto que aparece na página.
Medição automática: missing_tags.
Fontes: [W3C — PDF9 Títulos](https://www.w3.org/WAI/WCAG22/Techniques/pdf/PDF9); [Adobe — Criar e verificar PDFs acessíveis](https://helpx.adobe.com/acrobat/using/create-verify-pdf-accessibility.html)

## Ordem de leitura com sentido

Fazer: Mantenha uma sequência lógica na estrutura do PDF e confira também a ordem de foco dos elementos interativos.
Evitar: Não confie apenas na posição visual ou em copiar e colar o texto: a ordem das tags pode ser diferente da ordem de pintura.
Comportamento esperado, não fala capturada: Na lista deste exemplo, a leitura deve apresentar Primeiro prepare o documento antes de Depois revise o documento.
Verificação no aplicativo: Leia continuamente e percorra os itens da lista com o leitor. Compare a sequência falada com o sentido das instruções. Registre aplicativo, versão e configuração.
Defeito demonstrado: Os dois itens foram invertidos apenas na árvore de tags; a sequência visual não mudou.
Medição automática: o validador estrutural pode não detectar este defeito; revisar o conteúdo e a estrutura específica.
Fontes: [W3C — PDF3 Ordem de leitura](https://www.w3.org/WAI/WCAG22/Techniques/pdf/PDF3)

## PDF digitalizado com texto real

Fazer: Prefira o documento fonte com texto. Se só houver digitalização, aplique OCR, revise o reconhecimento e organize as tags e a ordem de leitura.
Evitar: Não entregue uma fotografia de texto como único conteúdo nem considere que executar OCR resolve toda a acessibilidade.
Comportamento esperado, não fala capturada: As palavras devem estar disponíveis como texto correto e estruturado. Recursos de OCR do leitor podem variar e não corrigem o arquivo de origem.
Verificação no aplicativo: Pesquise palavras, confira o texto reconhecido e leia o documento com tecnologia assistiva. Verifique números, acentos, ordem, títulos e tabelas.
Defeito demonstrado: O conteúdo foi rasterizado: o PDF contém somente a imagem da página, sem texto extraível nem estrutura.
Medição automática: page_without_extractable_text.
Fontes: [W3C — PDF7 Texto e OCR](https://www.w3.org/WAI/WCAG22/Techniques/pdf/PDF7); [Adobe — Criar e verificar PDFs acessíveis](https://helpx.adobe.com/acrobat/using/create-verify-pdf-accessibility.html)

## Limites complementares

Confira contraste e uso de cor sem depender apenas da cor; texto pequeno ou layout que não reflui podem impedir o uso com ampliação. Formulários precisam de nomes, instruções, estados e ordem de foco; o gerador atual não cria formulários interativos. Valide essas propriedades separadamente, sem afirmar que foram cobertas pelos pares desta galeria.
Não envie documentos privados a serviços externos sem autorização. Trabalhe no arquivo dentro da pasta escolhida pela pessoa e prefira corrigir a fonte, reexportar e conferir o resultado. Um DOCX correto não garante que qualquer exportação PDF preserve a estrutura.
