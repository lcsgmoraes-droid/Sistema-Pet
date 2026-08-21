param(
    [string]$Dominio = "corepet.com.br"
)

# COMPATIBILITY_ALIAS
# O diagnostico antigo misturava verificacao e alteracao do ambiente. Este nome
# agora consulta somente endpoints publicos.

$ErrorActionPreference = "Stop"
$diagnostico = Join-Path $PSScriptRoot "scripts\diagnosticar_producao_publica.py"

Write-Host "Atalho antigo detectado: executando diagnostico somente leitura."
& python $diagnostico --domain $Dominio
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
