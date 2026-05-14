param()

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $root

function Fail([string]$message) {
    Write-Host "ERRO: $message" -ForegroundColor Red
    exit 1
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Fail 'Git nao encontrado neste PC.'
}

git rev-parse --is-inside-work-tree *> $null
if ($LASTEXITCODE -ne 0) {
    Fail 'Execute este script dentro do repositorio Sistema-Pet.'
}

$hooksPath = Join-Path $root '.githooks'
if (-not (Test-Path $hooksPath)) {
    Fail "Pasta de hooks nao encontrada: $hooksPath"
}

git config core.hooksPath .githooks
git config pull.ff only
git config fetch.prune true

Write-Host 'OK: regras locais do Git ativadas neste PC.' -ForegroundColor Green
Write-Host 'Hooks ativos: bloqueiam commit/push direto em main/master.'
Write-Host 'Repita este script uma vez no outro computador depois de atualizar o repositorio.'
