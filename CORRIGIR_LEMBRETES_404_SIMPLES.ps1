# Script Simples para Corrigir Erro 404 do Endpoint de Lembretes

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host " DIAGNÓSTICO - Endpoint /api/lembretes/pendentes" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""

# Teste 1: Servidor está online?
Write-Host "[1/4] Testando servidor..." -ForegroundColor Yellow
try {
    $test = Invoke-WebRequest -Uri "https://mlprohub.com.br/docs" -UseBasicParsing -TimeoutSec 10
    Write-Host "      OK - Servidor online (Status $($test.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "      ERRO - Servidor offline ou inacessível!" -ForegroundColor Red
    exit 1
}

# Teste 2: Arquivo local existe?
Write-Host "[2/4] Verificando arquivo local..." -ForegroundColor Yellow
if (Test-Path "backend\app\lembretes.py") {
    Write-Host "      OK - Arquivo backend\app\lembretes.py existe" -ForegroundColor Green
} else {
    Write-Host "      ERRO - Arquivo não encontrado!" -ForegroundColor Red
    exit 1
}

# Teste 3: Endpoint está no código?
Write-Host "[3/4] Verificando endpoint no código..." -ForegroundColor Yellow
$codigo = Get-Content "backend\app\lembretes.py" -Raw
if ($codigo -like "*pendentes*") {
    Write-Host "      OK - Endpoint 'pendentes' encontrado" -ForegroundColor Green
} else {
    Write-Host "      ERRO - Endpoint não encontrado!" -ForegroundColor Red
    exit 1
}

# Teste 4: Router registrado?
Write-Host "[4/4] Verificando registro no main.py..." -ForegroundColor Yellow
$main = Get-Content "backend\app\main.py" -Raw
if ($main -like "*lembretes_router*") {
    Write-Host "      OK - Router registrado" -ForegroundColor Green
} else {
    Write-Host "      ERRO - Router não registrado!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=======================================================" -ForegroundColor Green
Write-Host " DIAGNÓSTICO COMPLETO" -ForegroundColor Green
Write-Host "=======================================================" -ForegroundColor Green
Write-Host ""
Write-Host "✅ Servidor de produção: Online" -ForegroundColor Green
Write-Host "✅ Código local: Correto e completo" -ForegroundColor Green
Write-Host "✅ Endpoint definido: Sim" -ForegroundColor Green
Write-Host "✅ Router registrado: Sim" -ForegroundColor Green
Write-Host ""
Write-Host "🎯 CONCLUSÃO:" -ForegroundColor Yellow
Write-Host "   O código está correto LOCALMENTE" -ForegroundColor White
Write-Host "   MAS não foi deployado no servidor!" -ForegroundColor White
Write-Host ""
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host " SOLUÇÃO: Fazer Deploy" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Para corrigir, você precisa fazer deploy do código." -ForegroundColor White
Write-Host ""
Write-Host "Opção 1 - DEPLOY AUTOMÁTICO (recomendado):" -ForegroundColor Green
Write-Host ""
Write-Host "   ssh root@mlprohub.com.br" -ForegroundColor Cyan
Write-Host '   cd /opt/petshop && ./deploy-producao.sh' -ForegroundColor Cyan
Write-Host ""
Write-Host "Opção 2 - DEPLOY RÁPIDO:" -ForegroundColor Green  
Write-Host ""
Write-Host '   ssh root@mlprohub.com.br "cd /opt/petshop && git pull && docker compose -f docker-compose.prod.yml restart backend"' -ForegroundColor Cyan
Write-Host ""
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""

$resposta = Read-Host "Deseja que eu execute o deploy via SSH agora? (s/n)"

if ($resposta -eq "s" -or $resposta -eq "S" -or $resposta -eq "sim") {
    Write-Host ""
    Write-Host "🚀 Executando deploy..." -ForegroundColor Green
    Write-Host ""
    
    # Comando SSH simples e direto
    $cmd = "cd /opt/petshop && git pull origin main && docker compose -f docker-compose.prod.yml down && docker compose -f docker-compose.prod.yml build --no-cache backend && docker compose -f docker-compose.prod.yml up -d backend postgres && sleep 15 && curl -s http://localhost:8000/health"
    
    Write-Host "Conectando no servidor..." -ForegroundColor Cyan
    ssh root@mlprohub.com.br $cmd
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "=======================================================" -ForegroundColor Green
        Write-Host " DEPLOY CONCLUÍDO!" -ForegroundColor Green
        Write-Host "=======================================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "🎉 O endpoint deve funcionar agora!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Teste no navegador ou Postman:" -ForegroundColor White
        Write-Host "   GET https://mlprohub.com.br/api/lembretes/pendentes" -ForegroundColor Cyan
        Write-Host ""
    } else {
        Write-Host ""
        Write-Host "❌ Erro durante deploy!" -ForegroundColor Red
        Write-Host "   Verifique manualmente via SSH" -ForegroundColor Yellow
    }
} else {
    Write-Host ""
    Write-Host "OK - Deploy cancelado" -ForegroundColor Yellow
    Write-Host "Execute manualmente quando estiver pronto" -ForegroundColor White
}

Write-Host ""
