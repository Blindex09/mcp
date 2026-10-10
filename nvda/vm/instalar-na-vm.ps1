# Roda DENTRO da maquina virtual (nunca no seu computador): prepara o Windows da VM para o agente do NVDA.
# Abra o PowerShell da VM "como administrador" e rode:   powershell -ExecutionPolicy Bypass -File instalar-na-vm.ps1
# Faz: instala o Node (se faltar), baixa o NVDA portatil do Guidepup, evita que a VM durma ou apague a tela,
# libera a porta do agente so para a rede local, e cria uma tarefa que liga o agente toda vez que voce entrar no Windows.
# Mostra no fim o token e o endereco da VM para configurar no MCP.
param(
  [int]$Porta = 8765,
  [ValidateSet("volume", "sem-fala", "")] [string]$Silencio = "volume"
)
$ErrorActionPreference = "Stop"
$pastaNvda = Split-Path -Parent $PSScriptRoot   # a pasta nvda\ (este script fica em nvda\vm\)

function Passo($texto) { Write-Host ""; Write-Host "== $texto" -ForegroundColor Cyan }

$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) { throw "Abra o PowerShell como administrador (clique direito, Executar como administrador)." }

Passo "1/6 Node.js"
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
  winget install -e --id OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements
  $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
}
node --version

Passo "2/6 Pacotes do agente e NVDA portatil do Guidepup (uns 400 MB)"
Push-Location $pastaNvda
npm install --no-fund --no-audit
npx @guidepup/setup install nvda
Pop-Location

Passo "3/6 A VM nao pode dormir nem apagar a tela durante o teste"
powercfg /change standby-timeout-ac 0
powercfg /change monitor-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
Set-ItemProperty "HKCU:\Control Panel\Desktop" -Name ScreenSaveActive -Value "0"

Passo "4/6 Firewall: a porta $Porta so para a rede local"
if (-not (Get-NetFirewallRule -DisplayName "A11Y NVDA agente" -ErrorAction SilentlyContinue)) {
  New-NetFirewallRule -DisplayName "A11Y NVDA agente" -Direction Inbound -Protocol TCP -LocalPort $Porta -Action Allow -RemoteAddress LocalSubnet -Profile Any | Out-Null
}

Passo "5/6 Token e inicio automatico"
$arquivoToken = Join-Path $env:USERPROFILE ".a11y-nvda-token"
if (Test-Path $arquivoToken) { $token = (Get-Content $arquivoToken -Raw).Trim() }
else {
  $bytes = New-Object byte[] 24
  [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
  $token = [Convert]::ToBase64String($bytes).Replace("+", "-").Replace("/", "_").TrimEnd("=")
  Set-Content -Path $arquivoToken -Value $token -NoNewline
}
$iniciar = Join-Path $pastaNvda "vm\iniciar-agente.cmd"
@"
@echo off
set NVDA_AGENT_TOKEN=$token
set NVDA_AGENT_PORT=$Porta
set NVDA_SILENCIO=$Silencio
cd /d "$pastaNvda"
node vm\agent.mjs
"@ | Set-Content -Path $iniciar -Encoding ASCII
$acao = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$iniciar`""
$gatilho = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
Register-ScheduledTask -TaskName "A11Y NVDA agente" -Action $acao -Trigger $gatilho -RunLevel Limited -Force | Out-Null
Start-ScheduledTask -TaskName "A11Y NVDA agente"

Passo "6/6 Pronto. Configure no cliente MCP (no seu computador, nao aqui):"
$enderecos = Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notmatch "^(127|169\.254)\." } | Select-Object -ExpandProperty IPAddress
Write-Host "  A11Y_MCP_NVDA_VM    = http://$($enderecos | Select-Object -First 1):$Porta"
Write-Host "  A11Y_MCP_NVDA_TOKEN = $token"
Write-Host ""
Write-Host "Falta, uma vez so: entrar com login automatico (netplwiz) e, na primeira execucao do NVDA, responder o aviso do Firewall com Cancelar."
Write-Host "Depois tire um instantaneo (snapshot) da VM limpa."
