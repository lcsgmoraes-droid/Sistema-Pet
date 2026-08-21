param(
    [string]$Dominio = "corepet.com.br"
)

# COMPATIBILITY_ALIAS
# A correcao automatica antiga foi desativada. Este nome agora executa somente
# o diagnostico publico, sem SSH, deploy ou alteracao de arquivos.

$ErrorActionPreference = "Stop"
$diagnostico = Join-Path $PSScriptRoot "scripts\diagnosticar_producao_publica.py"

Write-Host "Atalho antigo detectado: executando diagnostico somente leitura."
& python $diagnostico --domain $Dominio
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
