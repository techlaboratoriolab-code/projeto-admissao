# Aguarda Flask estar pronto e dispara o processamento das 4h30
$logFile = Join-Path $PSScriptRoot "logs\scheduler_4h.log"
New-Item -ItemType Directory -Path (Split-Path $logFile) -Force | Out-Null
function Log { param([string]$msg) $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"; Add-Content -Path $logFile -Value "[$ts] $msg" }
Log "=== Disparo agendado iniciado ==="
$maxTentativas = 10
$tentativa = 0
$flaskOk = $false

while ($tentativa -lt $maxTentativas) {
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:5000/api/health" -TimeoutSec 5 -UseBasicParsing
        if ($resp.StatusCode -eq 200) { $flaskOk = $true; Log "Health OK"; break }
    } catch { Log "Health tentativa $($tentativa + 1) falhou: $($_.Exception.Message)" }
    $tentativa++
    Start-Sleep -Seconds 30
}

if ($flaskOk) {
    try {
        $triggerResp = Invoke-WebRequest -Uri "http://127.0.0.1:5000/api/scheduler/executar" -Method POST -TimeoutSec 300 -UseBasicParsing
        Log "Trigger enviado com sucesso. StatusCode=$($triggerResp.StatusCode)"
        Write-Host "Job 4h30 disparado com sucesso"
        exit 0
    } catch {
        Log "Erro ao chamar endpoint de trigger: $($_.Exception.Message)"
        Write-Host "Falha ao disparar endpoint /api/scheduler/executar"
        exit 1
    }
} else {
    Log "Flask nao respondeu apos $maxTentativas tentativas"
    Write-Host "Flask nao respondeu apos $maxTentativas tentativas"
    exit 2
}
