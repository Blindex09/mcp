# Precisão das medições de acessibilidade

Revisão de 28/10/2026. Escopo: perdas de detalhes nos resultados, navegação até alvos, aprovação de formulários e limites numéricos. Não constitui certificação de todas as ferramentas ou de todos os critérios WCAG.

## Base oficial consultada

- [WCAG-EM 2.0, nota de 23/07/2026](https://www.w3.org/TR/2026/NOTE-wcag-em-2-20260723/): definir escopo e suporte, explorar funcionalidades e estados, selecionar amostra representativa e processos completos, avaliar e registrar resultados. Uma visita à página inicial não comprova um site inteiro.
- [ACT Rules Format 1.1](https://www.w3.org/TR/act-rules-format/): resultados passed, failed, inapplicable, cantTell e untested têm significados distintos. Incerteza real não pode virar aprovação ou reprovação. Os testes desta revisão não declaram conformidade formal com uma regra ACT específica.
- [WAI, seleção de ferramentas](https://www.w3.org/WAI/test-evaluate/tools/selecting/): ferramentas ajudam a avaliação e podem produzir resultados incorretos; julgamento contextual continua necessário.
- [WCAG 2.5.8](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum): medir pixels CSS e espaçamento; considerar as exceções. Caixas retangulares são fatos geométricos, não prova de que uma forma irregular contém uma área clicável de 24 por 24 pixels.
- [WCAG 1.4.3](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html): limiares de contraste sem arredondamento para decidir aprovação; texto grande em negrito a partir de 14 pontos. O cálculo usa 14 × 96 ÷ 72 pixels CSS, sem antecipar o limite para 18,66.
- [WCAG 2.4.11](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html): AA se refere a componente inteiramente oculto por conteúdo do autor; sobreposição parcial não é automaticamente falha. A amostra de cinco pontos da sonda não equivale à prova geométrica de cobertura integral.
- [WCAG 2.4.7](https://www.w3.org/WAI/WCAG22/Understanding/focus-visible.html): verificar indicador de foco no uso por teclado. Estilo computado ou ausência de outline isolados não decidem visibilidade.
- [Introdução ao APG](https://www.w3.org/WAI/ARIA/apg/about/introduction/): padrões de implementação auxiliam a avaliação; a divergência de uma orientação APG não é, isoladamente, prova de violação de WCAG.

## Defeitos corrigidos e regressões

Auditoria axe: o padrão devolvia apenas cinco nós por regra, embora contasse todos. Agora preserva todos os exemplos de falha e de revisão manual, inclusive HTML. Se um chamador interno escolher um limite, o resultado informa omitted_occurrences. Regressão: test_summarize_axe_preserves_all_locations_and_explicit_truncation.

Inventário: havia corte de descoberta em 600 elementos e de descrição em 200. O inventário usa zero como padrão para listar todos e mantém a opção de limite explicitamente solicitado. As sondas de alvos e a chamada única usam inventário completo. Regressões: test_full_dossier_does_not_stop_discovery_at_six_hundred, em Chromium e Firefox; test_single_call_returns_all_controls_on_large_page.

Tabulação: a varredura ocultava detalhes após 60 paradas, listas de sobreposição eram cortadas em 20, e a comparação entre navegadores parava em 60. Agora preservam todas as paradas até o fim real do percurso ou orçamento explicitamente solicitado. Regressões: test_large_page_preserves_every_keyboard_stop e test_browser_comparison_measures_after_sixtieth_stop.

Mapa: listas detalhadas de títulos, marcos, imagens, links, formulários, campos, tabelas, listas e regras de hover eram cortadas. O inventário desses itens agora é completo. A análise visual por pares também passou a incluir todos os elementos elegíveis; contagens e exemplos continuam sendo fatos para julgamento contextual. O teste de reflow devolve todos os elementos com transbordamento, sem cortar a lista nos primeiros 15. Regressão adicional: test_reading_order_and_reflow_do_not_drop_late_content. Regressão: test_page_map_keeps_content_after_previous_inventory_caps.

Observação: a árvore era cortada em 400 linhas; mudanças, em 40; anúncios, em 20, embora o cursor de leitura consumisse todos. Agora a observação e as diferenças padrão preservam esses dados. O observador também mantém o texto completo de cada anúncio. Regressões: test_tree_diff_preserves_more_than_forty_changes e test_observation_preserves_long_tree_and_all_live_updates. A demonstração de chat deixou de anunciar o limite antigo de 20.

Alcance por seletor: sem uma consulta prévia ao inventário, o alvo não tinha identificador interno e nunca era reconhecido, mesmo quando recebia foco. Agora a comparação também usa o elemento ativo da raiz do próprio alvo. Regressão: test_reach_css_target_without_prior_dossier, reproduzida falhando antes da correção.

Envio aprovado: o evento retido continuava chegando ao handler do site, que podia desabilitar o botão antes da aprovação. A captura agora impede a propagação nesse primeiro envio retido; na repetição autorizada, o handler roda normalmente. Regressão: test_held_submission_does_not_run_site_handler_before_replay, reproduzida falhando antes da correção. As proteções de rede e aprovações pontuais continuam ativas.

Precisão numérica: caixas do inventário mantêm frações de pixel. Um alvo de 23,75 pixels não é mais contado como 24. O limite de texto grande em negrito também usa a conversão exata de pontos. Regressões: test_target_size_does_not_round_a_small_target_up_to_twenty_four e test_bold_large_text_threshold_uses_exact_fourteen_point_conversion.

## Verificação real e limites

Em processo novo, pelo protocolo MCP, a página inicial do BlindHelp devolveu 26 ocorrências de contraste com 26 exemplos, um problema de idioma com um exemplo e nove ocorrências de tamanho com nove exemplos. Não houve omissão nessa saída.

A busca NVDA, autorizada pela pessoa, passou a mostrar Search results e um resultado para Vocalizer Expressive após a aprovação exclusiva do formulário. A requisição de estatísticas permaneceu retida e foi descartada ao fechar. A conclusão se limita ao envio e à chegada aos resultados; não aprova a acessibilidade da página de resultados nem transcreve fala de leitor de tela. A origem histórica exata do bloqueio anterior não foi registrada de forma suficiente para atribuir causalidade exclusiva; a reprodução local prova o defeito de propagação e a verificação real prova que o fluxo funciona após as correções.

NVDA real continua sem endereço e token de VM neste ambiente. A consulta ao Hyper-V foi recusada pelas permissões do sistema. Nenhum NVDA do computador foi encerrado ou reconfigurado. Não há executor de Android/iOS nem prova real de VoiceOver/JAWS. Isso é limitação de execução, não resultado de aprovação ou falha dos sites.

O conhecimento existente foi consultado e a matriz de componentes recebeu uma correção localizada, sem recriar o acervo: estrutura de títulos, recomendações APG, tratamento de erros, foco, exceções de tamanho de alvo, escopo de avaliação e estados de resultado. A indicação de um único h1 deixou de ser uma exigência universal. Uma seção com fontes oficiais esclarece que recomendações de implementação não acrescentam requisitos WCAG.

Antes da incorporação, o cliente Codex avaliou 24 cenários em três repetições com o guia e três sem ele. As 144 justificativas foram revisadas. O avaliador estrito inicial reportou 16/24 nas três rodadas com guia e 17/24, 16/24, 16/24 sem guia: sete perguntas com propriedade confirmada admitiam property_satisfied, embora o gabarito só aceitasse insufficient; no select não medido, insufficient também era uma resposta correta. Após revisar essas ambiguidades do gabarito, foram aceitas 72/72 decisões com guia e 72/72 na ablação. Os casos de defeito confirmado continuaram exigindo correção e reteste. Não houve ganho demonstrado nesse conjunto, nem prova em outros modelos. Gabarito original, justificativas, revisão e hash do guia estão em precisao_testes_evidencias.json. Não se apresenta essa avaliação delimitada como aprovação de todo o acervo; a observação das próximas execuções permanece necessária.

A regra de origem da matriz cita Qaaccessibility e este servidor. A pesquisa por arquivo com o mesmo nome ou título no repositório Qaaccessibility não encontrou uma cópia correspondente; nenhum arquivo daquele projeto foi editado nem se declarou sincronização inexistente.

Verificação de código: ruff e mypy passaram, com 38 fontes verificadas. A suíte geral iniciada nesta revisão terminou com 401 aprovados e um ignorado em 1134,30 segundos. Após os ajustes seguintes, a regressão dos sete módulos de medição passou com 152 testes em 358,14 segundos; o recorte de cobertura com os ajustes finais passou com 18 testes em 77,87 segundos, e servidor, protocolo e contratos de limites passaram com 11 testes em 71,95 segundos. Esses números são execuções separadas, com sobreposição; não devem ser somados como testes únicos. A matriz de conceitos continua em 12 cobertos, um parcial e uma lacuna, terminando com código 1 pelas pendências declaradas. As alterações permanecem locais para preservar o trabalho anterior já modificado no repositório; não houve publicação.

Conferência final pelo protocolo MCP em 29/10/2026: o guia devolvido corresponde integralmente ao arquivo avaliado (SHA-256 d8348e18b338c6a09d03d55bec0794813ebcd237edead4f2f325add30318f7c2), e o schema publicado do inventário usa max_elements=0. Os quatro testes selecionados de conteúdo/catálogo passaram após a incorporação; ruff, mypy e git diff --check também passaram. O processo novo foi encerrado após a conferência; conexões antigas carregadas antes das mudanças precisam recarregar o servidor.
