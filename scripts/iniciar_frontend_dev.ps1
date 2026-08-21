param()

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$frontendDir = Join-Path $root 'frontend'
$packageJson = Join-Path $frontendDir 'package.json'
$nodeModules = Join-Path $frontendDir 'node_modules'

if (-not (Test-Path -LiteralPath $packageJson)) {
    throw "Frontend nao encontrado: $packageJson"
}

if (-not (Test-Path -LiteralPath $nodeModules)) {
    Write-Host 'Dependencias do frontend ausentes. Executando npm ci...' -ForegroundColor Yellow
    & npm.cmd ci --prefix $frontendDir
    if ($LASTEXITCODE -ne 0) {
        throw 'Falha ao instalar as dependencias do frontend.'
    }
}

Write-Host 'Frontend DEV: http://localhost:5173' -ForegroundColor Green
Push-Location $frontendDir
try {
    & npm.cmd run dev
    if ($LASTEXITCODE -ne 0) {
        throw 'O frontend DEV terminou com erro.'
    }
}
finally {
    Pop-Location
}
