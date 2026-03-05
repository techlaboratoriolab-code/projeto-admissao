@echo off
chcp 65001 >nul
echo ========================================
echo   INSTALAR BACKEND COMO SERVICO WINDOWS
echo ========================================
echo.
echo Este script configura o backend Flask para iniciar
echo automaticamente toda vez que o Windows iniciar.
echo.

REM Verificar se esta rodando como administrador
net session >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Execute este script como ADMINISTRADOR!
    echo Clique com botao direito no .bat e escolha "Executar como administrador"
    pause
    exit /b 1
)

REM Pegar o caminho absoluto da pasta backend
set "VBS_PATH=%~dp0..\backend\iniciar_backend_oculto.vbs"
call :resolve_path VBS_PATH "%VBS_PATH%"

echo [1/3] Removendo tarefa antiga (se existir)...
schtasks /delete /tn "LaboratorioAdmissao_Backend" /f >nul 2>&1
echo [OK]

echo [2/3] Criando tarefa para iniciar com o Windows...
schtasks /create ^
  /tn "LaboratorioAdmissao_Backend" ^
  /tr "wscript.exe \"%VBS_PATH%\"" ^
  /sc onlogon ^
  /rl HIGHEST ^
  /delay 0001:30 ^
  /f

if errorlevel 1 (
    echo [ERRO] Falha ao criar tarefa agendada!
    pause
    exit /b 1
)

echo [3/3] Iniciando backend agora (primeira vez)...
wscript.exe "%VBS_PATH%"
timeout /t 5 /nobreak >nul

echo.
echo ========================================
echo   INSTALACAO CONCLUIDA COM SUCESSO!
echo ========================================
echo.
echo O backend Flask agora vai iniciar AUTOMATICAMENTE
echo toda vez que você fizer login no Windows.
echo.
echo Para verificar se está rodando, acesse:
echo   http://localhost:5000/api/health
echo.
echo Para DESINSTALAR, rode: desinstalar_servico.bat
echo.
pause
exit /b 0

:resolve_path
set %1=%~f2
exit /b 0
