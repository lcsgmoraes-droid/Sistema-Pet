param(
    [string]$Dominio = "corepet.com.br",
    [string]$ChaveSsh = "$env:USERPROFILE\.ssh\mlprohub_codex_deploy"
)

# COMPATIBILITY_ALIAS
# Atalho historico do Windows. O launcher remoto oficial concentra validacao de
# destino, usuario e chave SSH.

$ErrorActionPreference = "Stop"
$launcher = Join-Path $PSScriptRoot "scripts\deploy_producao_remoto.ps1"

Write-Host "Atalho antigo detectado: encaminhando para o deploy remoto oficial."
& $launcher -Dominio $Dominio -ChaveSsh $ChaveSsh
