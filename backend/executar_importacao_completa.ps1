[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Argumentos
)

$scriptOficial = Join-Path (Split-Path -Parent $PSScriptRoot) 'scripts\importar_simplesvet_seguro.ps1'
Write-Host 'Este nome e mantido por compatibilidade. Encaminhando ao fluxo seguro.' -ForegroundColor Yellow
& powershell -ExecutionPolicy Bypass -File $scriptOficial @Argumentos
exit $LASTEXITCODE
