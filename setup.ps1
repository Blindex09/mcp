# MCP Skills Server - Windows Setup Script
# Execução: .\setup.ps1

Write-Host "🚀 MCP Skills Server - Setup para Windows`n" -ForegroundColor Cyan

# Verifica Python
Write-Host "📋 Verificando Python..." -ForegroundColor Yellow
$pythonPath = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $pythonPath) {
    Write-Host "❌ Python não encontrado no PATH" -ForegroundColor Red
    Write-Host "   Instale de: https://www.python.org/downloads/" -ForegroundColor Gray
    exit 1
}
Write-Host "✅ Python encontrado: $pythonPath`n" -ForegroundColor Green

# Instala dependências
Write-Host "📦 Instalando dependências..." -ForegroundColor Yellow
python -m pip install -q -r "$PSScriptRoot\requirements.txt" 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Dependências instaladas`n" -ForegroundColor Green
} else {
    Write-Host "⚠️  Erro ao instalar dependências" -ForegroundColor Yellow
}

# Testa servidor
Write-Host "🧪 Testando servidor MCP..." -ForegroundColor Yellow
python "$PSScriptRoot\test.py" | ForEach-Object { Write-Host $_ }

# Setup
Write-Host "`n🔧 Registrando serviço MCP..." -ForegroundColor Yellow
python "$PSScriptRoot\setup.py" | ForEach-Object { Write-Host $_ }

Write-Host "`n📝 Próximos passos:" -ForegroundColor Cyan
Write-Host "  1. Feche Claude Desktop completamente" -ForegroundColor White
Write-Host "  2. Abra novamente Claude Desktop" -ForegroundColor White
Write-Host "  3. As skills estarão disponíveis!" -ForegroundColor White

Write-Host "`n✨ Setup concluído!" -ForegroundColor Green
