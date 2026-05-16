param(
    [switch]$InstallDevDependencies
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

function Find-Python {
    $candidates = @('py', 'python')
    foreach ($candidate in $candidates) {
        $command = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($command) {
            return $command.Source
        }
    }

    throw 'Python nao encontrado no PATH.'
}

function Ensure-Venv([string]$server, [string]$python) {
    if (Test-Path $python) {
        return
    }

    if (-not $InstallDevDependencies) {
        throw "Python do venv nao encontrado: $python. Rode scripts\setup_mcp_local.ps1 ou use -InstallDevDependencies."
    }

    Write-Host "Criando venv em $server..." -ForegroundColor Yellow
    $basePython = Find-Python
    if ((Split-Path -Leaf $basePython) -eq 'py.exe' -or (Split-Path -Leaf $basePython) -eq 'py') {
        & $basePython -3 -m venv (Join-Path $server '.venv')
    } else {
        & $basePython -m venv (Join-Path $server '.venv')
    }

    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $python)) {
        throw "Falha ao criar venv para $server"
    }
}

$servers = @(
    (Join-Path $root 'mcp\frontend_react_server')
    (Join-Path $root 'mcp\ops_api_server')
)

foreach ($server in $servers) {
    Write-Host "`n=== Testando MCP: $server ===" -ForegroundColor Cyan
    $python = Join-Path $server '.venv\Scripts\python.exe'
    Ensure-Venv -server $server -python $python

    Push-Location $server
    try {
        if ($InstallDevDependencies) {
            & $python -m pip install --upgrade pip
            if ($LASTEXITCODE -ne 0) {
                throw "Falha ao atualizar pip em $server"
            }

            & $python -m pip install -e "$server[dev]"
            if ($LASTEXITCODE -ne 0) {
                throw "Falha ao instalar dependencias de teste em $server"
            }
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
