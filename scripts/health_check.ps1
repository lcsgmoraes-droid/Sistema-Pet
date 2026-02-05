# ===========================================================================
# Script de Verificação de Saúde do Sistema
# ===========================================================================
# Execute diariamente para monitorar o sistema de produção local
# ===========================================================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Health Check - Sistema Pet Shop Pro" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$hasErrors = $false

# 1. Verificar containers rodando
Write-Host "[1/5] Verificando containers..." -ForegroundColor Yellow
$containers = docker ps --filter "name=petshop-local-prod" --format "{{.Names}}" 2>$null

if ($containers) {
    $containerCount = ($containers | Measure-Object).Count
    Write-Host "  ✓ $containerCount containers rodando" -ForegroundColor Green
    foreach ($container in $containers) {
        $status = docker inspect $container --format "{{.State.Health.Status}}" 2>$null
        if ($status) {
            if ($status -eq "healthy") {
                Write-Host "    ✓ $container - healthy" -ForegroundColor Green
            } else {
                Write-Host "    ⚠ $container - $status" -ForegroundColor Yellow
            }
        } else {
            Write-Host "    • $container - running (no healthcheck)" -ForegroundColor Gray
        }
    }
} else {
    Write-Host "  ✗ Nenhum container rodando!" -ForegroundColor Red
    Write-Host "    Execute: docker-compose -f docker-compose.local-prod.yml up -d" -ForegroundColor Yellow
    $hasErrors = $true
}

Write-Host ""

# 2. Verificar últimos backups
Write-Host "[2/5] Verificando backups..." -ForegroundColor Yellow
$backupDir = Join-Path $PSScriptRoot "..\backups"
$recentBackups = Get-ChildItem -Path $backupDir -Filter "backup_*.dump.gz" -ErrorAction SilentlyContinue | 
    Where-Object { $_.LastWriteTime -gt (Get-Date).AddHours(-24) }

if ($recentBackups) {
    $count = ($recentBackups | Measure-Object).Count
    $latest = $recentBackups | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    Write-Host "  ✓ $count backup(s) nas últimas 24h" -ForegroundColor Green
    Write-Host "    Último: $($latest.Name) ($([math]::Round($latest.Length/1KB, 2)) KB)" -ForegroundColor Green
} else {
    Write-Host "  ⚠ Nenhum backup nas últimas 24h!" -ForegroundColor Yellow
    Write-Host "    Considere executar backup manual" -ForegroundColor Yellow
}

Write-Host ""

# 3. Verificar erros no backend
Write-Host "[3/5] Verificando erros no backend..." -ForegroundColor Yellow
$errorCount = 0
$criticalCount = 0

try {
    $logs = docker logs petshop-local-prod-backend --since 24h 2>&1
    $errorCount = ($logs | Select-String -Pattern "ERROR" -AllMatches).Matches.Count
    $criticalCount = ($logs | Select-String -Pattern "CRITICAL" -AllMatches).Matches.Count
    
    if ($criticalCount -gt 0) {
        Write-Host "  ✗ $criticalCount erros CRÍTICOS encontrados!" -ForegroundColor Red
        $hasErrors = $true
        Write-Host "    Últimos erros críticos:" -ForegroundColor Red
        $logs | Select-String -Pattern "CRITICAL" | Select-Object -Last 3 | ForEach-Object {
            Write-Host "      $_" -ForegroundColor Red
        }
    } elseif ($errorCount -gt 10) {
        Write-Host "  ⚠ $errorCount erros nas últimas 24h" -ForegroundColor Yellow
        Write-Host "    Últimos erros:" -ForegroundColor Yellow
        $logs | Select-String -Pattern "ERROR" | Select-Object -Last 3 | ForEach-Object {
            Write-Host "      $_" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  ✓ Sistema saudável: $errorCount erros nas últimas 24h" -ForegroundColor Green
    }
} catch {
    Write-Host "  ✗ Não foi possível verificar logs do backend" -ForegroundColor Red
}

Write-Host ""

# 4. Verificar espaço em disco
Write-Host "[4/5] Verificando espaço em disco..." -ForegroundColor Yellow
$drive = Get-PSDrive C
$freeSpaceGB = [math]::Round($drive.Free / 1GB, 2)
$totalSpaceGB = [math]::Round(($drive.Used + $drive.Free) / 1GB, 2)
$percentFree = [math]::Round(($drive.Free / ($drive.Used + $drive.Free)) * 100, 1)

if ($percentFree -lt 10) {
    Write-Host "  ✗ Espaço crítico: $freeSpaceGB GB livres de $totalSpaceGB GB ($percentFree%)" -ForegroundColor Red
    $hasErrors = $true
} elseif ($percentFree -lt 20) {
    Write-Host "  ⚠ Espaço baixo: $freeSpaceGB GB livres de $totalSpaceGB GB ($percentFree%)" -ForegroundColor Yellow
} else {
    Write-Host "  ✓ Espaço adequado: $freeSpaceGB GB livres de $totalSpaceGB GB ($percentFree%)" -ForegroundColor Green
}

Write-Host ""

# 5. Testar endpoints
Write-Host "[5/5] Testando endpoints..." -ForegroundColor Yellow
try {
    $healthResponse = Invoke-WebRequest -Uri "http://localhost:8001/health" -TimeoutSec 5 -ErrorAction Stop
    if ($healthResponse.StatusCode -eq 200) {
        Write-Host "  ✓ /health - OK" -ForegroundColor Green
    }
} catch {
    Write-Host "  ✗ /health - Falhou" -ForegroundColor Red
    $hasErrors = $true
}

try {
    $readyResponse = Invoke-WebRequest -Uri "http://localhost:8001/ready" -TimeoutSec 5 -ErrorAction Stop
    if ($readyResponse.StatusCode -eq 200) {
        Write-Host "  ✓ /ready - OK" -ForegroundColor Green
    }
} catch {
    Write-Host "  ✗ /ready - Falhou (banco pode estar desconectado)" -ForegroundColor Red
    $hasErrors = $true
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan

if ($hasErrors) {
    Write-Host "  ⚠ ATENÇÃO: Problemas detectados!" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Cyan
    exit 1
} else {
    Write-Host "  ✓ Sistema operacional!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    exit 0
}
