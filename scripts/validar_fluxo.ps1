param(
    [switch]$PermitirAlteracoesLocais
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $root

function Write-Section([string]$text) {
    Write-Host "`n=== $text ===" -ForegroundColor Cyan
}

function Fail([string]$message) {
    Write-Host "ERRO: $message" -ForegroundColor Red
    exit 1
}

function Check-Command([string]$command) {
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
        Fail "Comando obrigatório não encontrado: $command"
    }
}

function Get-AlembicHeads {
    $versionsPath = Join-Path $root 'backend/alembic/versions'
    if (-not (Test-Path $versionsPath)) {
        return @()
    }

    $revisionSet = [System.Collections.Generic.HashSet[string]]::new()
    $downRevisionSet = [System.Collections.Generic.HashSet[string]]::new()

    $files = Get-ChildItem -Path $versionsPath -Filter '*.py' -File
    foreach ($file in $files) {
        $content = Get-Content -Path $file.FullName -Raw

        $revMatch = [regex]::Match($content, "revision\s*:\s*[^=]+\s*=\s*'([^']+)'")
        if (-not $revMatch.Success) {
            $revMatch = [regex]::Match($content, "revision\s*=\s*'([^']+)'")
        }

        if ($revMatch.Success) {
            [void]$revisionSet.Add($revMatch.Groups[1].Value)
        }

        $downLine = [regex]::Match($content, "down_revision\s*:\s*[^=]+\s*=\s*([^`r`n]+)")
        if (-not $downLine.Success) {
            $downLine = [regex]::Match($content, "down_revision\s*=\s*([^`r`n]+)")
        }

        if ($downLine.Success) {
            $downRaw = $downLine.Groups[1].Value
            $matches = [regex]::Matches($downRaw, "'([^']+)'")
            foreach ($m in $matches) {
                [void]$downRevisionSet.Add($m.Groups[1].Value)
            }
        }
    }

    $heads = @()
    foreach ($revision in $revisionSet) {
        if (-not $downRevisionSet.Contains($revision)) {
            $heads += $revision
        }
    }

    return $heads
}

Check-Command 'git'

Write-Section 'Validacao de fluxo DEV -> PROD'
Write-Host "Raiz: $root"

$branch = (git rev-parse --abbrev-ref HEAD).Trim()
Write-Host "Branch atual: $branch"

Write-Section '1) Estado do Git'
$workingTree = @(git status --porcelain)
$changesCount = $workingTree.Count
Write-Host "Alteracoes locais: $changesCount"

if (-not $PermitirAlteracoesLocais -and $changesCount -gt 0) {
    Write-Host "Primeiras alterações encontradas:" -ForegroundColor Yellow
    $workingTree | Select-Object -First 20 | ForEach-Object { Write-Host "  $_" }
    Fail 'Release bloqueada: ha alteracoes locais. Commit/stash antes de subir producao.'
}

Write-Section '2) Arquivos proibidos rastreados'
$forbiddenTracked = @(
    git ls-files "backups/**"
    git ls-files "limpeza/**"
    git ls-files "simplesvet/**"
    git ls-files "tmp_*" ".tmp_*"
    git ls-files "*.dump" "*.sql.gz" "*.tar" "*.tar.gz" "*.zip"
    git ls-files "nginx/ssl/*.pem"
) | Where-Object { $_ -and $_.Trim().Length -gt 0 } | Sort-Object -Unique

Write-Host "Arquivos proibidos rastreados: $($forbiddenTracked.Count)"
if ($forbiddenTracked.Count -gt 0) {
    $forbiddenTracked | Select-Object -First 20 | ForEach-Object { Write-Host "  $_" -ForegroundColor Yellow }
    Fail 'Ha arquivos locais/temporarios rastreados no Git. Corrija antes de continuar.'
}

Write-Section '3) Alembic heads'
$heads = Get-AlembicHeads
Write-Host "Heads detectadas: $($heads.Count)"
if ($heads.Count -gt 1) {
    $heads | ForEach-Object { Write-Host "  $_" -ForegroundColor Yellow }
    Fail 'Multiplas heads de migration detectadas. Unifique antes de subir producao.'
}

Write-Section 'Resultado'
Write-Host 'OK: Fluxo validado. Repositorio limpo para seguir trilho unico DEV -> PROD.' -ForegroundColor Green
exit 0
