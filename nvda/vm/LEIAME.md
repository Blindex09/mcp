# NVDA de verdade numa máquina virtual

Por que uma VM. O NVDA só tem uma cópia por vez e o Guidepup fecha a do usuário ao iniciar (ele chama `quit()` antes de começar). Numa VM, o seu NVDA, a sua voz e os seus complementos nunca são tocados, e você continua usando o computador e ouvindo a IA normalmente. A fala do NVDA da VM chega ao MCP como texto.

## O que você precisa fazer, uma vez só

1. No VMware, crie uma VM com Windows 10 ou 11 (4 GB de memória, 2 ou 3 processadores, uns 50 GB de disco). Instale o Windows e o VMware Tools. Deixe a **placa de som** da VM ligada: o agente silencia o NVDA por dentro (volume da voz em 0), e a fala continua chegando como texto.
2. Rede da VM: NAT ou somente-anfitrião, as duas servem, desde que o seu computador e a VM se enxerguem. O endereço do seu computador visto pela VM aparece no `ipconfig` do seu computador, no adaptador "VMware Network Adapter VMnet8" (NAT) ou "VMnet1" (somente-anfitrião).
3. Copie a pasta `nvda\` do projeto para dentro da VM (pasta compartilhada do VMware ou pendrive virtual).
4. Dentro da VM, abra o PowerShell **como administrador** na pasta `nvda\vm` e rode:

   powershell -ExecutionPolicy Bypass -File instalar-na-vm.ps1

   Ele instala o Node, baixa o NVDA portátil do Guidepup (uns 400 MB), impede a VM de dormir, libera a porta 8765 só para a rede local, cria o token e liga o agente toda vez que você entrar no Windows. No fim, mostra o endereço e o token.
5. Na VM, configure o login automático (`netplwiz`): o teste precisa de um desktop aberto e desbloqueado.
6. Na primeira execução do NVDA portátil, o Firewall do Windows pergunta se libera: responda **Cancelar** (o Guidepup só fala com o NVDA dentro da própria VM).
7. Reinicie a VM, confira que o agente subiu sozinho, e tire um **instantâneo (snapshot)** dela limpa.

## No seu computador

No JSON do cliente MCP, na entrada do servidor, em `env`:

- `A11Y_MCP_NVDA_VM`: o endereço que o instalador mostrou, por exemplo `http://192.168.100.20:8765`
- `A11Y_MCP_NVDA_TOKEN`: o token que o instalador mostrou
- `A11Y_MCP_NVDA_HOST_ADDR` (opcional): o endereço do seu computador visto pela VM. Com ele, um site seu em `localhost` é aberto na VM pelo endereço certo. O site precisa escutar nessa rede (por exemplo, `python -m http.server --bind 0.0.0.0`) e o firewall do seu computador precisa deixar a VM entrar.

Depois, a ferramenta `a11y_nvda_speech(url)` devolve o que o NVDA falou.

## O que ainda não foi testado com o NVDA de verdade

Tudo aqui foi provado com um NVDA simulado (o agente e o cliente conversam de verdade; só o NVDA é de mentira). Não foi confirmado ainda numa VM de verdade: (1) que o NVDA portátil sobe numa VM, (2) que com a voz em 0 o log de fala continua chegando, (3) que a espera adaptativa da fala (que substitui as pausas fixas do primeiro teste) acompanha o ritmo do NVDA real. Quem responde é a primeira execução na VM.
