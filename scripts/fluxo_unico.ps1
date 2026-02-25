param(
    [ValidateSet('check', 'release-check', 'dev-up', 'prod-up', 'status')]
    [string]$Acao = 'status'
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $root

$validatorScript = Join-Path $PSScriptRoot 'validar_fluxo.ps1'
$devComposeFile = Join-Path $root 'docker-compose.local-dev.yml'
$prodComposeFile = Join-Path $root 'docker-compose.prod.yml'

function Run-Validator([bool]$allowLocalChanges) {
    if ($allowLocalChanges) {
        & $validatorScript -PermitirAlteracoesLocais
    } else {
        & $validatorScript
    }

    if ($LASTEXITCODE -ne 0) {
        throw 'Validacao do fluxo falhou.'
    }
}

function Run-ComposeUp([string]$composeFile) {
    if (-not (Test-Path $composeFile)) {
        throw "Arquivo docker compose nao encontrado: $composeFile"
    }

    docker compose -f $composeFile up -d
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao subir containers com compose: $composeFile"
    }
}

function Run-ComposeStatus([string]$composeFile) {
    if (-not (Test-Path $composeFile)) {
        throw "Arquivo docker compose nao encontrado: $composeFile"
    }

    docker compose -f $composeFile ps
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao consultar status do compose: $composeFile"
    }
}

Write-Host "`n=== Fluxo Unico DEV -> PROD ($Acao) ===" -ForegroundColor Cyan

switch ($Acao) {
    'check' {
        Run-Validator -allowLocalChanges $true
    }

    'release-check' {
        Run-Validator -allowLocalChanges $false
        Write-Host 'Release-check passou. Pode seguir para producao.' -ForegroundColor Green
    }

    'dev-up' {
        Run-Validator -allowLocalChanges $true
        Run-ComposeUp -composeFile $devComposeFile
    }

    'prod-up' {
        Run-Validator -allowLocalChanges $false
        Run-ComposeUp -composeFile $prodComposeFile
    }

    'status' {
        Run-ComposeStatus -composeFile $prodComposeFile
    }
}
