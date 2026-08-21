[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('Simular', 'Aplicar')]
    [string]$Modo,

    [string]$TenantId,
    [int]$UserId,
    [string]$DiretorioDados,
    [ValidateSet('all', 'base', 'catalog', 'pets', 'sales')]
    [string]$Escopo = 'all',
    [int]$Limite,
    [string]$DiretorioRelatorios,

    [string]$Plano,
    [string]$ConfirmarTenantId,
    [string]$ConfirmarPlanId,
    [switch]$PermitirProducao,
    [string]$ConfirmacaoProducao
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $repoRoot 'backend'
$cliArgs = @('importar_simplesvet_cli.py')

if ($Modo -eq 'Simular') {
    if (-not $TenantId -or $UserId -le 0 -or -not $DiretorioDados) {
        throw 'Simular exige -TenantId, -UserId e -DiretorioDados.'
    }
    $cliArgs += @(
        'plan',
        '--tenant-id', $TenantId,
        '--user-id', [string]$UserId,
        '--source-dir', $DiretorioDados,
        '--scope', $Escopo
    )
    if ($Limite -gt 0) {
        $cliArgs += @('--limit', [string]$Limite)
    }
    if ($DiretorioRelatorios) {
        $cliArgs += @('--report-dir', $DiretorioRelatorios)
    }
}
else {
    if (-not $Plano -or -not $ConfirmarTenantId -or -not $ConfirmarPlanId) {
        throw 'Aplicar exige -Plano, -ConfirmarTenantId e -ConfirmarPlanId.'
    }
    $cliArgs += @(
        'apply',
        '--plan-file', $Plano,
        '--confirm-tenant-id', $ConfirmarTenantId,
        '--confirm-plan-id', $ConfirmarPlanId
    )
    if ($PermitirProducao) {
        $cliArgs += '--allow-production-apply'
    }
    if ($ConfirmacaoProducao) {
        $cliArgs += @('--confirm-production', $ConfirmacaoProducao)
    }
}

Write-Host 'Executando importacao pelo fluxo seguro plan/apply...' -ForegroundColor Cyan
$processExitCode = 1
Push-Location $backendDir
try {
    & python @cliArgs
    $processExitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}

exit $processExitCode
