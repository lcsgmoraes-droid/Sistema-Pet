# 🔧 Script PowerShell - Diagnóstico e Correção Erro 404 Frontend
# Uso: .\DIAGNOSTICAR_404.ps1

Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "🔍 DIAGNÓSTICO RÁPIDO - Erro 404 /notas-fiscais" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Verificar se estamos na pasta correta
if (-not (Test-Path "docker-compose.prod.yml")) {
    Write-Host "❌ Erro: docker-compose.prod.yml não encontrado" -ForegroundColor Red
    Write-Host "Execute este script na pasta raiz do projeto" -ForegroundColor Yellow
    exit 1
}

$problemasEncontrados = @()

# ============================================================================
# VERIFICAÇÃO 1: Arquivos locais
# ============================================================================
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "📁 Verificando arquivos locais..." -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan

if (Test-Path "frontend\dist") {
    Write-Host "✅ Pasta frontend\dist existe" -ForegroundColor Green
    
    if (Test-Path "frontend\dist\index.html") {
        $fileSize = (Get-Item "frontend\dist\index.html").Length
        Write-Host "✅ index.html existe (${fileSize} bytes)" -ForegroundColor Green
        
        if ($fileSize -lt 1000) {
            Write-Host "❌ Arquivo muito pequeno - provavelmente inválido" -ForegroundColor Red
            $problemasEncontrados += "index.html muito pequeno"
        }
    } else {
        Write-Host "❌ index.html NÃO existe" -ForegroundColor Red
        $problemasEncontrados += "index.html ausente"
    }
    
    $fileCount = (Get-ChildItem "frontend\dist" -Recurse -File).Count
    Write-Host "   Total de arquivos: $fileCount" -ForegroundColor Gray
    
    if ($fileCount -lt 5) {
        Write-Host "❌ Build incompleto (poucos arquivos)" -ForegroundColor Red
        $problemasEncontrados += "Build incompleto"
    }
} else {
    Write-Host "❌ Pasta frontend\dist NÃO existe" -ForegroundColor Red
    $problemasEncontrados += "Pasta dist ausente"
}

Write-Host ""

# ============================================================================
# VERIFICAÇÃO 2: .env.production
# ============================================================================
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "⚙️  Verificando .env.production..." -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan

if (Test-Path "frontend\.env.production") {
    $envContent = Get-Content "frontend\.env.production" -Raw
    if ($envContent -match "VITE_API_URL=/api") {
        Write-Host "✅ VITE_API_URL configurado corretamente (/api)" -ForegroundColor Green
    } else {
        Write-Host "❌ VITE_API_URL incorreto ou ausente" -ForegroundColor Red
        Write-Host "   Conteúdo: $envContent" -ForegroundColor Yellow
        $problemasEncontrados += "VITE_API_URL incorreto"
    }
} else {
    Write-Host "❌ Arquivo .env.production NÃO existe" -ForegroundColor Red
    $problemasEncontrados += ".env.production ausente"
}

Write-Host ""

# ============================================================================
# VERIFICAÇÃO 3: Teste remoto no servidor
# ============================================================================
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "🌐 Testando servidor de produção..." -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan

Write-Host "   Executando diagnóstico remoto..." -ForegroundColor Gray

$diagnosticoRemoto = @"
cd ~/Sistema\ Pet 2>/dev/null || cd /root/Sistema\ Pet 2>/dev/null || { echo 'ERRO: Pasta não encontrada'; exit 1; }
echo '--- CONTAINERS ---'
docker ps | grep -E 'frontend|nginx' || echo 'Nenhum container rodando'
echo ''
echo '--- DIST LOCAL ---'
ls -lh frontend/dist/ 2>/dev/null | head -5 || echo 'Pasta dist não existe'
echo ''
echo '--- NGINX CONTAINER ---'
docker exec petshop-prod-nginx ls -lh /usr/share/nginx/html/ 2>/dev/null | head -5 || echo 'Container nginx não está rodando'
echo ''
echo '--- TESTE INTERNO ---'
docker exec petshop-prod-nginx wget -q -O - http://localhost/notas-fiscais 2>&1 | head -1 || echo 'Falha ao testar'
echo ''
echo '--- LOGS NGINX ---'
docker logs petshop-prod-nginx --tail 5 2>&1 | grep -v health || echo 'Sem logs'
"@

try {
    $resultadoRemoto = ssh root@mlprohub.com.br $diagnosticoRemoto 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Conseguiu conectar ao servidor" -ForegroundColor Green
        Write-Host ""
        Write-Host "Resultado do diagnóstico remoto:" -ForegroundColor Yellow
        Write-Host $resultadoRemoto -ForegroundColor Gray
        
        # Analisar resultado
        if ($resultadoRemoto -match "Container nginx não está rodando" -or $resultadoRemoto -match "Nenhum container rodando") {
            $problemasEncontrados += "Container nginx não está rodando"
        }
        
        if ($resultadoRemoto -match "Pasta dist não existe") {
            $problemasEncontrados += "Dist não existe no servidor"
        }
    } else {
        Write-Host "❌ Não conseguiu conectar ao servidor via SSH" -ForegroundColor Red
        $problemasEncontrados += "Sem acesso SSH"
    }
} catch {
    Write-Host "❌ Erro ao executar diagnóstico remoto: $_" -ForegroundColor Red
    $problemasEncontrados += "Erro SSH: $_"
}

Write-Host ""

# ============================================================================
# RESULTADO E RECOMENDAÇÃO
# ============================================================================
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "🎯 RESULTADO DO DIAGNÓSTICO" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

if ($problemasEncontrados.Count -gt 0) {
    Write-Host "❌ PROBLEMAS ENCONTRADOS ($($problemasEncontrados.Count)):" -ForegroundColor Red
    foreach ($problema in $problemasEncontrados) {
        Write-Host "   • $problema" -ForegroundColor Yellow
    }
    Write-Host ""
    
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host "💡 SOLUÇÕES RECOMENDADAS" -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host ""
    
    Write-Host "Escolha uma opção:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "[1] Rebuild COMPLETO local + Deploy automático (RECOMENDADO)" -ForegroundColor Green
    Write-Host "[2] Rebuild APENAS frontend" -ForegroundColor Cyan
    Write-Host "[3] Deploy sem rebuild (usar dist atual)" -ForegroundColor Cyan
    Write-Host "[4] Apenas corrigir .env.production e fazer build" -ForegroundColor Cyan
    Write-Host "[5] Cancelar (corrigir manualmente)" -ForegroundColor Gray
    Write-Host ""
    
    $opcao = Read-Host "Digite o número da opção"
    
    switch ($opcao) {
        "1" {
            Write-Host ""
            Write-Host "🔧 Executando rebuild completo..." -ForegroundColor Cyan
            Write-Host ""
            
            # Corrigir .env.production
            Write-Host "1️⃣ Corrigindo .env.production..." -ForegroundColor Yellow
            "VITE_API_URL=/api" | Out-File -FilePath "frontend\.env.production" -Encoding utf8 -Force
            Write-Host "✅ .env.production atualizado" -ForegroundColor Green
            
            # Build do frontend
            Write-Host ""
            Write-Host "2️⃣ Fazendo build do frontend..." -ForegroundColor Yellow
            Push-Location frontend
            npm run build
            if ($LASTEXITCODE -ne 0) {
                Write-Host "❌ Erro no build do frontend!" -ForegroundColor Red
                Pop-Location
                exit 1
            }
            Pop-Location
            Write-Host "✅ Build concluído" -ForegroundColor Green
            
            # Deploy
            Write-Host ""
            Write-Host "3️⃣ Iniciando deploy para produção..." -ForegroundColor Yellow
            Write-Host "   (Isso pode levar alguns minutos)" -ForegroundColor Gray
            .\deploy-prod-auto.ps1
            
            Write-Host ""
            Write-Host "✅ DEPLOY CONCLUÍDO!" -ForegroundColor Green
            Write-Host ""
            Write-Host "Teste agora: https://mlprohub.com.br/notas-fiscais" -ForegroundColor Cyan
        }
        
        "2" {
            Write-Host ""
            Write-Host "🔧 Rebuild apenas frontend..." -ForegroundColor Cyan
            
            Write-Host "1️⃣ Corrigindo .env.production..." -ForegroundColor Yellow
            "VITE_API_URL=/api" | Out-File -FilePath "frontend\.env.production" -Encoding utf8 -Force
            Write-Host "✅ .env.production atualizado" -ForegroundColor Green
            
            Write-Host ""
            Write-Host "2️⃣ Build do frontend..." -ForegroundColor Yellow
            Push-Location frontend
            npm run build
            Pop-Location
            Write-Host "✅ Build concluído" -ForegroundColor Green
            
            Write-Host ""
            Write-Host "3️⃣ Para fazer deploy, execute:" -ForegroundColor Yellow
            Write-Host "   .\deploy-prod-auto.ps1" -ForegroundColor Cyan
        }
        
        "3" {
            Write-Host ""
            Write-Host "🚀 Fazendo deploy (sem rebuild)..." -ForegroundColor Cyan
            .\deploy-prod-auto.ps1
        }
        
        "4" {
            Write-Host ""
            Write-Host "⚙️  Corrigindo .env e fazendo build..." -ForegroundColor Cyan
            "VITE_API_URL=/api" | Out-File -FilePath "frontend\.env.production" -Encoding utf8 -Force
            Write-Host "✅ .env.production atualizado" -ForegroundColor Green
            
            Write-Host ""
            Write-Host "Fazendo build..." -ForegroundColor Yellow
            Push-Location frontend
            npm run build
            Pop-Location
            Write-Host "✅ Build concluído" -ForegroundColor Green
            Write-Host ""
            Write-Host "Agora execute: .\deploy-prod-auto.ps1" -ForegroundColor Cyan
        }
        
        "5" {
            Write-Host ""
            Write-Host "Correção cancelada pelo usuário" -ForegroundColor Yellow
            Write-Host ""
            Write-Host "Para corrigir manualmente:" -ForegroundColor Yellow
            Write-Host "   1. cd frontend" -ForegroundColor Gray
            Write-Host "   2. npm run build" -ForegroundColor Gray
            Write-Host "   3. cd .." -ForegroundColor Gray
            Write-Host "   4. .\deploy-prod-auto.ps1" -ForegroundColor Gray
        }
        
        default {
            Write-Host "Opção inválida" -ForegroundColor Red
        }
    }
} else {
    Write-Host "✅ Nenhum problema crítico detectado!" -ForegroundColor Green
    Write-Host ""
    Write-Host "O erro 404 pode ser causado por:" -ForegroundColor Yellow
    Write-Host "   • Cache do navegador" -ForegroundColor Gray
    Write-Host "   • CDN/Proxy externo" -ForegroundColor Gray
    Write-Host "   • Problema de rede/DNS" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Tente:" -ForegroundColor Yellow
    Write-Host "   1. Ctrl + Shift + R (hard refresh)" -ForegroundColor Cyan
    Write-Host "   2. Abrir em aba anônima" -ForegroundColor Cyan
    Write-Host "   3. Limpar cache do navegador" -ForegroundColor Cyan
    Write-Host "   4. Testar de outro dispositivo" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Ou force um rebuild:" -ForegroundColor Yellow
    Write-Host "   .\deploy-prod-auto.ps1" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
