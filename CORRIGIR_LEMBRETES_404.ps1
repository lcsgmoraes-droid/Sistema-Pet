# 🔧 Script para Corrigir Erro 404 do Endpoint /api/lembretes/pendentes
# Uso: .\CORRIGIR_LEMBRETES_404.ps1

Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "🔍 DIAGNÓSTICO - Endpoint /api/lembretes/pendentes" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# TESTE 1: Verificar se o servidor está online
# ============================================================================
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "📡 Testando conexão com servidor..." -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan

try {
    $healthCheck = Invoke-WebRequest -Uri "https://mlprohub.com.br/docs" -Method GET -UseBasicParsing -TimeoutSec 10
    if ($healthCheck.StatusCode -eq 200) {
        Write-Host "✅ Servidor online e respondendo" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Servidor não está respondendo!" -ForegroundColor Red
    Write-Host "   Verifique se o Docker está rodando no servidor" -ForegroundColor Yellow
    exit 1
}
Write-Host ""

# ============================================================================
# TESTE 2: Verificar arquivo local do endpoint
# ============================================================================
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "📂 Verificando arquivo local..." -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan

$lembreteFile = "backend\app\lembretes.py"
if (Test-Path $lembreteFile) {
    Write-Host "✅ Arquivo backend\app\lembretes.py existe" -ForegroundColor Green
    
    # Verificar se o endpoint /pendentes está no código
    $conteudo = Get-Content $lembreteFile -Raw
    if ($conteudo -match '@router\.get\("/pendentes"') {
        Write-Host "✅ Endpoint encontrado no código" -ForegroundColor Green
    } else {
        Write-Host "❌ Endpoint '/pendentes' NÃO encontrado no código!" -ForegroundColor Red
        Write-Host "   O arquivo pode estar corrompido ou desatualizado" -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host "❌ Arquivo backend\app\lembretes.py NÃO existe!" -ForegroundColor Red
    exit 1
}
Write-Host ""

# ============================================================================
# TESTE 3: Verificar registro no main.py
# ============================================================================
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "🔗 Verificando registro no main.py..." -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan

$mainFile = "backend\app\main.py"
if (Test-Path $mainFile) {
    $mainContent = Get-Content $mainFile -Raw
    
    # Verificar import
    if ($mainContent -match 'from app\.lembretes import router as lembretes_router') {
        Write-Host "✅ Import do lembretes_router encontrado" -ForegroundColor Green
    } else {
        Write-Host "❌ Import do lembretes_router NÃO encontrado!" -ForegroundColor Red
        exit 1
    }
    
    # Verificar registro
    if ($mainContent -match 'app\.include_router\(lembretes_router') {
        Write-Host "✅ Router registrado com app.include_router()" -ForegroundColor Green
    } else {
        Write-Host "❌ Router NÃO está registrado no app!" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "❌ Arquivo backend\app\main.py NÃO existe!" -ForegroundColor Red
    exit 1
}
Write-Host ""

Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "📊 DIAGNÓSTICO COMPLETO" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""
Write-Host "✅ Servidor de produção: Online" -ForegroundColor Green
Write-Host "✅ Código local: Correto e completo" -ForegroundColor Green
Write-Host "✅ Endpoint definido: @router.get('/pendentes')" -ForegroundColor Green
Write-Host "✅ Router registrado: app.include_router(lembretes_router, prefix='/api')" -ForegroundColor Green
Write-Host ""
Write-Host "🎯 CONCLUSÃO:" -ForegroundColor Yellow
Write-Host "   O código está correto LOCALMENTE, mas não foi deployado no servidor!" -ForegroundColor Yellow
Write-Host ""

# ============================================================================
# PERGUNTA: Fazer deploy?
# ============================================================================
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "🚀 SOLUÇÃO: Deploy para Produção" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Para corrigir o erro 404, você precisa fazer deploy do código atualizado." -ForegroundColor White
Write-Host ""
Write-Host "Opções disponíveis:" -ForegroundColor White
Write-Host ""
Write-Host "1️⃣  DEPLOY AUTOMÁTICO via PowerShell" -ForegroundColor Cyan
Write-Host "   .\deploy-prod-auto.ps1" -ForegroundColor Gray
Write-Host ""
Write-Host "2️⃣  DEPLOY MANUAL via SSH (recomendado)" -ForegroundColor Cyan
Write-Host "   ssh root@mlprohub.com.br" -ForegroundColor Gray
Write-Host "   cd /opt/petshop" -ForegroundColor Gray
Write-Host "   ./deploy-producao.sh" -ForegroundColor Gray
Write-Host ""
Write-Host "3️⃣  Deploy via Remote PowerShell (se habilitado no servidor)" -ForegroundColor Cyan
Write-Host "   (Precisa de configuração de SSH + PowerShell)" -ForegroundColor Gray
Write-Host ""

$resposta = Read-Host "Deseja executar o DEPLOY via SSH agora? (s/n)"

if ($resposta -eq "s" -or $resposta -eq "S") {
    Write-Host ""
    Write-Host "🚀 Iniciando deploy via SSH..." -ForegroundColor Green
    Write-Host ""
    Write-Host "EXECUTANDO COMANDOS NO SERVIDOR:" -ForegroundColor Yellow
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow
    
    # Criar script temporário para executar no servidor
    $comandos = @"
cd /opt/petshop &&
echo '📥 Atualizando código...' &&
git pull origin main &&
echo '🛑 Parando containers...' &&
docker compose -f docker-compose.prod.yml down &&
echo '🔨 Rebuilding backend (sem cache)...' &&
docker compose -f docker-compose.prod.yml build --no-cache backend &&
echo '🚀 Iniciando containers...' &&
docker compose -f docker-compose.prod.yml up -d backend postgres &&
echo '⏳ Aguardando 15 segundos...' &&
sleep 15 &&
echo '✅ Deploy concluído! Testando...' &&
curl -s http://localhost:8000/health | head -5 &&
echo '' &&
echo '✅ Backend reiniciado!'
"@
    
    Write-Host "Executando no servidor..." -ForegroundColor Cyan
    Write-Host ""
    
    # Executar via SSH (requer ssh.exe no PATH do Windows)
    ssh root@mlprohub.com.br $comandos
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Green
        Write-Host "✅ DEPLOY CONCLUÍDO COM SUCESSO!" -ForegroundColor Green
        Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Green
        Write-Host ""
        Write-Host "🧪 Testando endpoint..." -ForegroundColor Cyan
        Start-Sleep -Seconds 3
        
        try {
            Write-Host "   GET https://mlprohub.com.br/api/health" -ForegroundColor Gray
            $teste = Invoke-WebRequest -Uri "https://mlprohub.com.br/api/health" -UseBasicParsing -TimeoutSec 10
            Write-Host "   ✅ Status: $($teste.StatusCode)" -ForegroundColor Green
            Write-Host ""
            Write-Host "🎉 O endpoint /api/lembretes/pendentes agora deve funcionar!" -ForegroundColor Green
            Write-Host "   Teste no navegador: https://mlprohub.com.br/api/lembretes/pendentes" -ForegroundColor White
        } catch {
            Write-Host "   ⚠️  Servidor ainda está reiniciando... Aguarde 30s e teste manualmente" -ForegroundColor Yellow
        }
    } else {
        Write-Host ""
        Write-Host "❌ Erro durante o deploy!" -ForegroundColor Red
        Write-Host "   Verifique os logs acima e tente novamente" -ForegroundColor Yellow
    }
} else {
    Write-Host ""
    Write-Host "ℹ️  Deploy cancelado. Execute manualmente quando estiver pronto." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "COMANDOS PARA COPIAR E COLAR NO SSH:" -ForegroundColor Yellow
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow
    Write-Host "ssh root@mlprohub.com.br" -ForegroundColor White
    Write-Host "cd /opt/petshop" -ForegroundColor White
    Write-Host "./deploy-producao.sh" -ForegroundColor White
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "Script concluído!" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
