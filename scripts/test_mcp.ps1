param(
    [switch]$InstallDevDependencies
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

$servers = @(
    (Join-Path $root 'mcp\frontend_react_server')
    (Join-Path $root 'mcp\ops_api_server')
)

foreach ($server in $servers) {
    Write-Host "`n=== Testando MCP: $server ===" -ForegroundColor Cyan
    $python = Join-Path $server '.venv\Scripts\python.exe'

    if (-not (Test-Path $python)) {
        throw "Python do venv nao encontrado: $python. Rode scripts\setup_mcp_local.ps1 primeiro."
    }

    Push-Location $server
    try {
        if ($InstallDevDependencies) {
            & $python -m pip install -e "$server[dev]"
        }

        & $python -m pytest tests
        if ($LASTEXITCODE -ne 0) {
            throw "Testes falharam em $server"
        }
    }
    finally {
        Pop-Location
    }
}

Write-Host "`nOK: testes dos MCPs passaram." -ForegroundColor Green
