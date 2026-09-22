[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('Simular', 'Aplicar')]
    [string]$Modo,

    [string]$TenantId,
    [int]$UserId,
    [string]$TenantFonteId,
    [string]$Pdf,
    [int]$QuantidadeEsperada = 3643,
    [string]$DiretorioRelatorios,

    [string]$Plano,
    [string]$ConfirmarTenantId,
    [string]$ConfirmarPlanId,
    [switch]$PermitirProducao,
    [string]$ConfirmacaoProducao,
    [string]$ReferenciaBackup
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $repoRoot 'backend'
$cliArgs = @('importar_excellent_produtos_cli.py')

if ($Modo -eq 'Simular') {
    if (-not $TenantId -or $UserId -le 0 -or -not $TenantFonteId -or -not $Pdf) {
        throw 'Simular exige -TenantId, -UserId, -TenantFonteId e -Pdf.'
    }
    $cliArgs += @(
        'plan',
        '--tenant-id', $TenantId,
        '--user-id', [string]$UserId,
        '--source-tenant-id', $TenantFonteId,
        '--pdf', $Pdf,
        '--expected-count', [string]$QuantidadeEsperada
    )
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
    if ($ReferenciaBackup) {
        $cliArgs += @('--backup-reference', $ReferenciaBackup)
    }
}

Write-Host 'Executando substituicao segura de produtos Excellent (plan/apply)...' -ForegroundColor Cyan
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
