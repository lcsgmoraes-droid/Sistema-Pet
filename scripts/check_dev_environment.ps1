param(
    [switch]$Json,
    [switch]$NoNetwork,
    [switch]$Strict,
    [string]$EnvFile = '.env.development'
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $root

$checks = [System.Collections.Generic.List[object]]::new()

function Add-Check {
    param(
        [string]$Id,
        [string]$Name,
        [ValidateSet('ok', 'warning', 'error', 'skipped')]
        [string]$Status,
        [string]$Message,
        [string]$Fix = '',
        [hashtable]$Details = @{}
    )

    $checks.Add([pscustomobject][ordered]@{
        id = $Id
        name = $Name
        status = $Status
        message = $Message
        fix = $Fix
        details = [pscustomobject]$Details
    }) | Out-Null
}

function Get-VersionLine {
    param(
        [string]$Command,
        [string[]]$Arguments
    )

    try {
        $output = & $Command @Arguments 2>&1 | Select-Object -First 1
        if ($output) {
            return ($output -join ' ').Trim()
        }
    }
    catch {
        return ''
    }

    return ''
}

function Test-Tool {
    param(
        [string]$Id,
        [string]$Name,
        [string]$Command,
        [string[]]$VersionArgs,
        [string]$Fix
    )

    $resolved = Get-Command $Command -ErrorAction SilentlyContinue
    if (-not $resolved) {
        Add-Check -Id $Id -Name $Name -Status 'error' -Message "$Command nao encontrado no PATH." -Fix $Fix -Details @{
            command = $Command
        }
        return
    }

    $version = Get-VersionLine -Command $Command -Arguments $VersionArgs
    Add-Check -Id $Id -Name $Name -Status 'ok' -Message "$Command encontrado." -Details @{
        command = $Command
        source = $resolved.Source
        version = $version
    }
}

function Test-RequiredPaths {
    $requiredPaths = @(
        'backend',
        'frontend',
        'mcp',
        'docker-compose.local-dev.yml',
        'scripts/git_start_task.ps1',
        'scripts/git_finish_task.ps1',
        'scripts/validar_fluxo.ps1'
    )

    $missing = @()
    foreach ($relativePath in $requiredPaths) {
        if (-not (Test-Path (Join-Path $root $relativePath))) {
            $missing += $relativePath
        }
    }

    if ($missing.Count -gt 0) {
        Add-Check -Id 'project.required_paths' -Name 'Arquivos essenciais do projeto' -Status 'error' -Message 'Arquivos ou pastas essenciais nao foram encontrados.' -Fix 'Confirme se este comando esta sendo executado na raiz do repositorio Sistema-Pet.' -Details @{
            missing = $missing
        }
        return
    }

    Add-Check -Id 'project.required_paths' -Name 'Arquivos essenciais do projeto' -Status 'ok' -Message 'Estrutura essencial encontrada.'
}

function Get-EnvFileKeys {
    param([string]$Path)

    $keys = [System.Collections.Generic.HashSet[string]]::new()
    $lines = Get-Content -Path $Path
    foreach ($line in $lines) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith('#')) {
            continue
        }

        $match = [regex]::Match($trimmed, '^([A-Za-z_][A-Za-z0-9_]*)\s*=')
        if ($match.Success) {
            [void]$keys.Add($match.Groups[1].Value)
        }
    }

    return $keys
}

function Test-EnvFile {
    $envPath = Join-Path $root $EnvFile
    if (-not (Test-Path $envPath)) {
        Add-Check -Id 'project.env_file' -Name 'Arquivo de ambiente DEV' -Status 'warning' -Message "$EnvFile nao encontrado." -Fix "Crie $EnvFile a partir de .env.example ou use as variaveis do docker-compose local. Nao cole secrets em chat."
        Add-Check -Id 'project.env_required_keys' -Name 'Chaves obrigatorias do ambiente' -Status 'skipped' -Message 'Validacao de chaves pulada porque o arquivo de ambiente nao existe.'
        return
    }

    Add-Check -Id 'project.env_file' -Name 'Arquivo de ambiente DEV' -Status 'ok' -Message "$EnvFile encontrado. Valores nao foram impressos."

    $keys = Get-EnvFileKeys -Path $envPath
    $requiredKeys = @('DATABASE_URL', 'JWT_SECRET_KEY', 'ENVIRONMENT')
    $missing = @()
    foreach ($key in $requiredKeys) {
        if (-not $keys.Contains($key)) {
            $missing += $key
        }
    }

    if ($missing.Count -gt 0) {
        Add-Check -Id 'project.env_required_keys' -Name 'Chaves obrigatorias do ambiente' -Status 'warning' -Message 'Arquivo de ambiente existe, mas faltam chaves esperadas.' -Fix 'Complete apenas os nomes de variaveis faltantes no arquivo local; mantenha valores reais fora do Git.' -Details @{
            missing_keys = $missing
        }
        return
    }

    Add-Check -Id 'project.env_required_keys' -Name 'Chaves obrigatorias do ambiente' -Status 'ok' -Message 'Chaves obrigatorias encontradas. Valores nao foram impressos.'
}

function Test-GitWorkingTree {
    $git = Get-Command git -ErrorAction SilentlyContinue
    if (-not $git) {
        Add-Check -Id 'git.working_tree' -Name 'Estado do Git' -Status 'skipped' -Message 'Git nao encontrado; estado do repositorio nao foi validado.'
        return
    }

    git rev-parse --is-inside-work-tree *> $null
    if ($LASTEXITCODE -ne 0) {
        Add-Check -Id 'git.working_tree' -Name 'Estado do Git' -Status 'error' -Message 'Este diretorio nao parece ser um repositorio Git.' -Fix 'Execute o script dentro da pasta Sistema-Pet.'
        return
    }

    $branch = (git rev-parse --abbrev-ref HEAD).Trim()
    $changes = @(git status --porcelain)
    if ($changes.Count -gt 0) {
        Add-Check -Id 'git.working_tree' -Name 'Estado do Git' -Status 'warning' -Message "Branch $branch tem $($changes.Count) alteracao(oes) local(is)." -Fix 'Antes de trocar de tarefa, commite via git_finish_task.ps1 ou deixe claro o que fica pendente.' -Details @{
            branch = $branch
            local_changes = $changes.Count
        }
        return
    }

    Add-Check -Id 'git.working_tree' -Name 'Estado do Git' -Status 'ok' -Message "Branch $branch sem alteracoes locais." -Details @{
        branch = $branch
        local_changes = 0
    }
}

function Test-GitHubAuth {
    if ($NoNetwork) {
        Add-Check -Id 'network.github_auth' -Name 'Autenticacao GitHub CLI' -Status 'skipped' -Message 'Check pulado por -NoNetwork.'
        return
    }

    if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
        Add-Check -Id 'network.github_auth' -Name 'Autenticacao GitHub CLI' -Status 'skipped' -Message 'gh nao encontrado; autenticacao nao foi validada.'
        return
    }

    gh auth status --hostname github.com *> $null
    if ($LASTEXITCODE -ne 0) {
        Add-Check -Id 'network.github_auth' -Name 'Autenticacao GitHub CLI' -Status 'warning' -Message 'GitHub CLI nao esta autenticado.' -Fix 'Rode gh auth login --hostname github.com --web --git-protocol https --scopes repo,workflow.'
        return
    }

    Add-Check -Id 'network.github_auth' -Name 'Autenticacao GitHub CLI' -Status 'ok' -Message 'GitHub CLI autenticado. Token nao foi impresso.'
}

function Test-DockerDaemon {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Add-Check -Id 'docker.daemon' -Name 'Docker daemon' -Status 'skipped' -Message 'Docker nao encontrado; daemon nao foi validado.'
        Add-Check -Id 'docker.compose' -Name 'Docker Compose' -Status 'skipped' -Message 'Docker nao encontrado; compose nao foi validado.'
        return
    }

    docker info *> $null
    if ($LASTEXITCODE -ne 0) {
        Add-Check -Id 'docker.daemon' -Name 'Docker daemon' -Status 'warning' -Message 'Docker existe, mas o daemon nao respondeu.' -Fix 'Abra o Docker Desktop e aguarde ficar Running.'
    }
    else {
        Add-Check -Id 'docker.daemon' -Name 'Docker daemon' -Status 'ok' -Message 'Docker daemon respondeu.'
    }

    docker compose version *> $null
    if ($LASTEXITCODE -ne 0) {
        Add-Check -Id 'docker.compose' -Name 'Docker Compose' -Status 'warning' -Message 'docker compose nao respondeu.' -Fix 'Atualize Docker Desktop ou instale o plugin Docker Compose.'
    }
    else {
        Add-Check -Id 'docker.compose' -Name 'Docker Compose' -Status 'ok' -Message 'Docker Compose respondeu.'
    }
}

function Test-LocalDependencies {
    $backendPython = Join-Path $root 'backend/.venv/Scripts/python.exe'
    $backendPythonUnix = Join-Path $root 'backend/.venv/bin/python'
    if ((Test-Path $backendPython) -or (Test-Path $backendPythonUnix)) {
        Add-Check -Id 'deps.backend_venv' -Name 'Backend venv' -Status 'ok' -Message 'Ambiente virtual do backend encontrado.'
    }
    else {
        Add-Check -Id 'deps.backend_venv' -Name 'Backend venv' -Status 'warning' -Message 'Ambiente virtual do backend nao encontrado.' -Fix 'Crie o venv do backend antes de rodar testes locais.'
    }

    if (Test-Path (Join-Path $root 'frontend/node_modules')) {
        Add-Check -Id 'deps.frontend_node_modules' -Name 'Dependencias frontend' -Status 'ok' -Message 'frontend/node_modules encontrado.'
    }
    else {
        Add-Check -Id 'deps.frontend_node_modules' -Name 'Dependencias frontend' -Status 'warning' -Message 'frontend/node_modules nao encontrado.' -Fix 'Rode npm install dentro de frontend quando precisar trabalhar no frontend.'
    }

    $mcpMissing = @()
    foreach ($mcpPath in @('mcp/frontend_react_server/.venv', 'mcp/ops_api_server/.venv')) {
        if (-not (Test-Path (Join-Path $root $mcpPath))) {
            $mcpMissing += $mcpPath
        }
    }

    if ($mcpMissing.Count -gt 0) {
        Add-Check -Id 'deps.mcp_venvs' -Name 'MCP venvs' -Status 'warning' -Message 'Ambientes virtuais de MCP incompletos.' -Fix 'Rode scripts/setup_mcp_local.ps1 para preparar os MCPs locais.' -Details @{
            missing = $mcpMissing
        }
    }
    else {
        Add-Check -Id 'deps.mcp_venvs' -Name 'MCP venvs' -Status 'ok' -Message 'Ambientes virtuais dos MCPs encontrados.'
    }
}

Test-Tool -Id 'tool.git' -Name 'Git' -Command 'git' -VersionArgs @('--version') -Fix 'Instale Git for Windows e reabra o terminal.'
Test-Tool -Id 'tool.python' -Name 'Python' -Command 'python' -VersionArgs @('--version') -Fix 'Instale Python 3.11+ e marque Add to PATH.'
Test-Tool -Id 'tool.node' -Name 'Node.js' -Command 'node' -VersionArgs @('--version') -Fix 'Instale Node.js LTS e reabra o terminal.'
Test-Tool -Id 'tool.npm' -Name 'npm' -Command 'npm' -VersionArgs @('--version') -Fix 'Instale Node.js LTS; npm vem junto.'
Test-Tool -Id 'tool.docker' -Name 'Docker' -Command 'docker' -VersionArgs @('--version') -Fix 'Instale Docker Desktop e abra antes de subir DEV.'
Test-Tool -Id 'tool.gh' -Name 'GitHub CLI' -Command 'gh' -VersionArgs @('--version') -Fix 'Instale GitHub CLI e rode gh auth login.'
Test-Tool -Id 'tool.ssh' -Name 'SSH' -Command 'ssh' -VersionArgs @('-V') -Fix 'Instale OpenSSH Client ou Git for Windows.'

Test-RequiredPaths
Test-EnvFile
Test-GitWorkingTree
Test-GitHubAuth
Test-DockerDaemon
Test-LocalDependencies

$errors = @($checks | Where-Object { $_.status -eq 'error' }).Count
$warnings = @($checks | Where-Object { $_.status -eq 'warning' }).Count
$skipped = @($checks | Where-Object { $_.status -eq 'skipped' }).Count
$ok = @($checks | Where-Object { $_.status -eq 'ok' }).Count

$overallStatus = 'ok'
if ($errors -gt 0) {
    $overallStatus = 'error'
}
elseif ($warnings -gt 0) {
    $overallStatus = 'warning'
}

$report = [pscustomobject][ordered]@{
    project = 'Sistema-Pet'
    root = $root
    mode = if ($NoNetwork) { 'no-network' } else { 'default' }
    status = $overallStatus
    summary = [pscustomobject][ordered]@{
        total = $checks.Count
        ok = $ok
        warnings = $warnings
        errors = $errors
        skipped = $skipped
    }
    checks = $checks
}

if ($Json) {
    $report | ConvertTo-Json -Depth 8
}
else {
    Write-Host '=== Sistema Pet - check seguro de ambiente DEV ===' -ForegroundColor Cyan
    Write-Host "Raiz: $root"
    Write-Host "Modo: $($report.mode)"
    Write-Host ''

    foreach ($check in $checks) {
        $label = $check.status.ToUpperInvariant()
        $color = switch ($check.status) {
            'ok' { 'Green' }
            'warning' { 'Yellow' }
            'error' { 'Red' }
            default { 'DarkGray' }
        }

        Write-Host "[$label] $($check.name): $($check.message)" -ForegroundColor $color
        if ($check.fix) {
            Write-Host "      Como corrigir: $($check.fix)" -ForegroundColor DarkGray
        }
    }

    Write-Host ''
    Write-Host "Resumo: $ok ok, $warnings aviso(s), $errors erro(s), $skipped pulado(s)."
    Write-Host 'Valores de secrets nao sao impressos por este script.' -ForegroundColor DarkGray
}

if ($Strict -and $errors -gt 0) {
    exit 1
}

exit 0
