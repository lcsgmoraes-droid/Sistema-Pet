param(
    [Parameter(Mandatory = $true)]
    [string]$Nome,

    [ValidateSet('feat', 'fix', 'docs', 'chore', 'refactor', 'test', 'hotfix')]
    [string]$Tipo = 'feat'
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $root

function Fail([string]$message) {
    Write-Host "ERRO: $message" -ForegroundColor Red
    exit 1
}

function Require-CleanTree {
    $status = @(git status --porcelain)
    if ($status.Count -gt 0) {
        Write-Host 'Existem alteracoes locais. Feche, commite ou guarde antes de iniciar outra tarefa:' -ForegroundColor Yellow
        $status | Select-Object -First 30 | ForEach-Object { Write-Host "  $_" }
        Fail 'Arvore de trabalho nao esta limpa.'
    }
}

function Test-BranchExists([string]$name) {
    git show-ref --verify --quiet "refs/heads/$name"
    return $LASTEXITCODE -eq 0
}

function New-Slug([string]$text) {
    $normalized = $text.Normalize([System.Text.NormalizationForm]::FormD)
    $builder = [System.Text.StringBuilder]::new()

    foreach ($char in $normalized.ToCharArray()) {
        $category = [System.Globalization.CharUnicodeInfo]::GetUnicodeCategory($char)
        if ($category -ne [System.Globalization.UnicodeCategory]::NonSpacingMark) {
            [void]$builder.Append($char)
        }
    }

    $plain = $builder.ToString().Normalize([System.Text.NormalizationForm]::FormC).ToLowerInvariant()
    $slug = [regex]::Replace($plain, '[^a-z0-9]+', '-').Trim('-')

    if ([string]::IsNullOrWhiteSpace($slug)) {
        $slug = 'tarefa'
    }

    if ($slug.Length -gt 48) {
        $slug = $slug.Substring(0, 48).Trim('-')
    }

    return $slug
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Fail 'Git nao encontrado neste PC.'
}

git rev-parse --is-inside-work-tree *> $null
if ($LASTEXITCODE -ne 0) {
    Fail 'Execute este script dentro do repositorio Sistema-Pet.'
}

Require-CleanTree

$currentBranch = (git rev-parse --abbrev-ref HEAD).Trim()
if ($currentBranch -ne 'main') {
    Fail "Voce esta na branch '$currentBranch'. Finalize essa tarefa antes de abrir outra."
}

Write-Host 'Atualizando main a partir do GitHub...' -ForegroundColor Cyan
git fetch origin
if ($LASTEXITCODE -ne 0) {
    Fail 'Falha ao buscar atualizacoes do GitHub.'
}

git switch main
if ($LASTEXITCODE -ne 0) {
    Fail 'Falha ao trocar para main.'
}

git pull --ff-only origin main
if ($LASTEXITCODE -ne 0) {
    Fail 'Nao foi possivel atualizar main com fast-forward. Resolva o Git antes de continuar.'
}

Require-CleanTree

$slug = New-Slug $Nome
$stamp = Get-Date -Format 'yyyyMMdd-HHmm'
$branch = "$Tipo/$stamp-$slug"
$candidate = $branch
$counter = 2

while (Test-BranchExists $candidate) {
    $candidate = "$branch-$counter"
    $counter++
}

git switch -c $candidate
if ($LASTEXITCODE -ne 0) {
    Fail "Falha ao criar branch: $candidate"
}

Write-Host "OK: tarefa iniciada na branch $candidate" -ForegroundColor Green
Write-Host 'Agora pode trabalhar normalmente. Ao terminar, use git_finish_task.ps1.'
