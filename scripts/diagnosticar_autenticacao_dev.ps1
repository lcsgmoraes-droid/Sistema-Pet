param(
    [string]$ApiBaseUrl = 'http://127.0.0.1:8000'
)

$ErrorActionPreference = 'Stop'
$baseUri = [Uri]$ApiBaseUrl

if ($baseUri.Host -notin @('127.0.0.1', 'localhost')) {
    throw 'Este diagnostico aceita somente o backend DEV local.'
}

function Get-HttpStatus([string]$Url) {
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 10
        return [int]$response.StatusCode
    }
    catch {
        if ($null -ne $_.Exception.Response) {
            return [int]$_.Exception.Response.StatusCode
        }
        throw
    }
}

$normalizedBase = $ApiBaseUrl.TrimEnd('/')
$healthStatus = Get-HttpStatus "$normalizedBase/api/health"
$protectedStatus = Get-HttpStatus "$normalizedBase/api/operadoras-cartao?apenas_ativas=true"

Write-Host "API DEV: HTTP $healthStatus" -ForegroundColor Cyan
Write-Host "Rota protegida sem login: HTTP $protectedStatus" -ForegroundColor Cyan

if ($healthStatus -ne 200) {
    throw 'A API DEV nao esta saudavel.'
}
if ($protectedStatus -notin @(401, 403)) {
    throw 'A rota protegida aceitou acesso sem login ou respondeu de forma inesperada.'
}

Write-Host 'Diagnostico de autenticacao DEV aprovado.' -ForegroundColor Green
