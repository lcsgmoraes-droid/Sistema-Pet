#!/usr/bin/env pwsh
# Script de Deploy Automatizado para Produção - mlprohub.com.br
# Executa: .\deploy-prod-auto.ps1

param(
    [switch]$SkipMigrations,
    [switch]$SkipRestart
)

$ErrorActionPreference = "Stop"
$SERVER = "root@mlprohub.com.br"
$SERVER_PATH = "/opt/petshop"

Write-Host "`n[DEPLOY] DEPLOY AUTOMATIZADO PARA PRODUCAO" -ForegroundColor Cyan
Write-Host ("="*60) -ForegroundColor Cyan
Write-Host "Servidor: mlprohub.com.br" -ForegroundColor Yellow
Write-Host "Path: $SERVER_PATH`n" -ForegroundColor Yellow

# Função para executar comando SSH
function Invoke-SSHCommand {
    param([string]$Command)
    ssh $SERVER "cd $SERVER_PATH && $Command"
}

# Função para copiar arquivo
function Copy-ToServer {
    param([string]$LocalPath, [string]$RemotePath)
    Write-Host "[UPLOAD] Enviando: $LocalPath" -ForegroundColor Blue
    scp $LocalPath "${SERVER}:${RemotePath}"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Enviado com sucesso`n" -ForegroundColor Green
    } else {
        Write-Host "[ERRO] Erro ao enviar arquivo`n" -ForegroundColor Red
        exit 1
    }
}

try {
    # 1. Verificar conexão com servidor
    Write-Host "[CHECK] Verificando conexao com servidor..." -ForegroundColor Cyan
    ssh -o ConnectTimeout=5 $SERVER "echo 'Conexão OK'" | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERRO] Nao foi possivel conectar ao servidor" -ForegroundColor Red
        exit 1
    }
    Write-Host "[OK] Servidor acessivel`n" -ForegroundColor Green

    # 2. Enviar migrations
    if (-not $SkipMigrations) {
        Write-Host "[DEPLOY] Enviando migrations..." -ForegroundColor Cyan
        
        $migrations = @(
            "backend\alembic\versions\20260215_add_data_fechamento_comissao_to_users.py",
            "backend\alembic\versions\20260215_add_missing_permissions.py"
        )
        
        foreach ($migration in $migrations) {
            if (Test-Path $migration) {
                Copy-ToServer $migration "$SERVER_PATH/backend/alembic/versions/"
            }
        }
    }

    # 3. Enviar script de permissoes
    Write-Host "[DEPLOY] Enviando script de permissoes..." -ForegroundColor Cyan
    if (Test-Path "backend\dar_full_permissoes.py") {
        Copy-ToServer "backend\dar_full_permissoes.py" "$SERVER_PATH/backend/"
    }

    # 4. Aplicar migrations
    if (-not $SkipMigrations) {
        Write-Host "[MIGRATE] Aplicando migrations no banco..." -ForegroundColor Cyan
        Invoke-SSHCommand "docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head"
        Write-Host "[OK] Migrations aplicadas`n" -ForegroundColor Green
    }

    # 5. Atualizar permissoes do usuario
    Write-Host "[USER] Atualizando permissoes do usuario teste@teste.com..." -ForegroundColor Cyan
    Invoke-SSHCommand "docker cp $SERVER_PATH/backend/dar_full_permissoes.py petshop-prod-backend:/app/"
    Invoke-SSHCommand "docker compose -f docker-compose.prod.yml exec -T backend python dar_full_permissoes.py"
    Write-Host "[OK] Permissoes atualizadas`n" -ForegroundColor Green

    # 6. Reiniciar backend (se necessario)
    if (-not $SkipRestart) {
        Write-Host "[RESTART] Reiniciando backend..." -ForegroundColor Cyan
        Invoke-SSHCommand "docker compose -f docker-compose.prod.yml restart backend"
        Write-Host "[OK] Backend reiniciado`n" -ForegroundColor Green
        
        Start-Sleep -Seconds 5
    }

    # 7. Verificar status dos containers
    Write-Host "[STATUS] Status dos containers:" -ForegroundColor Cyan
    Invoke-SSHCommand "docker compose -f docker-compose.prod.yml ps"

    # 8. Verificar logs do backend
    Write-Host "`n[LOGS] Ultimas 10 linhas do log do backend:" -ForegroundColor Cyan
    Invoke-SSHCommand "docker compose -f docker-compose.prod.yml logs --tail=10 backend"

    Write-Host "`n" + ("="*60) -ForegroundColor Green
    Write-Host "[SUCCESS] DEPLOY CONCLUIDO COM SUCESSO!" -ForegroundColor Green
    Write-Host ("="*60) -ForegroundColor Green
    Write-Host "`n[WEB] Acesse: http://mlprohub.com.br" -ForegroundColor Cyan
    Write-Host "[LOGIN] Usuario: teste@teste.com" -ForegroundColor Yellow
    Write-Host "[LOGIN] Senha: test123" -ForegroundColor Yellow
    Write-Host ""

} catch {
    Write-Host "`n[ERRO] ERRO NO DEPLOY!" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
