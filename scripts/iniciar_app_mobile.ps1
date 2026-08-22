param(
    [string]$ApiUrl = ''
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$mobileDir = Join-Path $root 'app-mobile'
$packageJson = Join-Path $mobileDir 'package.json'
$nodeModules = Join-Path $mobileDir 'node_modules'

if (-not (Test-Path -LiteralPath $packageJson)) {
    throw "App mobile nao encontrado: $packageJson"
}

if ($ApiUrl) {
    $parsedUrl = $null
    if (-not [Uri]::TryCreate($ApiUrl, [UriKind]::Absolute, [ref]$parsedUrl)) {
        throw 'ApiUrl deve ser uma URL completa, por exemplo http://192.168.1.20:8000/api.'
    }
    if ($parsedUrl.Scheme -notin @('http', 'https')) {
        throw 'ApiUrl deve usar http ou https.'
    }
    $env:EXPO_PUBLIC_DEV_API_URL = $ApiUrl.TrimEnd('/')
    Write-Host "API do app configurada para $env:EXPO_PUBLIC_DEV_API_URL" -ForegroundColor Green
}
else {
    Write-Host 'API do app: configuracao padrao de desenvolvimento.' -ForegroundColor Yellow
    Write-Host 'Em celular fisico, informe a URL como primeiro argumento do INICIAR_APP.bat.'
}

if (-not (Test-Path -LiteralPath $nodeModules)) {
    Write-Host 'Dependencias do app ausentes. Executando npm ci...' -ForegroundColor Yellow
    & npm.cmd ci --prefix $mobileDir
    if ($LASTEXITCODE -ne 0) {
        throw 'Falha ao instalar as dependencias do app mobile.'
    }
}

Push-Location $mobileDir
try {
    & npm.cmd run start:clear
    if ($LASTEXITCODE -ne 0) {
        throw 'O Expo terminou com erro.'
    }
}
finally {
    Pop-Location
}
