param(
    [switch]$SemPergunta,
    [switch]$ExecutarCommit,
    [switch]$ExecutarPush
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $root

$prepareScript = Join-Path $PSScriptRoot 'preparar_commit_bloco.ps1'
$fluxoScript = Join-Path $PSScriptRoot 'fluxo_unico.ps1'

$blocos = @(
    @{ Nome = 'bloco1'; Mensagem = 'chore(repo): remover backups do git e reforcar gitignore' },
    @{ Nome = 'bloco2'; Mensagem = 'chore(flow): padronizar fluxo unico dev-prod e tarefas vscode' },
    @{ Nome = 'bloco3'; Mensagem = 'fix(migrations): unificar heads alembic em uma unica linha' }
)

function Perguntar-SimNao([string]$texto) {
    if ($SemPergunta) { return $true }
    $resp = Read-Host "$texto [S/N]"
    return ($resp -match '^(s|S)$')
}

function Rodar-Fluxo([string]$acao) {
    & powershell -ExecutionPolicy Bypass -File $fluxoScript $acao
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao executar fluxo: $acao"
    }
}

Write-Host "`n=== Assistente Release Seguro ===" -ForegroundColor Cyan
Write-Host "Branch atual: $((git rev-parse --abbrev-ref HEAD).Trim())"
if (-not $ExecutarCommit) {
    Write-Host "Modo atual: SIMULACAO (nao vai commitar nem dar push)." -ForegroundColor Yellow
}

foreach ($bloco in $blocos) {
    Write-Host "`nPreparando $($bloco.Nome)..." -ForegroundColor Yellow
    & powershell -ExecutionPolicy Bypass -File $prepareScript $bloco.Nome

    $staged = @(git diff --cached --name-only)
    if ($staged.Count -eq 0) {
        Write-Host "Nada staged no $($bloco.Nome). Pulando." -ForegroundColor DarkYellow
        continue
    }

    Write-Host "Arquivos staged do $($bloco.Nome): $($staged.Count)"
    $staged | Select-Object -First 20 | ForEach-Object { Write-Host "  $_" }

    if (-not $ExecutarCommit) {
        Write-Host "Simulacao: bloco preparado, sem commit." -ForegroundColor DarkYellow
        continue
    }

    if (-not (Perguntar-SimNao "Commitar $($bloco.Nome) agora?")) {
        Write-Host "Parado por decisao do usuario." -ForegroundColor Yellow
        exit 0
    }

    git commit -m $bloco.Mensagem
    if ($LASTEXITCODE -ne 0) {
        throw "Falha no commit do $($bloco.Nome)."
    }
}

Write-Host "`nRodando validacoes finais..." -ForegroundColor Cyan
Rodar-Fluxo 'check'
Rodar-Fluxo 'release-check'

if (-not $ExecutarPush) {
    Write-Host "Push nao executado (modo seguro)." -ForegroundColor Yellow
    Write-Host "Para executar push com assistente: usar parametro -ExecutarPush." -ForegroundColor Yellow
    exit 0
}

if (Perguntar-SimNao "Tudo validado. Posso fazer push final?") {
    git push
    if ($LASTEXITCODE -ne 0) {
        throw 'Falha no push final.'
    }
    Write-Host "Push final concluido." -ForegroundColor Green
} else {
    Write-Host "Push nao executado por escolha do usuario." -ForegroundColor Yellow
}
