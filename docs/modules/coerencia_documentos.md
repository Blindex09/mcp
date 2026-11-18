Coerência entre código, guias e documentos acessíveis

Revisão de 29/10/2026

Foram corrigidas cinco inconsistências demonstradas pelo código ou pelos textos existentes. Os passos de reprodução chegavam ao gerador como parágrafo com números digitados; agora report_spec usa blocos de lista nativa por modalidade, reiniciando a numeração. O teste test_report_qa.py verifica o contrato, os parágrafos numPr do DOCX e as tags L no PDF real.

Os guias de Excel confundiam congelar painéis com disponibilizar relações de cabeçalho. O texto agora distingue apresentação visual de tabela, nomes definidos, configuração e suporte do leitor. Os guias e o exemplo web também deixaram de condenar automaticamente títulos significativos dentro de itens de lista. Tab, leitura linear e navegação por títulos não precisam percorrer os mesmos elementos; a avaliação considera relações incoerentes, não diferenças esperadas entre modalidades.

Os guias especialista Excel e de navegação foram corrigidos também na origem Qaaccessibility. O índice agent_knowledge.md foi regenerado. O teste unitário do especialista e o teste de sincronização do índice passaram: dez testes. Ruff passou nos dois arquivos Python alterados e mypy passou no especialista, com importações acompanhadas em modo silencioso. Isso não é teste de todos os provedores do Qaaccessibility.

O validador XLSX distingue arquivos genéricos do contrato de relatórios do MCP. A ferramenta de validação genérica registra fatos das planilhas, tabelas, nomes e congelamento sem exigir seis abas de auditoria. A geração de relatório continua validando as seis abas e seus cabeçalhos. A regressão da galeria verifica os dois caminhos.

A galeria passou de 42 para 46 arquivos, acrescentando quatro XLSX reais, em dois pares: cabeçalhos e status com texto versus cor isolada. Os pares foram abertos no Excel instalado em instância própria, oculta e somente para leitura, exportados e conferidos visualmente. O congelamento é igual no par de cabeçalhos; a diferença demonstrada está na tabela declarada, sem afirmar que tabela seja a única técnica aceitável.

Avaliação das instruções

Antes de instalar os guias revisados, 24 casos variados foram avaliados em três rodadas com guia e três ablações no cliente Codex padrão: 72 de 72 decisões aceitas em cada condição. A primeira rodada revelou duas ambiguidades do avaliador, preservadas no registro. O gabarito da célula mesclada foi corrigido porque o fato isolado não comprova falha; a pergunta VoiceOver passou a explicitar ausência de execução. O guia não foi alterado para acomodar rótulos incorretos. Os resultados não demonstram ganho causado pelo guia. Outros modelos e observação prolongada continuam pendentes. As decisões e hashes estão em coerencia_documentos_evidencias.json.

Fontes conferidas

Microsoft, boas práticas de acessibilidade no Excel: https://support.microsoft.com/en-us/accessibility/excel/accessibility-best-practices-with-excel-spreadsheets
NV Access, NVDA User Guide, Microsoft Excel: https://download.nvaccess.org/documentation/en/userGuide.html#MicrosoftExcel
WHATWG, conteúdo do elemento li: https://html.spec.whatwg.org/multipage/grouping-content.html#the-li-element
W3C APG, navegação por teclado: https://www.w3.org/WAI/ARIA/apg/practices/keyboard-interface/
W3C, técnica PDF21 para listas: https://www.w3.org/WAI/WCAG22/Techniques/pdf/PDF21

Arquivos da pessoa

O MCP foi iniciado por um cliente de protocolo real e gerou novos arquivos BlindHelp_pagina_inicial.xlsx, .docx e .pdf, substituídos em C:\relatórioss. A cópia BlindHelp_pagina_inicial_corrigida.xlsx recebeu o mesmo arquivo. O XLSX tem 18 ocorrências, 31 colunas, Site em A1, Sistema operacional em B1 e Navegadores em C1, sem Título da página. O DOCX tem 37 páginas no Word e o PDF 40 páginas; ambos foram renderizados e todas as páginas conferidas. As verificações estruturais dos três arquivos passaram; a checagem automática PDF/UA do PDF passou. A regeneração usa registros anteriores e não é nova auditoria da página.

Limites

Nenhuma fala real de NVDA, JAWS ou VoiceOver foi capturada no Word, Excel ou leitor PDF. A estrutura programática, os downloads por teclado e a aparência não comprovam todas as combinações de aplicativo e leitor. As cópias didáticas inadequadas possuem defeitos deliberados que um validador genérico pode não detectar. Nenhum resultado automático certifica acessibilidade integral.

A matriz de cobertura retornou código 1: 12 conceitos cobertos, um parcial e uma lacuna. Permanecem avaliação ampla dos demais guias/modelos e revisão do harness em nova geração de modelo. O documento de metodologia indicado nas regras não existe nesta cópia do MCP; foi consultada a fonte existente no Qaaccessibility. As alterações ficaram locais; havia numerosas alterações anteriores nos mesmos arquivos, preservadas sem inclusão indiscriminada em commit.


Achados adicionais durante a regressão

A navegação e o cartão inicial ainda anunciavam apenas Word e PDF. Agora incluem Excel; a regressão da galeria depois dessa alteração passou com 18 testes, incluindo downloads efetivos dos quatro XLSX e percurso por teclado.

A regressão conjunta revelou um erro no teste de streaming: o extrator do contador incluía o ponto final e a primeira linha da lista na conversão para inteiro. Três medições isoladas registraram 12 atualizações na região assertiva e uma no status final do exemplo adequado. O teste agora extrai o contador somente da primeira linha e conserva os limites numéricos exigidos; mede diretamente os dois exemplos, sem reconstruir todos os outros cenários. O teste corrigido passou no navegador real.

Essa investigação encontrou também uma promessa indevida na explicação da galeria: contar mutações como se fossem anúncios que o leitor efetivamente fala. O gerador, o texto dos exemplos e o comentário do observador agora distinguem atualizações de regiões vivas de fala capturada; a página chat-ia.html foi medida e gerada novamente. Não houve alteração no mecanismo de observação nem execução de leitor real. A explicação da variante de lista sem subtítulos também foi alinhada ao exemplo válido com subtítulos, preservando suas medições.


Verificação final

Ruff passou no projeto; mypy verificou 38 arquivos sem erros. Os testes específicos anteriores tiveram 81 aprovações, a galeria após o ajuste de navegação teve 18 e a origem Qaaccessibility teve dez. A suíte conjunta terminou em 1272,65 segundos: 418 aprovados, um ignorado e uma falha no extrator antigo do teste de streaming. A suíte já estava em execução com esse teste anterior quando a correção foi instalada; não houve outra falha. O teste corrigido foi executado diretamente no navegador e passou em 7,78 segundos, e novamente após o pedido de tentar de novo, em 4,50 segundos. Esses resultados são execuções separadas, não uma nova execução integral com todos os testes verdes. Os arquivos entregues e seus limites permanecem os registrados acima.
