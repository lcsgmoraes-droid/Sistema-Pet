param(
    [ValidateSet('preparar', 'verificar-config', 'subir', 'status', 'validar', 'parar', 'resetar')]
    [string]$Acao = 'status',

    [switch]$ConfirmarReset
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$composeFile = Join-Path $root 'docker-compose.homolog.yml'
$exampleEnvFile = Join-Path $root 'homolog.env.example'
$localEnvFile = Join-Path $root '.env.homolog.local'
$projectName = 'corepet-homolog'

function New-RandomHex([int]$byteCount) {
    $bytes = New-Object byte[] $byteCount
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    return ([System.BitConverter]::ToString($bytes)).Replace('-', '').ToLowerInvariant()
}

function New-UrlSafeBase64([int]$byteCount) {
    $bytes = New-Object byte[] $byteCount
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    return [Convert]::ToBase64String($bytes).Replace('+', '-').Replace('/', '_')
}

function Initialize-HomologEnv {
    if (Test-Path -LiteralPath $localEnvFile) {
        Write-Host 'Configuracao local de homologacao ja existe e foi preservada.' -ForegroundColor Yellow
        return
    }

    $lines = @(
        '# Gerado localmente. Nao versionar nem compartilhar.',
        "HOMOLOG_POSTGRES_PASSWORD=$(New-RandomHex 24)",
        "HOMOLOG_JWT_SECRET_KEY=$(New-RandomHex 32)",
        "HOMOLOG_PAYMENT_CONFIG_ENCRYPTION_KEY=$(New-UrlSafeBase64 32)",
        'HOMOLOG_USER_EMAIL=homologacao@corepet.test',
        "HOMOLOG_USER_PASSWORD=$(New-RandomHex 16)",
        'HOMOLOG_TENANT_NAME=CorePet Homologacao Local'
    )
    $encoding = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllLines($localEnvFile, $lines, $encoding)
    Write-Host 'Configuracao local criada em .env.homolog.local sem exibir credenciais.' -ForegroundColor Green
}

function Read-HomologEnv {
    if (-not (Test-Path -LiteralPath $localEnvFile)) {
        throw 'Execute primeiro: scripts\homologacao_local.ps1 -Acao preparar'
    }

    $values = @{}
    foreach ($line in Get-Content -LiteralPath $localEnvFile) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith('#')) {
            continue
        }
        $parts = $trimmed.Split('=', 2)
        if ($parts.Count -eq 2) {
            $values[$parts[0]] = $parts[1]
        }
    }
    return $values
}

function Assert-DockerCli {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw 'Docker Desktop nao foi encontrado. Instale-o antes de usar a homologacao local.'
    }
}

function Assert-DockerEngine {
    Assert-DockerCli
    & docker info --format '{{.ServerVersion}}' *> $null
    if ($LASTEXITCODE -ne 0) {
        throw 'Docker Desktop esta fechado. Abra o Docker Desktop e tente novamente.'
    }
}

function Invoke-HomologCompose([string[]]$Arguments, [string]$EnvFile = $localEnvFile) {
    & docker compose --env-file $EnvFile -f $composeFile --project-name $projectName @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose falhou: $($Arguments -join ' ')"
    }
}

function Show-HomologDiagnostics {
    Write-Host 'Diagnostico seguro dos containers de homologacao:' -ForegroundColor Yellow
    & docker compose --env-file $localEnvFile -f $composeFile --project-name $projectName ps
    & docker compose --env-file $localEnvFile -f $composeFile --project-name $projectName `
        logs --no-color --tail 240 migrate backend
}

function Wait-HomologHealth {
    $deadline = (Get-Date).AddMinutes(4)
    do {
        try {
            $frontend = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:18080/health' -TimeoutSec 5
            $backend = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:18080/api/health/watchdog' -TimeoutSec 8
            if ($frontend.StatusCode -eq 200 -and $backend.StatusCode -eq 200) {
                Write-Host 'Frontend e backend de homologacao estao saudaveis.' -ForegroundColor Green
                return
            }
        }
        catch {
            Start-Sleep -Seconds 4
        }
    } while ((Get-Date) -lt $deadline)

    Invoke-HomologCompose @('ps')
    throw 'A homologacao nao ficou saudavel no tempo esperado. Consulte os logs com docker compose.'
}

function Invoke-JsonPost([string]$Uri, [hashtable]$Payload) {
    return Invoke-RestMethod -Method Post -Uri $Uri -ContentType 'application/json' `
        -Body ($Payload | ConvertTo-Json -Depth 5) -TimeoutSec 60
}

function Get-OrCreate-HomologIdentity([hashtable]$Values) {
    $baseUrl = 'http://127.0.0.1:18080/api'
    $loginPayload = @{
        email = $Values['HOMOLOG_USER_EMAIL']
        password = $Values['HOMOLOG_USER_PASSWORD']
    }

    try {
        $response = Invoke-JsonPost "$baseUrl/auth/login-multitenant" $loginPayload
    }
    catch {
        $registerPayload = @{
            email = $Values['HOMOLOG_USER_EMAIL']
            password = $Values['HOMOLOG_USER_PASSWORD']
            nome = 'Operador Homologacao'
            nome_loja = $Values['HOMOLOG_TENANT_NAME']
            plan = 'pet-start'
            organization_type = 'petshop'
            accepted_terms = $true
            accepted_privacy = $true
            terms_version = 'homolog-local'
            privacy_version = 'homolog-local'
        }
        $response = Invoke-JsonPost "$baseUrl/auth/register" $registerPayload
        Write-Host 'Tenant ficticio de homologacao criado.' -ForegroundColor Green
    }

    $tenant = @($response.tenants) | Select-Object -First 1
    if (-not $tenant -or -not $tenant.id) {
        throw 'Nao foi possivel identificar o tenant ficticio da homologacao.'
    }
    return [string]$tenant.id
}

Set-Location $root

switch ($Acao) {
    'preparar' {
        Initialize-HomologEnv
    }
    'verificar-config' {
        Assert-DockerCli
        Invoke-HomologCompose @('config', '--quiet') $exampleEnvFile
        Write-Host 'Configuracao Docker Compose de homologacao: OK.' -ForegroundColor Green
    }
    'subir' {
        Initialize-HomologEnv
        Assert-DockerEngine
        try {
            Invoke-HomologCompose @('up', '-d', '--build', '--remove-orphans')
        }
        catch {
            Show-HomologDiagnostics
            throw
        }
        Wait-HomologHealth
        Write-Host 'Homologacao disponivel somente neste computador: http://127.0.0.1:18080' -ForegroundColor Cyan
    }
    'status' {
        Assert-DockerEngine
        if (-not (Test-Path -LiteralPath $localEnvFile)) {
            throw 'A homologacao ainda nao foi preparada.'
        }
        Invoke-HomologCompose @('ps')
        Wait-HomologHealth
    }
    'validar' {
        Assert-DockerEngine
        $values = Read-HomologEnv
        Wait-HomologHealth
        try {
            $tenantId = Get-OrCreate-HomologIdentity $values

            $env:E2E_BASE_URL = 'http://127.0.0.1:18080/api'
            $env:E2E_USER_EMAIL = $values['HOMOLOG_USER_EMAIL']
            $env:E2E_USER_PASSWORD = $values['HOMOLOG_USER_PASSWORD']
            $env:E2E_TENANT_ID = $tenantId
            $env:E2E_BLOCKED_PATH = '/bling/teste-conexao'
            $env:E2E_ALLOW_PRODUCTION = 'false'

            & (Join-Path $PSScriptRoot 'executar_testes_e2e.ps1')
            if ($LASTEXITCODE -ne 0) {
                throw 'A jornada E2E da homologacao falhou.'
            }
        }
        catch {
            Show-HomologDiagnostics
            throw
        }
        Write-Host 'Homologacao funcional concluida com dados ficticios.' -ForegroundColor Green
    }
    'parar' {
        Assert-DockerEngine
        Invoke-HomologCompose @('down', '--remove-orphans')
        Write-Host 'Homologacao parada. Os volumes locais foram preservados.' -ForegroundColor Green
    }
    'resetar' {
        if (-not $ConfirmarReset) {
            throw 'Reset bloqueado. Repita com -ConfirmarReset para apagar somente os volumes do projeto corepet-homolog.'
        }
        Assert-DockerEngine
        Invoke-HomologCompose @('down', '--volumes', '--remove-orphans')
        Write-Host 'Volumes descartaveis da homologacao foram removidos. Producao nao foi acessada.' -ForegroundColor Green
    }
}
