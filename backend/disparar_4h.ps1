# Aguarda Flask estar pronto e dispara o processamento das 4h
$maxTentativas = 10
$tentativa = 0
$flaskOk = $false

while ($tentativa -lt $maxTentativas) {
    try {
        $resp = Invoke-WebRequest -Uri "http://localhost:5000/api/health" -TimeoutSec 5 -UseBasicParsing
        if ($resp.StatusCode -eq 200) { $flaskOk = $true; break }
    } catch {}
    $tentativa++
    Start-Sleep -Seconds 30
}

if ($flaskOk) {
    Invoke-WebRequest -Uri "http://localhost:5000/api/scheduler/executar" -Method POST -TimeoutSec 10 -UseBasicParsing
    Write-Host "Job 4h disparado com sucesso"
} else {
    Write-Host "Flask nao respondeu apos $maxTentativas tentativas"
}
