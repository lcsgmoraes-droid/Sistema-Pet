param()

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$admDir = Join-Path $root 'adm'
$nodeModules = Join-Path $admDir 'node_modules'

if (-not (Test-Path -LiteralPath (Join-Path $admDir 'package.json'))) {
    throw "Painel adm nao encontrado: $admDir"
}

if (-not (Test-Path -LiteralPath $nodeModules)) {
    Write-Host 'Dependencias do painel adm ausentes. Executando npm ci...' -ForegroundColor Yellow
    & npm.cmd ci --prefix $admDir
    if ($LASTEXITCODE -ne 0) {
        throw 'Falha ao instalar as dependencias do painel adm.'
    }
}

Write-Host 'Painel adm DEV: http://localhost:5176' -ForegroundColor Green
Push-Location $admDir
try {
    & npm.cmd run dev
}
finally {
    Pop-Location
}
