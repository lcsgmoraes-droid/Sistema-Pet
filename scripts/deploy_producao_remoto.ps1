param(
    [string]$Dominio = "corepet.com.br",
    [string]$ChaveSsh = "$env:USERPROFILE\.ssh\mlprohub_codex_deploy"
)

$ErrorActionPreference = "Stop"

$enderecos = [System.Net.Dns]::GetHostAddresses($Dominio) |
    ForEach-Object { $_.IPAddressToString } |
    Sort-Object -Unique

if (-not $enderecos) {
    throw "Deploy bloqueado: o dominio $Dominio nao resolveu para nenhum IP."
}

Write-Host "Destino publico confirmado pelo DNS: $Dominio -> $($enderecos -join ', ')"
Write-Host "O servidor ainda validara novamente o dominio antes de alterar codigo ou banco."

& ssh -i $ChaveSsh -o IdentitiesOnly=yes -o BatchMode=yes `
    -o "HostKeyAlias=$($enderecos[0])" `
    "petdeploy@$Dominio" "sudo -n /usr/local/sbin/petshop-deploy-producao"

if ($LASTEXITCODE -ne 0) {
    throw "O deploy remoto falhou com codigo $LASTEXITCODE."
}
