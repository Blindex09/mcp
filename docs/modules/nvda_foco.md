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

## Execução ao vivo na VM e alinhamento com o Guidepup, 05/11/2026

A execução real numa máquina virtual Windows com NVDA controlado pelo Guidepup
revelou cinco causas na costura entre `nvda/focus.mjs`, `nvda/walk.mjs` e a
implementação interna do `@guidepup/guidepup` (`NVDAClient.ts`,
`navigateToWebContent.ts` e `overrides/userConfig/nvda.ini`):

1. O NVDA insere espaços nas transições entre letras maiúsculas, minúsculas e
   dígitos ao anunciar o título da janela (`A11yNvda...` é falado como
   `A 11y Nvda ...`). A conferência foi ajustada para normalizar o texto falado
   e o marcador em minúsculas e sem espaços ou pontuação, seguindo o padrão de
   `cleanString.ts` do Guidepup.
2. No `NVDAClient.ts` do Guidepup, o modo padrão `capture: "initial"` encerra a
   escuta do evento `speak` na primeira mensagem recebida. Quando o NVDA emite
   um pacote `speak` inicial sem texto antes da frase falada, a frase real é
   descartada. O `nvda.start` passou a usar `capture: true`, enquanto comandos
   auxiliares de preparação e troca de janela (`exitFocusMode`,
   `toggleBetweenBrowseAndFocusMode`, `Alt+Escape`) usam `{ capture: false }`
   como em `navigateToWebContent.ts`.
3. Na reativação após `page.reload()`, chamar `windowsActivate` novamente sobre
   uma janela já ativa e maximizada executava `ShowWindow(hWnd, 9)`
   (`SW_RESTORE`), desmaximizando a janela e transferindo o foco para a janela
   de fundo. Agora, quando a janela já foi ativada na sessão, o controle
   atualiza o título, garante a maximização e confere o título no NVDA antes de
   recorrer a uma nova ativação externa.
4. Após confirmar o foco da janela, o controle foca e clica no `body` e alterna
   `toggleBetweenBrowseAndFocusMode` duas vezes seguido de `exitFocusMode`,
   sincronizando o cursor virtual do NVDA com o documento web antes da
   navegação por Tab e seta.
5. O `nvda.ini` distribuído pelo `@guidepup/nvda` traz `MSTTS_V110_enGB_GeorgeM`
   fixo e `showSpeechViewerAtStartup = True`. Em sistemas Windows em português
   (onde só existem as vozes `MSTTS_V110_ptBR_DanielM` e `MariaM`), o script
   `instalar-na-vm.ps1` agora ajusta a voz para a voz OneCore instalada e
   desativa a abertura automática da janela do Speech Viewer.

Verificação: 17 testes Node em `nvda/focus.test.mjs`, `nvda/vm/agent.test.mjs`
e `nvda/window.test.mjs` passaram; 8 testes Python em `tests/test_nvda_vm.py`
passaram; e a execução ao vivo na VM (o endereço do agente em `A11Y_MCP_NVDA_VM`) contra
`https://example.com` concluiu com `erro: null`, 12 confirmações seguidas de
foco (`confirmado: true`), janela maximizada (`1358x636`) e captura real da
fala do NVDA tanto em `tab` (`Learn more, link`) quanto em `leitura`
(`This domain is for use in documentation examples without needing permission.`,
`Avoid use in operations.`, `link, Learn more`).

Referências consultadas: [ativação no Guidepup](https://www.guidepup.dev/docs/api/class-windows-activate),
[testes com NVDA](https://www.guidepup.dev/docs/screen-reader-testing/testing-nvda)
e [restrições de SetForegroundWindow](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setforegroundwindow).
