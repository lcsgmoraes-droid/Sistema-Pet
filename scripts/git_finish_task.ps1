param(
    [Parameter(Mandatory = $true)]
    [string]$Mensagem,

    [switch]$Push
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $root

function Fail([string]$message) {
    Write-Host "ERRO: $message" -ForegroundColor Red
    exit 1
}

function Convert-GitPath([string]$path) {
    return $path.Trim().Trim('"').Replace('\', '/')
}

function Get-ChangedPath([string]$line) {
    if ($line.Length -lt 4) {
        return ''
    }

    $path = $line.Substring(3)
    if ($path.Contains(' -> ')) {
        $path = ($path -split ' -> ')[0]
    }

    return Convert-GitPath $path
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Fail 'Git nao encontrado neste PC.'
}

git rev-parse --is-inside-work-tree *> $null
if ($LASTEXITCODE -ne 0) {
    Fail 'Execute este script dentro do repositorio Sistema-Pet.'
}

$branch = (git rev-parse --abbrev-ref HEAD).Trim()
if ($branch -eq 'main' -or $branch -eq 'master') {
    Fail "Nao feche tarefa direto em $branch. Crie uma branch de tarefa primeiro."
}

$status = @(git status --porcelain)
if ($status.Count -eq 0) {
    Write-Host 'Nada para commitar.' -ForegroundColor Yellow
    exit 0
}

Write-Host "Branch atual: $branch" -ForegroundColor Cyan
Write-Host 'Alteracoes encontradas:'
$status | Select-Object -First 60 | ForEach-Object { Write-Host "  $_" }

$protectedRegexes = @(
    '^docker-compose\..*\.yml$',
    '^\.env\.example$',
    '^\.env\.production$',
    '^frontend/\.env\.production$',
    '^scripts/fluxo_unico\.ps1$',
    '^scripts/validar_fluxo\.ps1$',
    '^\.github/copilot-instructions\.md$',
    '^\.github/assistant-rules\.json$',
    '^docs/FLUXO_UNICO_DEV_PROD\.md$'
)

$blockedDeletes = @()
foreach ($line in $status) {
    $xy = $line.Substring(0, [Math]::Min(2, $line.Length))
    if (-not $xy.Contains('D')) {
        continue
    }

    $path = Get-ChangedPath $line
    foreach ($regex in $protectedRegexes) {
        if ($path -match $regex) {
            $blockedDeletes += $path
            break
        }
    }
}

if ($blockedDeletes.Count -gt 0) {
    Write-Host 'Arquivos protegidos aparecem como deletados:' -ForegroundColor Yellow
    $blockedDeletes | Sort-Object -Unique | ForEach-Object { Write-Host "  $_" }
    Fail 'Commit bloqueado para evitar apagar arquivos importantes.'
}

$validator = Join-Path $PSScriptRoot 'validar_fluxo.ps1'
if (Test-Path $validator) {
    & $validator -PermitirAlteracoesLocais
    if ($LASTEXITCODE -ne 0) {
        Fail 'Validacao do fluxo falhou.'
    }
}

git add -A
if ($LASTEXITCODE -ne 0) {
    Fail 'Falha ao preparar arquivos para commit.'
}

$staged = @(git diff --cached --name-only)
if ($staged.Count -eq 0) {
    Write-Host 'Nada preparado para commit.' -ForegroundColor Yellow
    exit 0
}

git commit -m $Mensagem
if ($LASTEXITCODE -ne 0) {
    Fail 'Falha ao criar commit.'
}

if ($Push) {
    git push -u origin $branch
    if ($LASTEXITCODE -ne 0) {
        Fail 'Falha ao enviar branch para o GitHub.'
    }

    Write-Host 'OK: branch enviada. Abra o Pull Request no GitHub.' -ForegroundColor Green
} else {
    Write-Host 'OK: commit criado localmente. Use -Push para enviar a branch ao GitHub.' -ForegroundColor Green
}
