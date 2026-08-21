param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('corrigir-permissoes-admin', 'resetar-sequences')]
    [string]$Operacao,
    [switch]$Confirmar
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$container = 'petshop-dev-postgres'
$database = 'petshop_dev'
$sqlByOperation = @{
    'corrigir-permissoes-admin' = 'backend\scripts\fix_admin_permissions.sql'
    'resetar-sequences' = 'backend\scripts\reset_sequences.sql'
}

if (-not $Confirmar) {
    $answer = Read-Host "Operacao '$Operacao' altera somente o banco DEV. Digite DEV para continuar"
    if ($answer -cne 'DEV') {
        throw 'Operacao cancelada.'
    }
}

$running = & docker inspect --format '{{.State.Running}}' $container 2>$null
if ($LASTEXITCODE -ne 0 -or $running.Trim() -ne 'true') {
    throw "Container DEV nao esta ativo: $container"
}

$sqlPath = Join-Path $root $sqlByOperation[$Operacao]
if (-not (Test-Path -LiteralPath $sqlPath)) {
    throw "Arquivo SQL oficial nao encontrado: $sqlPath"
}

Write-Host "Executando '$Operacao' em $container/$database..." -ForegroundColor Cyan
Get-Content -LiteralPath $sqlPath -Raw |
    & docker exec -i $container psql -v ON_ERROR_STOP=1 -U postgres -d $database
if ($LASTEXITCODE -ne 0) {
    throw "A manutencao DEV falhou: $Operacao"
}

Write-Host 'Manutencao DEV concluida.' -ForegroundColor Green
