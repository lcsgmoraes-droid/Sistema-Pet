param(
    [ValidateSet('rapido', 'completo')]
    [string]$Nivel = 'completo'
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

function Write-Section([string]$text) {
    Write-Host "`n=== $text ===" -ForegroundColor Cyan
}

function Fail([string]$message) {
    Write-Host "ERRO: $message" -ForegroundColor Red
    exit 1
}

function Resolve-RequiredCommand([string]$command) {
    $resolved = Get-Command $command -ErrorAction SilentlyContinue
    if (-not $resolved) {
        Fail "Comando obrigatorio nao encontrado: $command"
    }

    return $resolved.Source
}

function Resolve-BackendPython {
    $candidates = @(
        (Join-Path $root 'backend/.venv/Scripts/python.exe'),
        (Join-Path $root 'backend/.venv/bin/python')
    )

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return (Resolve-Path $candidate).Path
        }
    }

    return Resolve-RequiredCommand 'python'
}

function Resolve-PythonWithModule([string]$module) {
    $candidates = @(
        (Resolve-BackendPython),
        (Resolve-RequiredCommand 'python')
    ) | Select-Object -Unique

    foreach ($candidate in $candidates) {
        $previousErrorActionPreference = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        & $candidate -c "import $module" *> $null
        $moduleAvailable = $LASTEXITCODE -eq 0
        $ErrorActionPreference = $previousErrorActionPreference
        if ($moduleAvailable) {
            return $candidate
        }
    }

    Fail "Modulo Python obrigatorio nao encontrado: $module"
}

function Invoke-GateStep {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,

        [Parameter(Mandatory = $true)]
        [string]$Executable,

        [Parameter(Mandatory = $true)]
        [object[]]$Arguments,

        [Parameter(Mandatory = $true)]
        [string]$WorkingDirectory
    )

    Write-Section $Name
    Push-Location $WorkingDirectory
    try {
        & $Executable @Arguments
        if ($LASTEXITCODE -ne 0) {
            Fail "Gate falhou em: $Name"
        }
    } finally {
        Pop-Location
    }
}

$python = Resolve-BackendPython
$auditPython = Resolve-PythonWithModule 'pip_audit'
$ruff = Resolve-RequiredCommand 'ruff'
$npm = Resolve-RequiredCommand 'npm'
$node = Resolve-RequiredCommand 'node'
$backend = Join-Path $root 'backend'
$frontend = Join-Path $root 'frontend'
$mobile = Join-Path $root 'app-mobile'

$env:DEBUG = 'false'
$env:ENVIRONMENT = 'testing'
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:DATABASE_URL = 'sqlite:///./test.db'
$env:JWT_SECRET_KEY = 'local-release-gate-secret-with-more-than-32-characters'
$env:EMAIL_VERIFICATION_REQUIRED = 'false'
$env:BLING_SYNC_SCHEDULER_ENABLED = 'false'
$env:SEFAZ_IMPORTACAO_AUTOMATICA = 'false'

Write-Host "`n=== Gate tecnico de release ($Nivel) ===" -ForegroundColor Cyan
Write-Host "Raiz: $root"
Write-Host "Python: $python"

Invoke-GateStep 'Backend dependency sync' $python @(
    (Join-Path $root 'scripts/check_python_requirements.py'),
    (Join-Path $backend 'requirements.txt')
) $root
Invoke-GateStep 'Backend lint' $ruff @('check', '.') $backend
Invoke-GateStep 'Backend format' $ruff @(
    'format', '--check', '.', '--exclude', 'alembic/versions'
) $backend

Invoke-GateStep 'Frontend dependency audit' $npm @(
    'audit', '--audit-level=moderate'
) $frontend
Invoke-GateStep 'Frontend lint' $npm @('run', 'lint:core') $frontend
Invoke-GateStep 'Frontend format' $npm @('run', 'format:core:check') $frontend
Invoke-GateStep 'Frontend production build' $npm @('run', 'build') $frontend

if ($Nivel -eq 'rapido') {
    Write-Host "`nOK: gate rapido passou." -ForegroundColor Green
    exit 0
}

Invoke-GateStep 'Root smoke tests' $python @('-m', 'pytest', 'tests', '-q') $root
Invoke-GateStep 'Multitenant hardening suite' $python @(
    '-m', 'pytest', 'tests/multi_tenant', '-q', '--cov=app', '--cov-report=term'
) $backend
Invoke-GateStep 'Backend import smoke' $python @(
    '-c', "import app.main; print('main import ok')"
) $backend
Invoke-GateStep 'Backend dependency audit' $auditPython @(
    '-m', 'pip_audit', '-r', 'requirements.lock', '-s', 'osv',
    '--progress-spinner', 'off', '--timeout', '60', '--no-deps', '--disable-pip'
) $backend

Invoke-GateStep 'Mobile dependency audit' $npm @(
    'audit', '--audit-level=moderate'
) $mobile
Invoke-GateStep 'Mobile typecheck' $npm @('run', 'typecheck') $mobile

$mobileTests = @(
    Get-ChildItem -Path (Join-Path $mobile 'tests') -Filter '*.test.mjs' -File |
        Sort-Object FullName |
        ForEach-Object { $_.FullName }
)
if ($mobileTests.Count -eq 0) {
    Fail 'Nenhum teste mobile *.test.mjs foi encontrado.'
}
Invoke-GateStep 'Mobile tests' $node (@('--test') + $mobileTests) $mobile

Write-Host "`nOK: gate completo de release passou." -ForegroundColor Green
exit 0
