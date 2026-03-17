param(
    [ValidateSet('up', 'down', 'status', 'logs')]
    [string]$Acao = 'status'
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $root

$composeFile = Join-Path $root 'docker-compose.whatsapp-pilot.yml'
$pilotEnvFile = Join-Path $root '.env.whatsapp-pilot'

function Ensure-ComposeFile {
    if (-not (Test-Path $composeFile)) {
        throw "Arquivo docker compose do piloto nao encontrado: $composeFile"
    }
}

function Ensure-EnvFile {
    if (-not (Test-Path $pilotEnvFile)) {
        throw "Arquivo .env.whatsapp-pilot nao encontrado. Copie .env.whatsapp-pilot.example e preencha os valores."
    }
}

function Run-Compose([string[]]$ComposeArgs) {
    docker compose --env-file $pilotEnvFile -f $composeFile @ComposeArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao executar docker compose no piloto WhatsApp."
    }
}

Write-Host "`n=== Piloto WhatsApp WAHA + n8n ($Acao) ===" -ForegroundColor Cyan

Ensure-ComposeFile

switch ($Acao) {
    'up' {
        Ensure-EnvFile
        Run-Compose @('up', '-d')
        Run-Compose @('ps')
        Write-Host 'Piloto iniciado com sucesso.' -ForegroundColor Green
    }

    'down' {
        Ensure-EnvFile
        Run-Compose @('down')
        Write-Host 'Piloto parado.' -ForegroundColor Yellow
    }

    'status' {
        Ensure-EnvFile
        Run-Compose @('ps')
    }

    'logs' {
        Ensure-EnvFile
        Run-Compose @('logs', '--tail', '120')
    }
}
