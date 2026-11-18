# Verificação de planilhas no Excel

Rodada de 24/10/2026, cliente Codex, servidor MCP local, Excel
16.0.20430.20182. O relatório didático foi criado por a11y_create_report
com o registro 20261024-183529-html-local. O achado da página de exemplo
é intencional e não representa uma avaliação de um site externo.

## Defeitos reproduzidos e proteção

A primeira planilha exigiu reparo do Excel. O registro nativo
error074480_01.xml informou a remoção de AutoFilter e Table de
/xl/tables/table1.xml. O gerador aplicava simultaneamente o filtro da
planilha e o filtro da tabela ao mesmo intervalo. A versão corrigida usa
somente o filtro da tabela quando há achados e mantém o filtro da folha
quando não há tabela. A abertura real posterior preservou tabela e filtros
sem pedir reparo. validate_xlsx detecta filtros de folha que sobrepõem uma
tabela. tests/test_workbook_filters.py reproduz a duplicação e cobre a
planilha sem achados.

O verificador nativo também sinalizou contraste na tabela com o estilo
Medium2. Com Light1, o painel mostrou “Está bom! Não encontramos nenhum
problema.” Essa comparação comprova o resultado observado no Excel;
não estabelece uma fórmula universal de contraste para estilos do Office.

## Interação observada

Tab moveu entre células de cabeçalho. Ctrl+PageDown mudou de Resumo para
Problemas. Alt+Down abriu o filtro da tabela. A versão final com Light1
abriu sem reparo e passou pelo verificador nativo. Não houve captura de
fala, nem comprovação de anúncio de cabeçalhos pelo leitor de tela.
Ausência de alertas automáticos não comprova acessibilidade completa.

Arquivo entregue: C:\Users\olive\Downloads\Planilha_acessibilidade_MCP_20261024_final.xlsx.

## Limites e verificações do projeto

Ruff e mypy passaram. A suíte conjunta terminou com 371 testes aprovados
e um ignorado; os dois testes de filtros foram executados novamente após
a alteração final do estilo e passaram. A matriz de cobertura registrou
12 de 14 conceitos cobertos; permanecem as lacunas já existentes de
avaliação ampla dos guias por modelos e revisão do harness por geração.

A navegação semântica item a item e célula a célula do PDF de demonstração
continua não comprovada. O Acrobat 26.2.22031.0 apresentou repetidamente
“Font Capture: Windows - Erro de Aplicativo”, exceção 0xc06d007e, inclusive
após reabrir e nas preferências. “Sempre exibir o cursor de seleção do
teclado” já estava habilitado. Não foi estabelecida a causa desse erro,
nem relação causal com o gerador. Seleção de texto ou pesquisa por palavra
não foi contabilizada como navegação semântica de tabela. Não havia
sessões conectadas no controle de documentos na retomada.

As mudanças de produção estão em report_artifacts.py, que já era arquivo
não versionado de uma implementação maior antes desta rodada. Não houve
commit para não incluir silenciosamente esse trabalho anterior; a correção
fica local, junto do teste e desta documentação. O módulo não é declarado
concluído e não recebe tag de conclusão.
