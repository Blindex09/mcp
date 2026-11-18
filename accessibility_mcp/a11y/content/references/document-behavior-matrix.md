# Document behavior matrix: Word DOCX, PDF and Excel XLSX examples

Origem: este MCP. Contratos dos exemplos de documentos e uso das ferramentas deste servidor.
Fontes oficiais consultadas em 2026-10-29. Textos sintetizados; arquivos de terceiros não foram incorporados.

## Como usar e o que pode afirmar

Escolha os assuntos pelo significado da tarefa. A galeria está em demo/exemplos-leitor-de-tela/documentos.html.
Para produzir arquivos, escreva o conteúdo e use a11y_create_document; para relatório dos achados, a11y_create_report. Valide o arquivo efetivo com a11y_validate_document.
O MCP mede estrutura; o modelo do cliente julga significado, qualidade e cobertura. Não escolha casos por palavras-chave nem converta ausência de erros em conformidade.
As técnicas W3C são formas de atender critérios, não uma lista de implementações obrigatórias. A galeria ensina casos delimitados; Bom significa que a propriedade exemplificada foi preservada, não certificação do arquivo.
A inspeção XLSX genérica mede tabelas, cabeçalhos declarados, congelamento, células mescladas e nomes definidos sem exigir as abas de um relatório de auditoria; o significado dos valores e as associações efetivas no leitor exigem revisão. A inspeção DOCX verifica metadados, títulos, alternativas, cabeçalhos de tabela e links sem texto. PDF acrescenta tags, fontes, Unicode e texto extraível. Listas simuladas, propósito de links, sentido da alternativa e ordem lógica exigem julgamento e revisão no aplicativo.
Uma imagem decorativa corretamente marcada não exige a mesma descrição de uma figura informativa. O validador DOCX atual não distingue decoração e pode pedir revisão; o gerador exige alt para as imagens que aceita.
PDF/UA-1 e PDF/UA-2 são perfis distintos. O gerador atual é verificado automaticamente com veraPDF PDF/UA-1; não declare PDF/UA-2. Aprovação automática não comprova todos os requisitos nem WCAG.
A sonda a11y_nvda_speech é para páginas na VM configurada, não abre Word ou leitor de PDF. Não invente fala literal nem declare teste real de documentos sem capturar o leitor no aplicativo. Registre versões, comandos, resultado e limitações. OCR do leitor não torna o arquivo acessível.

## Formulários realmente preenchíveis

Fazer: Use controles preenchíveis com nome, rótulo, tipo, estado, instruções e sequência lógica. Indique campos obrigatórios em texto e nas propriedades que o formato oferece.
Evitar: Não simule campos com linhas de sublinhado nem use somente cor ou asterisco sem explicação. Não confunda uma caixa desenhada com um controle de formulário.
Comportamento esperado, não fala capturada: A pessoa deve reconhecer o campo, entender como preenchê-lo e consultar seu valor ou estado. No PDF, os widgets precisam estar na estrutura de formulário e ligados às tags. No Word, os controles têm título e instruções; isso ainda exige conferir a experiência no aplicativo.
Verificação no aplicativo: Percorra os campos pelo teclado no aplicativo, preencha texto, selecione uma opção e alterne a caixa de seleção. Salve, reabra e confira valores e anúncios. Obrigatório no Word é uma indicação textual; não há envio nem validação programada por macros.
Defeito demonstrado: Os campos mantêm aparência e valores, mas perderam seus nomes acessíveis nas propriedades dos controles.
Medição automática: form_missing_label.
Fontes: [Microsoft — Formulários preenchíveis no Word](https://support.microsoft.com/en-us/word/create-a-form-in-word-that-users-can-complete-or-print); [W3C — PDF12 Nome papel valor dos campos](https://www.w3.org/WAI/WCAG22/Techniques/pdf/PDF12); [W3C — PDF5 Campos obrigatórios](https://www.w3.org/WAI/WCAG22/Techniques/pdf/PDF5)

## Sumário automático e clicável

Fazer: Gere o sumário a partir dos títulos e use links que levem às seções corretas. No Word, atualize o campo depois de editar títulos ou páginas.
Evitar: Não apresente apenas uma lista de títulos como se fosse navegação clicável. Não confunda o sumário no corpo com os marcadores laterais do PDF.
Comportamento esperado, não fala capturada: As entradas devem permitir chegar à seção indicada. O DOCX tem campo de sumário com links iniciais; o PDF tem entradas clicáveis e marcadores. A atualização posterior do campo depende do editor.
Verificação no aplicativo: Ative cada entrada pelo teclado e confira o título de chegada. No Word, edite um título em uma cópia, atualize o sumário e confira novamente. No PDF, teste também os marcadores separadamente.
Defeito demonstrado: As entradas continuam visíveis, mas foram convertidas em texto sem links; o campo automático do Word foi retirado.
Medição automática: o validador estrutural pode não detectar este defeito; revisar o conteúdo e a estrutura específica.
Fontes: [Microsoft — Sumário automático no Word](https://support.microsoft.com/en-us/word/training/insert-a-table-of-contents); [W3C — PDF2 Marcadores](https://www.w3.org/WAI/WCAG22/Techniques/pdf/PDF2); [W3C — PDF11 Links e estrutura](https://www.w3.org/WAI/WCAG22/Techniques/pdf/PDF11)

## Links internos com destino válido

Fazer: Vincule o texto descritivo a um marcador ou seção existente e confira a chegada no arquivo final.
Evitar: Não deixe links apontando para marcadores removidos nem suponha que a navegação interna sobrevive a qualquer exportação.
Comportamento esperado, não fala capturada: A ativação deve levar ao trecho indicado. A posição do cursor e o anúncio ao chegar variam com o leitor e o aplicativo; a existência do destino não prova o foco real.
Verificação no aplicativo: Percorra e ative os links pelo teclado, confira a seção de destino e continue a leitura a partir dela. Teste novamente depois de exportar.
Defeito demonstrado: O link foi alterado para apontar a um destino que não existe no documento.
Medição automática: broken_internal_link.
Fontes: [W3C — PDF11 Links e estrutura](https://www.w3.org/WAI/WCAG22/Techniques/pdf/PDF11); [W3C — PDF2 Marcadores](https://www.w3.org/WAI/WCAG22/Techniques/pdf/PDF2)

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

## Planilhas com cabeçalhos associados aos dados

Fazer: Use estrutura tabular simples, nomes claros e cabeçalhos associados aos dados. Confira no Excel e no leitor escolhido como os cabeçalhos são identificados; podem ser necessários recursos e configurações específicos.
Evitar: Não trate congelamento visual como definição semântica de cabeçalho, nem considere o uso de Tabela a única solução possível.
Comportamento esperado, não fala capturada: O exemplo bom define uma Tabela do Excel com linha de cabeçalhos. O ruim mantém os mesmos textos e o mesmo congelamento, mas remove a definição da Tabela. A fala real e as associações no leitor não foram executadas; intervalos nomeados ou outras soluções precisam ser avaliados em contexto.
Verificação no aplicativo: Abra cada arquivo no Excel, confira a existência da Tabela e da linha de cabeçalhos e navegue entre os dados. Com NVDA real, confira a configuração de anúncio de cabeçalhos; quando necessário, defina os cabeçalhos com os comandos documentados e registre a combinação usada.
Defeito demonstrado: O vínculo explícito da Tabela com sua linha de cabeçalhos foi retirado. A aparência e o congelamento permanecem; isso não comprova falha WCAG universal de todo intervalo que não seja uma Tabela.
Medição automática: o validador estrutural pode não detectar este defeito; revisar o conteúdo e a estrutura específica.
Fontes: [Microsoft — Boas práticas de acessibilidade no Excel](https://support.microsoft.com/en-us/accessibility/excel/accessibility-best-practices-with-excel-spreadsheets); [NV Access — Cabeçalhos no Microsoft Excel](https://download.nvaccess.org/documentation/en/userGuide.html#MicrosoftExcel)

## Situação da planilha disponível além da cor

Fazer: Mantenha um valor textual que identifique a situação de cada registro, além das cores.
Evitar: Não dependa exclusivamente de vermelho e verde para transmitir a situação.
Comportamento esperado, não fala capturada: Nos arquivos os registros de participação são iguais. O bom escreve Revisar e Concluído na coluna Situação, além das cores; no ruim esses valores foram removidos e só a cor permanece.
Verificação no aplicativo: Confira os valores da coluna Situação sem usar as cores. No Excel e com o leitor escolhido, navegue até cada célula e registre se a informação está disponível em texto.
Defeito demonstrado: Os textos da coluna Situação foram retirados, mantendo os preenchimentos vermelho e verde. O significado da cor é o conteúdo declarado deste exemplo, não uma regra automática baseada em nomes de cor.
Medição automática: o validador estrutural pode não detectar este defeito; revisar o conteúdo e a estrutura específica.
Fontes: [Microsoft — Boas práticas de acessibilidade no Excel](https://support.microsoft.com/en-us/accessibility/excel/accessibility-best-practices-with-excel-spreadsheets)

## Limites complementares

O gerador oferece campos text, checkbox e choice em blocos field, com field_name, text como rótulo, help_text, required, value ou checked e options nas escolhas. DOCX usa controles nativos de conteúdo; PDF usa AcroForm e widgets ligados às tags. Não há macros, envio automático, campos de assinatura ou grupos de rádio. A indicação de obrigatório no Word não é validação automática; no PDF há sinalizador Required, mas envio e avisos dependem do aplicativo e não foram programados aqui.
toc=true gera campo TOC com resultado inicial clicável no Word e sumário clicável no PDF; atualize o campo no Word após editar. Títulos aceitam id, e links aceitam url=#id. O destino deve existir. Sumário e marcadores PDF são recursos distintos. Aparências iniciais dos campos PDF usam fonte incorporada Windows-1252; o corpo do documento aceita Unicode. Não afirme suporte a todos os alfabetos e aplicativos sem verificar.
Confira também contraste, uso de cor, ampliação, instruções de erros e comportamento real ao preencher. Os pares são exemplos delimitados; não comprovam toda experiência de formulário com tecnologia assistiva.
Não envie documentos privados a serviços externos sem autorização. Trabalhe no arquivo dentro da pasta escolhida pela pessoa e prefira corrigir a fonte, reexportar e conferir o resultado. Um DOCX correto não garante que qualquer exportação PDF preserve a estrutura.
