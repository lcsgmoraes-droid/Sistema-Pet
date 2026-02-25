param(
    [ValidateSet('check', 'release-check', 'dev-up', 'prod-up', 'status')]
    [string]$Acao = 'status'
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $root

$validatorScript = Join-Path $PSScriptRoot 'validar_fluxo.ps1'
$prodScript = Join-Path $PSScriptRoot 'gerenciar_producao.ps1'
$devScript = Join-Path $root 'INICIAR_DEV.bat'

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
        & $devScript
    }

    'prod-up' {
        Run-Validator -allowLocalChanges $false
        & $prodScript up
    }

    'status' {
        & $prodScript status
    }
}
