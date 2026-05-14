param(
    [bool]$InstalarExtensoesVSCode = $true,
    [bool]$InstalarInspector = $true,
    [bool]$ConfigurarCodex = $true,
    [switch]$InstalarGitHubCli
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $root

function Write-Section([string]$text) {
    Write-Host "`n=== $text ===" -ForegroundColor Cyan
}

function Find-CodeCmd {
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA 'Programs\Microsoft VS Code\bin\code.cmd'),
        (Join-Path $env:ProgramFiles 'Microsoft VS Code\bin\code.cmd')
    )

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    $command = Get-Command code.cmd -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    return $null
}

function Install-McpServer([string]$serverPath) {
    Push-Location $serverPath
    try {
        if (-not (Test-Path '.venv\Scripts\python.exe')) {
            python -m venv .venv
        }

        .\.venv\Scripts\python.exe -m pip install --upgrade pip
        .\.venv\Scripts\python.exe -m pip install -e .
    }
    finally {
        Pop-Location
    }
}

Write-Section 'PowerShell para ferramentas Node'
try {
    Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force
    Write-Host ('ExecutionPolicy CurrentUser: ' + (Get-ExecutionPolicy -Scope CurrentUser))
}
catch {
    Write-Host 'Nao consegui alterar ExecutionPolicy. Continue se npm ja funcionar neste PC.' -ForegroundColor Yellow
}

Write-Section 'MCPs locais do Sistema Pet'
Install-McpServer -serverPath (Join-Path $root 'mcp\frontend_react_server')
Install-McpServer -serverPath (Join-Path $root 'mcp\ops_api_server')

if ($InstalarInspector) {
    Write-Section 'MCP Inspector'
    $npmCmd = Join-Path $env:ProgramFiles 'nodejs\npm.cmd'
    if (Test-Path $npmCmd) {
        & $npmCmd install -g @modelcontextprotocol/inspector
    } else {
        Write-Host 'npm.cmd nao encontrado. Instale Node.js antes de instalar o MCP Inspector.' -ForegroundColor Yellow
    }
}

if ($InstalarExtensoesVSCode) {
    Write-Section 'Extensoes recomendadas do VS Code'
    $codeCmd = Find-CodeCmd
    $extensionsPath = Join-Path $root '.vscode\extensions.json'

    if ($codeCmd -and (Test-Path $extensionsPath)) {
        $json = Get-Content $extensionsPath -Raw | ConvertFrom-Json
        foreach ($extension in $json.recommendations) {
            Write-Host "Instalando $extension..."
            & $codeCmd --install-extension $extension
        }
    } else {
        Write-Host 'VS Code CLI ou .vscode/extensions.json nao encontrado.' -ForegroundColor Yellow
    }
}

if ($InstalarGitHubCli) {
    Write-Section 'GitHub CLI'
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        winget install --id GitHub.cli --source winget --silent --accept-package-agreements --accept-source-agreements
    } else {
        Write-Host 'winget nao encontrado. Instale GitHub CLI manualmente se precisar.' -ForegroundColor Yellow
    }
}

if ($ConfigurarCodex) {
    Write-Section 'Codex MCP'
    $codex = Get-Command codex -ErrorAction SilentlyContinue
    if ($codex) {
        $frontPython = (Resolve-Path (Join-Path $root 'mcp\frontend_react_server\.venv\Scripts\python.exe')).Path
        $opsPython = (Resolve-Path (Join-Path $root 'mcp\ops_api_server\.venv\Scripts\python.exe')).Path

        codex mcp remove sistema-pet-frontend *> $null
        codex mcp remove sistema-pet-ops *> $null
        codex mcp add sistema-pet-frontend -- $frontPython -m frontend_react_mcp.main
        codex mcp add sistema-pet-ops -- $opsPython -m ops_api_mcp.main
        codex mcp list
    } else {
        Write-Host 'Codex CLI nao encontrado. Pulei configuracao global de MCP no Codex.' -ForegroundColor Yellow
    }
}

Write-Section 'Concluido'
Write-Host 'Setup local de MCP finalizado.' -ForegroundColor Green
