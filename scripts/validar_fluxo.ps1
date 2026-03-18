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
            $revMatch = [regex]::Match($content, 'revision\s*:\s*[^=]+\s*=\s*"([^"]+)"')
        }
        if (-not $revMatch.Success) {
            $revMatch = [regex]::Match($content, "revision\s*=\s*'([^']+)'")
        }
        if (-not $revMatch.Success) {
            $revMatch = [regex]::Match($content, 'revision\s*=\s*"([^"]+)"')
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
            $matchesSingle = [regex]::Matches($downRaw, "'([^']+)'")
            foreach ($m in $matchesSingle) {
                [void]$downRevisionSet.Add($m.Groups[1].Value)
            }

            $matchesDouble = [regex]::Matches($downRaw, '"([^"]+)"')
            foreach ($m in $matchesDouble) {
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

function Get-DistAssetReferences {
    $indexPath = Join-Path $root 'frontend/dist/index.html'
    if (-not (Test-Path $indexPath)) {
        return @()
    }

    $content = Get-Content -Path $indexPath -Raw
    $matches = [regex]::Matches($content, '"/assets/([^"\?]+)')

    $assets = @()
    foreach ($m in $matches) {
        $assets += $m.Groups[1].Value
    }

    return $assets | Sort-Object -Unique
}

function Get-AllDistAssetReferences {
    $distPath = Join-Path $root 'frontend/dist'
    if (-not (Test-Path $distPath)) {
        return @()
    }

    $assetPattern = '/assets/([^"''\s\)\(\?]+(?:\?[^"''\s\)\(]*)?)'
    $assets = [System.Collections.Generic.HashSet[string]]::new()
    $visitedFiles = [System.Collections.Generic.HashSet[string]]::new()
    $pending = [System.Collections.Generic.Queue[string]]::new()

    $pending.Enqueue('frontend/dist/index.html')

    while ($pending.Count -gt 0) {
        $fileRelative = $pending.Dequeue()
        if (-not $visitedFiles.Add($fileRelative)) {
            continue
        }

        $filePath = Join-Path $root $fileRelative
        if (-not (Test-Path $filePath)) {
            continue
        }

        $content = Get-Content -Path $filePath -Raw
        $matches = [regex]::Matches($content, $assetPattern)

        foreach ($m in $matches) {
            $assetWithQuery = $m.Groups[1].Value
            if (-not $assetWithQuery) {
                continue
            }

            $asset = $assetWithQuery.Split('?')[0]
            if (-not $asset) {
                continue
            }

            [void]$assets.Add($asset)

            if ($asset.EndsWith('.js') -or $asset.EndsWith('.css')) {
                $nextRelative = "frontend/dist/assets/$asset"
                if (-not $visitedFiles.Contains($nextRelative)) {
                    $pending.Enqueue($nextRelative)
                }
            }
        }
    }

    return @($assets | Sort-Object)
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

Write-Section '4) Integridade do frontend dist/assets'
$assetRefs = Get-AllDistAssetReferences
Write-Host "Assets referenciados (index + imports dinamicos): $($assetRefs.Count)"
if ($assetRefs.Count -gt 0) {
    $missingAssets = @()

    foreach ($asset in $assetRefs) {
        $relativePath = "frontend/dist/assets/$asset"
        $fullPath = Join-Path $root $relativePath

        $trackedOutput = @(git ls-files -- $relativePath)
        $tracked = ''
        if ($trackedOutput.Count -gt 0) {
            $tracked = ($trackedOutput -join "`n").Trim()
        }

        if (-not $tracked -or -not (Test-Path $fullPath)) {
            $missingAssets += $relativePath
        }
    }

    if ($missingAssets.Count -gt 0) {
        Write-Host 'Assets faltando/rastreados incorretamente:' -ForegroundColor Yellow
        $missingAssets | Select-Object -First 80 | ForEach-Object { Write-Host "  $_" -ForegroundColor Yellow }
        if ($missingAssets.Count -gt 80) {
            Write-Host "  ... +$($missingAssets.Count - 80) assets" -ForegroundColor Yellow
        }
        Fail 'dist/index.html referencia assets ausentes no Git. Rode build e inclua frontend/dist/assets no commit.'
    }
}

$distAssetsPath = Join-Path $root 'frontend/dist/assets'
if (Test-Path $distAssetsPath) {
    $trackedAssets = @(git ls-files "frontend/dist/assets") | Where-Object { $_ -and $_.Trim().Length -gt 0 }
    $localAssets = @(Get-ChildItem -Path $distAssetsPath -File | ForEach-Object { "frontend/dist/assets/$($_.Name)" })

    $onlyLocalAssets = @($localAssets | Where-Object { $trackedAssets -notcontains $_ } | Sort-Object -Unique)
    Write-Host "Assets locais nao rastreados: $($onlyLocalAssets.Count)"

    if ($onlyLocalAssets.Count -gt 0) {
        Write-Host 'Exemplos de assets locais faltando no Git:' -ForegroundColor Yellow
        $onlyLocalAssets | Select-Object -First 80 | ForEach-Object { Write-Host "  $_" -ForegroundColor Yellow }
        if ($onlyLocalAssets.Count -gt 80) {
            Write-Host "  ... +$($onlyLocalAssets.Count - 80) assets" -ForegroundColor Yellow
        }

        Fail 'Existem arquivos em frontend/dist/assets que nao estao versionados. Rode build e inclua o dist completo no commit.'
    }
}

Write-Section 'Resultado'
Write-Host 'OK: Fluxo validado. Repositorio limpo para seguir trilho unico DEV -> PROD.' -ForegroundColor Green
exit 0
