param(
    [switch]$SemFrontend
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path $PSScriptRoot).Path
Set-Location $root

$composeFile = 'docker-compose.local-dev.yml'
$backendHealthUrl = 'http://localhost:8000/health'

Write-Host '=== Sistema Pet - subir stack DEV ===' -ForegroundColor Cyan
Write-Host "Raiz: $root"
Write-Host ''

docker info *> $null
if ($LASTEXITCODE -ne 0) {
    throw 'Docker Desktop nao esta rodando. Abra o Docker Desktop e tente de novo.'
}

Write-Host "Subindo Postgres + backend ($composeFile)..." -ForegroundColor Yellow
docker compose -f $composeFile up -d
if ($LASTEXITCODE -ne 0) {
    throw 'Falha ao subir os containers do docker compose.'
}

Write-Host 'Aguardando o backend responder em /health...' -ForegroundColor Yellow
$maxTentativas = 30
$ok = $false
for ($i = 0; $i -lt $maxTentativas; $i++) {
    try {
        $resposta = Invoke-WebRequest -Uri $backendHealthUrl -UseBasicParsing -TimeoutSec 3
        if ($resposta.StatusCode -eq 200) {
            $ok = $true
            break
        }
    }
    catch {
        # backend ainda subindo, tenta de novo
    }
    Start-Sleep -Seconds 2
}

if (-not $ok) {
    throw "Backend nao respondeu em $backendHealthUrl apos $($maxTentativas * 2)s. Confira 'docker compose -f $composeFile logs backend'."
}

Write-Host 'Backend saudavel.' -ForegroundColor Green
Write-Host ''
docker compose -f $composeFile ps

if ($SemFrontend) {
    Write-Host ''
    Write-Host 'OK: Postgres + backend no ar. Frontend nao foi iniciado (-SemFrontend).' -ForegroundColor Green
    exit 0
}

Write-Host ''
Write-Host 'Iniciando o frontend (Ctrl+C encerra so o frontend; os containers continuam rodando)...' -ForegroundColor Yellow
& (Join-Path $root 'scripts/iniciar_frontend_dev.ps1')
