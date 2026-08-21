param()

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$backendDir = Join-Path $root 'backend'
$testFile = Join-Path $backendDir 'tests\test_plano_basico_e2e.py'
$requiredVariables = @(
    'E2E_BASE_URL',
    'E2E_USER_EMAIL',
    'E2E_USER_PASSWORD',
    'E2E_TENANT_ID'
)

if (-not (Test-Path -LiteralPath $testFile)) {
    throw "Teste E2E oficial nao encontrado: $testFile"
}

$missing = @(
    $requiredVariables | Where-Object {
        [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($_))
    }
)
if ($missing.Count -gt 0) {
    throw 'Variaveis E2E obrigatorias ausentes: ' + ($missing -join ', ')
}

$baseUri = [Uri][Environment]::GetEnvironmentVariable('E2E_BASE_URL')
$productionDomains = @('corepet.com.br', 'mlprohub.com.br')
$hostname = $baseUri.Host.ToLowerInvariant()
$isProduction = @(
    $productionDomains | Where-Object {
        $hostname -eq $_ -or $hostname.EndsWith(".$_")
    }
).Count -gt 0
$allowProduction = [Environment]::GetEnvironmentVariable('E2E_ALLOW_PRODUCTION') -match '^(1|true|yes|sim|on)$'

if ($isProduction -and -not $allowProduction) {
    throw 'E2E contra producao bloqueado. Defina E2E_ALLOW_PRODUCTION=true somente com autorizacao explicita.'
}

Write-Host "E2E Plano Basico: $($baseUri.AbsoluteUri)" -ForegroundColor Cyan
Push-Location $backendDir
try {
    & python -m pytest tests/test_plano_basico_e2e.py -m e2e_long -q
    if ($LASTEXITCODE -ne 0) {
        throw 'O teste E2E falhou.'
    }
}
finally {
    Pop-Location
}

Write-Host 'E2E concluido com sucesso.' -ForegroundColor Green
