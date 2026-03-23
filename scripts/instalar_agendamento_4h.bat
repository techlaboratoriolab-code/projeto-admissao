@echo off
chcp 65001 >nul
echo ============================================
echo   INSTALAR AGENDAMENTO 4H (ACORDA PC)
echo ============================================
echo.
echo Este script cria uma tarefa que:
echo  - Acorda o PC as 4:25h (se estiver em sleep)
echo  - Dispara o processamento automatico as 4:30h
echo  - (imagens chegam no S3 a partir das 3:30h - margem de 60 min)
echo.

net session >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Execute como ADMINISTRADOR!
    pause
    exit /b 1
)

set "PS_SCRIPT=%~dp0..\backend\disparar_4h.ps1"
call :resolve_path PS_SCRIPT "%PS_SCRIPT%"

REM Criar o script PowerShell que chama o endpoint Flask
echo Criando script PowerShell...
(
echo # Aguarda Flask estar pronto e dispara o processamento das 4h30
echo $logFile = Join-Path $PSScriptRoot "logs\scheduler_4h.log"
echo New-Item -ItemType Directory -Path ^(Split-Path $logFile^) -Force ^| Out-Null
echo function Log ^{ param^([string]$msg^) $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"; Add-Content -Path $logFile -Value "[$ts] $msg" ^}
echo Log "=== Disparo agendado iniciado ==="
echo $maxTentativas = 10
echo $tentativa = 0
echo $flaskOk = $false
echo.
echo while ^($tentativa -lt $maxTentativas^) {
echo     try {
echo         $resp = Invoke-WebRequest -Uri "http://127.0.0.1:5000/api/health" -TimeoutSec 5 -UseBasicParsing
echo         if ^($resp.StatusCode -eq 200^) { $flaskOk = $true; Log "Health OK"; break }
echo     } catch { Log "Health tentativa $($tentativa + 1) falhou: $($_.Exception.Message)" }
echo     $tentativa++
echo     Start-Sleep -Seconds 30
echo }
echo.
echo if ^($flaskOk^) {
echo     try {
echo         $triggerResp = Invoke-WebRequest -Uri "http://127.0.0.1:5000/api/scheduler/executar" -Method POST -TimeoutSec 300 -UseBasicParsing
echo         Log "Trigger enviado com sucesso. StatusCode=$($triggerResp.StatusCode)"
echo         Write-Host "Job 4h30 disparado com sucesso"
echo         exit 0
echo     } catch {
echo         Log "Erro ao chamar endpoint de trigger: $($_.Exception.Message)"
echo         Write-Host "Falha ao disparar endpoint /api/scheduler/executar"
echo         exit 1
echo     }
echo } else {
echo     Log "Flask nao respondeu apos $maxTentativas tentativas"
echo     Write-Host "Flask nao respondeu apos $maxTentativas tentativas"
echo     exit 2
echo }
) > "%PS_SCRIPT%"
echo [OK] Script criado.

echo.
echo [1/2] Removendo tarefa antiga (se existir)...
schtasks /delete /tn "LaboratorioAdmissao_4h" /f >nul 2>&1

echo [2/2] Criando tarefa 4h30 (acorda PC + dispara job, roda como SYSTEM)...
schtasks /create ^
  /tn "LaboratorioAdmissao_4h" ^
  /tr "powershell.exe -NoProfile -ExecutionPolicy Bypass -NonInteractive -WindowStyle Hidden -File \"%PS_SCRIPT%\"" ^
  /sc weekly ^
  /d MON,TUE,WED,THU,FRI ^
  /st 04:30 ^
  /ru SYSTEM ^
  /rl HIGHEST ^
  /f

if errorlevel 1 (
    echo [ERRO] Falha ao criar tarefa!
    pause
    exit /b 1
)

REM Habilitar wake para esta tarefa (acorda o PC do sleep)
powershell -Command "& { $task = Get-ScheduledTask -TaskName 'LaboratorioAdmissao_4h'; $settings = $task.Settings; $settings.WakeToRun = $true; Set-ScheduledTask -TaskName 'LaboratorioAdmissao_4h' -Settings $settings }" >nul 2>&1

echo.
echo ============================================
echo   AGENDAMENTO 4H INSTALADO!
echo ============================================
echo.
echo O PC vai acordar automaticamente as 4h30
echo (seg-sex) e processar as requisicoes.
echo Margem de 60 min apos imagens chegarem no S3 (3h30).
echo Log de execucao: backend\logs\scheduler_4h.log
echo.
echo Para testar agora: POST http://localhost:5000/api/scheduler/executar
echo.
pause
exit /b 0

:resolve_path
set %1=%~f2
exit /b 0
