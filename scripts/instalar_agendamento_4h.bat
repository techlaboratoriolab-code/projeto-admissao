@echo off
chcp 65001 >nul
echo ============================================
echo   INSTALAR AGENDAMENTO 4H (ACORDA PC)
echo ============================================
echo.
echo Este script cria uma tarefa que:
echo  - Acorda o PC as 3:55h (se estiver em sleep)
echo  - Dispara o processamento automatico as 4:00h
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
echo # Aguarda Flask estar pronto e dispara o processamento das 4h
echo $maxTentativas = 10
echo $tentativa = 0
echo $flaskOk = $false
echo.
echo while ^($tentativa -lt $maxTentativas^) {
echo     try {
echo         $resp = Invoke-WebRequest -Uri "http://localhost:5000/api/health" -TimeoutSec 5 -UseBasicParsing
echo         if ^($resp.StatusCode -eq 200^) { $flaskOk = $true; break }
echo     } catch {}
echo     $tentativa++
echo     Start-Sleep -Seconds 30
echo }
echo.
echo if ^($flaskOk^) {
echo     Invoke-WebRequest -Uri "http://localhost:5000/api/scheduler/executar" -Method POST -TimeoutSec 10 -UseBasicParsing
echo     Write-Host "Job 4h disparado com sucesso"
echo } else {
echo     Write-Host "Flask nao respondeu apos $maxTentativas tentativas"
echo }
) > "%PS_SCRIPT%"
echo [OK] Script criado.

echo.
echo [1/2] Removendo tarefa antiga (se existir)...
schtasks /delete /tn "LaboratorioAdmissao_4h" /f >nul 2>&1

echo [2/2] Criando tarefa 4h (acorda PC + dispara job)...
schtasks /create ^
  /tn "LaboratorioAdmissao_4h" ^
  /tr "powershell.exe -NonInteractive -WindowStyle Hidden -File \"%PS_SCRIPT%\"" ^
  /sc weekly ^
  /d MON,TUE,WED,THU,FRI ^
  /st 04:00 ^
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
echo O PC vai acordar automaticamente as 4h
echo (seg-sex) e processar as requisicoes.
echo.
echo Para testar agora: POST http://localhost:5000/api/scheduler/executar
echo.
pause
exit /b 0

:resolve_path
set %1=%~f2
exit /b 0
