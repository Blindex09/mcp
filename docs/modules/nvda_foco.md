# Ativação e confirmação de foco do NVDA

Registro de 30/10/2026. Implementação em `nvda/focus.mjs`, usada por
`nvda/walk.mjs` tanto na linha de comando quanto no agente HTTP.

## Problema observado

O Guidepup 0.35.0 capturou anúncios reais das Configurações do Windows enquanto
o navegador de teste estava aberto no BlindHelp. A rotina anterior chamava
`windowsActivate` e prosseguia sem comprovar a ativação. O retorno dessa chamada
não garantia que a janela tivesse assumido o primeiro plano.

Na versão instalada, o helper também interpola o título recebido em VBS e
PowerShell e usa o identificador do aplicativo em `Get-Process`. A integração
passava `msedge.exe`, enquanto o nome do processo é `msedge`. Esses problemas
foram identificados por leitura do código instalado; a causa específica da
recusa de foco no computador ainda não foi comprovada por uma execução corrigida.

## Mudança implementada

A janela recebe um título temporário com identificador ASCII aleatório. O título
do site não é interpolado em comandos. A ativação usa `msedge`. O comando
`reportTitle` do próprio NVDA precisa anunciar o identificador. Caso a primeira
ativação não se confirme, há uma única tentativa de recuperação com Alt e nova
ativação. A segunda recusa encerra a navegação, sem laço de repetição.

Antes e depois de cada Tab ou movimento de leitura, o teste volta a conferir a
janela. Uma perda de foco descarta o passo em andamento e impede os próximos.
Os anúncios da conferência são apagados do log; o resultado registra apenas
booleanos de confirmação, sem gravar o título de outro aplicativo. Não há
alteração de configurações globais de foco do Windows.

O título é alterado apenas na página efêmera que o executor fecha ao terminar.
Por isso, essa execução não serve para avaliar o título original da página. A
confirmação identifica a janela; não certifica, sozinha, o modo de navegação do
NVDA nem a conformidade de cada anúncio. A análise desses anúncios continua com
o modelo cliente.

## Verificação realizada e limites

- Node: 13 testes passaram em `nvda/focus.test.mjs` e `nvda/vm/agent.test.mjs`.
  Cobrem identificador seguro, recuperação, recusa permanente sem laço,
  descarte do passo após perda de foco, limpeza de anúncios privados e recursos.
- Python: oito testes de `tests/test_nvda_vm.py` passaram; Ruff passou e mypy
  passou nos 38 arquivos de origem. Nenhum código Python mudou nesta correção.
- Matriz de cobertura: 12 conceitos cobertos, um parcial e uma lacuna, com saída
  1 pelas pendências já declaradas de avaliações de guias e revisão de harness
  por geração de modelo. Não mede a eficácia do controle de foco do Windows.
- A tentativa de iniciar o teste ao vivo da nova implementação foi bloqueada
  pela revisão automática de segurança, que informou apenas bloqueio por política.
  Não houve execução alternativa para contornar a recusa. O funcionamento real
  desta recuperação permanece pendente; testes simulados não o comprovam.

Antes desta alteração, a pessoa confirmou ter ouvido o NVDA do Guidepup nos
alto-falantes Realtek, mantendo a configuração de áudio do NVDA instalado.
Essa confirmação prova o roteamento de áudio naquela execução, não o foco.
Os documentos do BlindHelp não foram substituídos com resultados desta correção.

## Janela maximizada, 30/10/2026

O executor de NVDA no Edge inicia com `--start-maximized` e `viewport: null`,
para que a área da página acompanhe a janela, em vez do viewport emulado de
1280 por 720 que o Playwright usa por padrão. Após cada tentativa de ativação,
inclusive a recuperação e a ativação depois de recarregar a página, o executor
solicita maximização pelo protocolo do próprio navegador e confere o estado.
Se a janela não confirmar `maximized`, o teste termina com erro. A sessão de
controle é desconectada mesmo em caso de falha.

O resultado bruto registra em `janela` o estado e a área interna real em pixels
CSS, além da escala de pixels do dispositivo. Isso não altera o zoom do site ou
as preferências do Windows. Não modifica os testes específicos de reflow ou de
telas menores do servidor Python, nem tenta maximizar navegadores sem interface.

Verificação: 15 testes Node passaram, incluindo contrato de inicialização com
viewport livre, maximização da janela correta, dimensões e desconexão na falha.
Ruff, mypy e os oito testes Python da integração também passaram. A matriz foi
executada novamente: 12 conceitos cobertos, um parcial e uma lacuna já descritos.
A execução real continua pendente pelo bloqueio de segurança anterior; não foi
tentada uma rota alternativa. Esses testes não comprovam a maximização na tela
do usuário nem a correção do foco ao vivo.

Referências consultadas: [ativação no Guidepup](https://www.guidepup.dev/docs/api/class-windows-activate),
[testes com NVDA](https://www.guidepup.dev/docs/screen-reader-testing/testing-nvda)
e [restrições de SetForegroundWindow](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setforegroundwindow).
