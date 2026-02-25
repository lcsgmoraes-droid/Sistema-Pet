param(
    [ValidateSet('bloco1','bloco2','bloco3')]
    [string]$Bloco
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $root

function Stage-Bloco1 {
    git restore --staged .
    git add .gitignore
    git add -u backups
    Write-Host 'Bloco 1 preparado: higiene (backups + .gitignore).'
}

function Stage-Bloco2 {
    git restore --staged .
    git add .github/assistant-rules.json
    git add .github/copilot-instructions.md
    git add .vscode/tasks.json
    git add FLUXO_UNICO.bat
    git add scripts/fluxo_unico.ps1
    git add scripts/validar_fluxo.ps1
    git add docs/FLUXO_UNICO_DEV_PROD.md
    git add docs/PLANO_COMMIT_FLUXO_UNICO.md
    git add README.md
    Write-Host 'Bloco 2 preparado: fluxo unico operacional.'
}

function Stage-Bloco3 {
    git restore --staged .
    git add backend/alembic/versions/f6c9a1b2d3e4_merge_heads_a8f3_e1a2.py
    Write-Host 'Bloco 3 preparado: merge de migrations.'
}

switch ($Bloco) {
    'bloco1' { Stage-Bloco1 }
    'bloco2' { Stage-Bloco2 }
    'bloco3' { Stage-Bloco3 }
}

$staged = @(git diff --cached --name-only)
Write-Host ('Arquivos staged neste bloco: ' + $staged.Count)
