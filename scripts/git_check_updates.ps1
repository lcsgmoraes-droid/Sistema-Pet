param(
    [switch]$NoFetch
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $root

function Fail([string]$message) {
    Write-Host "ERRO: $message" -ForegroundColor Red
    exit 1
}

function Test-GitRef([string]$ref) {
    git show-ref --verify --quiet $ref
    return $LASTEXITCODE -eq 0
}

function Get-AheadBehind([string]$left, [string]$right) {
    $raw = (git rev-list --left-right --count "$left...$right").Trim()
    if ($LASTEXITCODE -ne 0) {
        Fail "Nao foi possivel comparar $left com $right."
    }

    $parts = $raw -split '\s+'
    return [pscustomobject]@{
        LeftAhead  = [int]$parts[0]
        RightAhead = [int]$parts[1]
    }
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Fail 'Git nao encontrado neste PC.'
}

git rev-parse --is-inside-work-tree *> $null
if ($LASTEXITCODE -ne 0) {
    Fail 'Execute este script dentro do repositorio Sistema-Pet.'
}

if (-not $NoFetch) {
    Write-Host 'Consultando o GitHub...' -ForegroundColor Cyan
    git fetch --prune origin
    if ($LASTEXITCODE -ne 0) {
        Fail 'Falha ao buscar atualizacoes do GitHub.'
    }
}

$branch = (git rev-parse --abbrev-ref HEAD).Trim()
$localChanges = @(git status --porcelain)
$actions = @()

Write-Host ''
Write-Host "Branch atual: $branch" -ForegroundColor Cyan

if ($localChanges.Count -gt 0) {
    Write-Host "Alteracoes locais: $($localChanges.Count)" -ForegroundColor Yellow
    $actions += 'Antes de baixar novidades, feche/commite as alteracoes locais desta branch.'
} else {
    Write-Host 'Alteracoes locais: 0' -ForegroundColor Green
}

if ((Test-GitRef 'refs/heads/main') -and (Test-GitRef 'refs/remotes/origin/main')) {
    $main = Get-AheadBehind 'main' 'origin/main'

    if ($main.RightAhead -gt 0) {
        Write-Host "Main deste PC: precisa baixar $($main.RightAhead) commit(s) do GitHub." -ForegroundColor Yellow
        $actions += 'Antes da proxima tarefa neste PC, rode git_start_task.ps1 ou atualize a main com git pull --ff-only origin main.'
    } elseif ($main.LeftAhead -gt 0) {
        Write-Host "Main deste PC: tem $($main.LeftAhead) commit(s) que ainda nao estao no GitHub." -ForegroundColor Yellow
        $actions += 'Evite trabalhar direto na main. Organize esses commits antes de continuar.'
    } else {
        Write-Host 'Main deste PC: sincronizada com origin/main.' -ForegroundColor Green
    }
} else {
    Write-Host 'Main deste PC: nao foi possivel comparar com origin/main.' -ForegroundColor Yellow
    $actions += 'Confira se este repositorio tem main e origin/main configurados.'
}

$previousErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = 'SilentlyContinue'
try {
    $upstreamRaw = git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>$null
    $upstreamExitCode = $LASTEXITCODE
} finally {
    $ErrorActionPreference = $previousErrorActionPreference
}

if ($upstreamExitCode -eq 0 -and -not [string]::IsNullOrWhiteSpace($upstreamRaw)) {
    $upstream = ($upstreamRaw | Select-Object -First 1).Trim()
    $current = Get-AheadBehind 'HEAD' $upstream

    if ($current.RightAhead -gt 0) {
        Write-Host "Branch atual: precisa baixar $($current.RightAhead) commit(s) de $upstream." -ForegroundColor Yellow
        $actions += 'Nesta branch, rode git pull --ff-only antes de continuar.'
    } elseif ($current.LeftAhead -gt 0) {
        Write-Host "Branch atual: tem $($current.LeftAhead) commit(s) local(is) para subir em $upstream." -ForegroundColor Yellow
        $actions += 'Quando a tarefa estiver pronta, rode git_finish_task.ps1 -Push.'
    } else {
        Write-Host "Branch atual: sincronizada com $upstream." -ForegroundColor Green
    }
} else {
    Write-Host 'Branch atual: ainda sem remoto configurado.' -ForegroundColor Yellow
    $actions += 'Ao fechar a tarefa com git_finish_task.ps1 -Push, a branch sera enviada ao GitHub.'
}

Write-Host ''
if ($actions.Count -eq 0) {
    Write-Host 'OK: este PC esta sincronizado. Pode seguir.' -ForegroundColor Green
} else {
    Write-Host 'Acoes recomendadas:' -ForegroundColor Yellow
    $actions | Select-Object -Unique | ForEach-Object { Write-Host "  - $_" }
}
