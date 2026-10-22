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

function Invoke-BackendDependencyAudit {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Python,

        [Parameter(Mandatory = $true)]
        [string]$WorkingDirectory
    )

    Write-Section 'Backend dependency audit'
    $commonArguments = @(
        '-m', 'pip_audit', '-r', 'requirements.lock',
        '--progress-spinner', 'off', '--timeout', '60', '--no-deps', '--disable-pip'
    )

    Push-Location $WorkingDirectory
    try {
        $previousErrorActionPreference = $ErrorActionPreference
        try {
            $ErrorActionPreference = 'Continue'
            $osvOutput = & $Python @commonArguments -s osv 2>&1
            $osvExitCode = $LASTEXITCODE
        } finally {
            $ErrorActionPreference = $previousErrorActionPreference
        }
        $osvOutput | ForEach-Object { Write-Host $_ }

        if ($osvExitCode -eq 0) {
            return
        }

        $osvText = $osvOutput -join "`n"
        $serviceFailurePattern = 'ServiceError|ConnectionError|ConnectTimeout|ReadTimeout|(?:429|5\d\d) Server Error'
        if ($osvText -notmatch $serviceFailurePattern) {
            Fail 'Gate falhou em: Backend dependency audit'
        }

        Write-Warning 'Servico OSV indisponivel. Repetindo a auditoria pela fonte PyPI.'
        & $Python @commonArguments -s pypi
        if ($LASTEXITCODE -ne 0) {
            Fail 'Gate falhou em: Backend dependency audit (fallback PyPI)'
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

Invoke-GateStep 'Faturamento and cash audit reconciliation regression' $python @(
    '-m', 'pytest',
    'tests/unit/test_faturamento_composicao.py',
    'tests/unit/test_faturamento_superficies.py',
    'tests/unit/test_pdf_caixa_resumo.py',
    'tests/unit/test_caixa_recebimentos_auditoria.py',
    'tests/unit/test_caixa_conferencia_estados.py',
    'tests/unit/test_caixa_auditoria_performance.py',
    'tests/unit/test_pagamento_excedente_finalizacao.py',
    'tests/unit/test_venda_edicao_pagamentos.py',
    'tests/unit/test_contas_receber_saldo_venda.py',
    'tests/unit/test_venda_finalizacao_pagamentos.py',
    'tests/unit/test_venda_status_pagamento.py',
    'tests/unit/test_finalizacao_recebiveis_atomicidade.py',
    'tests/unit/test_vendas_fechamento_edicao.py',
    'tests/unit/test_vendas_comissao_reprocessamento_contract.py', '-q'
) $backend

Invoke-GateStep 'Billing operational continuity regression' $python @(
    '-m', 'pytest',
    'tests/unit/test_plan_catalog_and_limits.py',
    'tests/unit/test_modulos_liberacao_temporaria_contract.py',
    'tests/unit/test_module_access_dependency.py',
    'tests/unit/test_custom_billing_offers.py',
    'tests/unit/test_asaas_billing.py',
    'tests/unit/test_ops_tenants_routes_contract.py', '-q'
) $backend
Invoke-GateStep 'Billing notices regression' $node @(
    'src/utils/billingNotice.test.mjs'
) $frontend
Invoke-GateStep 'Tenant suspension authorization regression' $node @(
    'src/pages/opsTenantsUtils.test.mjs'
) $frontend

Invoke-GateStep 'Frontend dependency audit' $npm @(
    'run', 'audit:dependencies'
) $frontend
Invoke-GateStep 'Frontend lint' $npm @('run', 'lint:core') $frontend
Invoke-GateStep 'Frontend format' $npm @('run', 'format:core:check') $frontend
Invoke-GateStep 'Frontend production build' $npm @('run', 'build') $frontend
Invoke-GateStep 'Frontend iFood and product regression tests' $npm @('run', 'test:ifood') $frontend
Invoke-GateStep 'Backend iFood safety contracts' $python @(
    '-m', 'pytest', 'tests/unit/test_ifood_management.py',
    'tests/unit/test_ifood_catalog_contract.py', 'tests/unit/test_ifood_routes_contract.py',
    'tests/unit/test_ifood_orders_contract.py', 'tests/unit/test_ifood_client_contract.py', '-q'
) $backend

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
Invoke-BackendDependencyAudit $auditPython $backend

Invoke-GateStep 'Mobile dependency audit' $npm @(
    'run', 'audit:dependencies'
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
