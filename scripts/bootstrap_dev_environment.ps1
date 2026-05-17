param(
    [switch]$DryRun,
    [switch]$Json,
    [switch]$NoNetwork,
    [switch]$SkipCheck,
    [switch]$SkipBackend,
    [switch]$SkipFrontend,
    [switch]$SkipMcp
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $root

$steps = [System.Collections.Generic.List[object]]::new()
$errors = [System.Collections.Generic.List[string]]::new()

function Add-Step {
    param(
        [string]$Id,
        [string]$Name,
        [ValidateSet('planned', 'ok', 'skipped', 'error')]
        [string]$Status,
        [string]$Message,
        [string]$Command = '',
        [hashtable]$Details = @{}
    )

    $steps.Add([pscustomobject][ordered]@{
        id = $Id
        name = $Name
        status = $Status
        message = $Message
        command = $Command
        details = [pscustomobject]$Details
    }) | Out-Null
}

function Invoke-Native {
    param(
        [string]$Executable,
        [string[]]$Arguments,
        [string]$WorkingDirectory = $root
    )

    Push-Location $WorkingDirectory
    try {
        & $Executable @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "Comando falhou com exit code ${LASTEXITCODE}: $Executable $($Arguments -join ' ')"
        }
    }
    finally {
        Pop-Location
    }
}

function Get-BackendPythonPath {
    $windowsPath = Join-Path $root 'backend/.venv/Scripts/python.exe'
    $unixPath = Join-Path $root 'backend/.venv/bin/python'

    if (Test-Path $windowsPath) {
        return $windowsPath
    }
    if (Test-Path $unixPath) {
        return $unixPath
    }

    if ($IsWindows -or $env:OS -eq 'Windows_NT') {
        return $windowsPath
    }

    return $unixPath
}

function Complete-Step {
    param(
        [string]$Id,
        [string]$Name,
        [string]$Command,
        [scriptblock]$Action,
        [switch]$NetworkRequired,
        [switch]$Skipped,
        [hashtable]$Details = @{}
    )

    if ($Skipped) {
        Add-Step -Id $Id -Name $Name -Status 'skipped' -Message 'Etapa pulada por parametro.' -Command $Command -Details $Details
        return
    }

    if ($NetworkRequired -and $NoNetwork) {
        Add-Step -Id $Id -Name $Name -Status 'skipped' -Message 'Etapa pulada por -NoNetwork porque pode baixar dependencias.' -Command $Command -Details $Details
        return
    }

    if ($DryRun) {
        Add-Step -Id $Id -Name $Name -Status 'planned' -Message 'Etapa planejada; nada foi executado por -DryRun.' -Command $Command -Details $Details
        return
    }

    try {
        & $Action
        Add-Step -Id $Id -Name $Name -Status 'ok' -Message 'Etapa concluida.' -Command $Command -Details $Details
    }
    catch {
        $message = $_.Exception.Message
        $errors.Add("${Id}: $message") | Out-Null
        Add-Step -Id $Id -Name $Name -Status 'error' -Message $message -Command $Command -Details $Details
    }
}

$checkCommand = 'powershell -ExecutionPolicy Bypass -File .\scripts\check_dev_environment.ps1'
if ($NoNetwork) {
    $checkCommand = "$checkCommand -NoNetwork"
}

Complete-Step `
    -Id 'check.dev_environment' `
    -Name 'Check seguro de ambiente DEV' `
    -Command $checkCommand `
    -Skipped:$SkipCheck `
    -Action {
        $checkScript = Join-Path $root 'scripts/check_dev_environment.ps1'
        if ($Json) {
            if ($NoNetwork) {
                & $checkScript -Json -NoNetwork *> $null
            }
            else {
                & $checkScript -Json *> $null
            }
        }
        else {
            if ($NoNetwork) {
                & $checkScript -NoNetwork
            }
            else {
                & $checkScript
            }
        }
        if ($LASTEXITCODE -ne 0) {
            throw 'check_dev_environment.ps1 retornou erro.'
        }
    }

$backendVenvCommand = 'python -m venv .\backend\.venv'
Complete-Step `
    -Id 'backend.venv' `
    -Name 'Backend venv' `
    -Command $backendVenvCommand `
    -Skipped:$SkipBackend `
    -Action {
        $backendPython = Get-BackendPythonPath
        if (Test-Path $backendPython) {
            return
        }
        Invoke-Native -Executable 'python' -Arguments @('-m', 'venv', (Join-Path $root 'backend/.venv'))
    }

$backendPythonForCommand = Get-BackendPythonPath
$backendDepsCommand = '.\backend\.venv\Scripts\python.exe -m pip install -r .\backend\requirements.txt'
Complete-Step `
    -Id 'backend.dependencies' `
    -Name 'Dependencias backend' `
    -Command $backendDepsCommand `
    -Skipped:$SkipBackend `
    -NetworkRequired `
    -Action {
        $backendPython = Get-BackendPythonPath
        if (-not (Test-Path $backendPython)) {
            throw 'Backend venv nao encontrado; rode a etapa backend.venv primeiro.'
        }
        Invoke-Native -Executable $backendPython -Arguments @('-m', 'pip', 'install', '-r', (Join-Path $root 'backend/requirements.txt'))
    } `
    -Details @{
        python = $backendPythonForCommand
    }

$frontendCommand = 'npm ci'
if (-not (Test-Path (Join-Path $root 'frontend/package-lock.json'))) {
    $frontendCommand = 'npm install'
}
Complete-Step `
    -Id 'frontend.dependencies' `
    -Name 'Dependencias frontend' `
    -Command "cd frontend; $frontendCommand" `
    -Skipped:$SkipFrontend `
    -NetworkRequired `
    -Action {
        if (Test-Path (Join-Path $root 'frontend/package-lock.json')) {
            Invoke-Native -Executable 'npm' -Arguments @('ci') -WorkingDirectory (Join-Path $root 'frontend')
        }
        else {
            Invoke-Native -Executable 'npm' -Arguments @('install') -WorkingDirectory (Join-Path $root 'frontend')
        }
    }

Complete-Step `
    -Id 'mcp.setup' `
    -Name 'Setup MCP local' `
    -Command 'powershell -ExecutionPolicy Bypass -File .\scripts\setup_mcp_local.ps1 -InstalarExtensoesVSCode:$false -InstalarInspector:$false -ConfigurarCodex:$true' `
    -Skipped:$SkipMcp `
    -NetworkRequired `
    -Action {
        & (Join-Path $root 'scripts/setup_mcp_local.ps1') -InstalarExtensoesVSCode:$false -InstalarInspector:$false -ConfigurarCodex:$true
        if ($LASTEXITCODE -ne 0) {
            throw 'setup_mcp_local.ps1 retornou erro.'
        }
    }

$ok = @($steps | Where-Object { $_.status -eq 'ok' }).Count
$planned = @($steps | Where-Object { $_.status -eq 'planned' }).Count
$skipped = @($steps | Where-Object { $_.status -eq 'skipped' }).Count
$failed = @($steps | Where-Object { $_.status -eq 'error' }).Count

$report = [pscustomobject][ordered]@{
    project = 'Sistema-Pet'
    root = $root
    mode = if ($DryRun) { 'dry-run' } elseif ($NoNetwork) { 'no-network' } else { 'default' }
    status = if ($failed -gt 0) { 'error' } elseif ($planned -gt 0 -or $skipped -gt 0) { 'partial' } else { 'ok' }
    summary = [pscustomobject][ordered]@{
        total = $steps.Count
        ok = $ok
        planned = $planned
        skipped = $skipped
        errors = $failed
    }
    steps = $steps
    errors = $errors
}

if ($Json) {
    $report | ConvertTo-Json -Depth 8
}
else {
    Write-Host '=== Sistema Pet - bootstrap ambiente DEV ===' -ForegroundColor Cyan
    Write-Host "Raiz: $root"
    Write-Host "Modo: $($report.mode)"
    Write-Host ''

    foreach ($step in $steps) {
        $label = $step.status.ToUpperInvariant()
        $color = switch ($step.status) {
            'ok' { 'Green' }
            'planned' { 'Cyan' }
            'skipped' { 'Yellow' }
            'error' { 'Red' }
        }

        Write-Host "[$label] $($step.name): $($step.message)" -ForegroundColor $color
        if ($step.command) {
            Write-Host "      Comando: $($step.command)" -ForegroundColor DarkGray
        }
    }

    Write-Host ''
    Write-Host "Resumo: $ok ok, $planned planejada(s), $skipped pulada(s), $failed erro(s)."
    Write-Host 'Valores de secrets nao sao impressos por este script.' -ForegroundColor DarkGray
}

if ($failed -gt 0) {
    exit 1
}

exit 0
