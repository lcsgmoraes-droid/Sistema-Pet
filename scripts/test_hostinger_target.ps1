param(
    [Parameter(Mandatory = $true)]
    [string]$IpAddress
)

$ErrorActionPreference = "Stop"

$parsedAddress = $null
if (-not [System.Net.IPAddress]::TryParse($IpAddress, [ref]$parsedAddress)) {
    throw "IpAddress invalido: $IpAddress"
}
if ($parsedAddress.AddressFamily -ne [System.Net.Sockets.AddressFamily]::InterNetwork) {
    throw "Este teste de virada espera o IPv4 publico da VPS."
}

$curl = Get-Command curl.exe -ErrorAction SilentlyContinue
if (-not $curl) {
    throw "curl.exe nao encontrado."
}

$checks = @(
    @{ HostName = "corepet.com.br"; Path = "/health"; Expected = 200 },
    @{ HostName = "corepet.com.br"; Path = "/api/health"; Expected = 200 },
    @{ HostName = "corepet.com.br"; Path = "/login"; Expected = 200 },
    @{ HostName = "corepet.com.br"; Path = "/landing"; Expected = 200 },
    @{ HostName = "corepet.com.br"; Path = "/termos"; Expected = 200 },
    @{ HostName = "corepet.com.br"; Path = "/privacidade"; Expected = 200 },
    @{ HostName = "corepet.com.br"; Path = "/atacadaopetpp"; Expected = 200 },
    @{ HostName = "www.corepet.com.br"; Path = "/api/health"; Expected = 200 },
    @{ HostName = "img.corepet.com.br"; Path = "/"; Expected = 404 }
)

$failures = @()
$results = @()
foreach ($check in $checks) {
    $hostName = $check.HostName
    $url = "https://${hostName}$($check.Path)"
    $resolve = "${hostName}:443:${IpAddress}"
    $statusText = & $curl.Source `
        --silent `
        --show-error `
        --location `
        --max-time 20 `
        --resolve $resolve `
        --output NUL `
        --write-out "%{http_code}" `
        $url
    $exitCode = $LASTEXITCODE
    $status = 0
    [void][int]::TryParse(($statusText | Out-String).Trim(), [ref]$status)
    $ok = $exitCode -eq 0 -and $status -eq $check.Expected
    $results += [pscustomobject]@{
        Host = $hostName
        Path = $check.Path
        Expected = $check.Expected
        Actual = $status
        Result = if ($ok) { "OK" } else { "FALHOU" }
    }
    if (-not $ok) {
        $failures += "$url esperado=$($check.Expected) recebido=$status curl_exit=$exitCode"
    }
}

$results | Format-Table -AutoSize

if ($failures.Count -gt 0) {
    Write-Error ("Teste do alvo falhou:`n- " + ($failures -join "`n- "))
    exit 1
}

Write-Output "target_smoke_status=ok"
Write-Output "target_ip=$IpAddress"
