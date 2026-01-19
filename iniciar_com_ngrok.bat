@echo off
chcp 65001 >nul
echo ========================================
echo   SISTEMA DE ADMISSAO - NGROK
echo ========================================
echo.

REM Verificar se Python esta instalado
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERRO] Python nao encontrado!
    pause
    exit /b 1
)

REM Verificar se ngrok esta instalado
where ngrok >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERRO] ngrok nao encontrado! Instale em: https://ngrok.com/download
    pause
    exit /b 1
)

REM Verificar se npm esta instalado
where npm >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERRO] npm nao encontrado!
    pause
    exit /b 1
)

echo [OK] Todas as verificacoes passaram!
echo.
echo Iniciando Backend Flask na porta 5000...
start "Backend Flask" cmd /k "cd /d "%~dp0backend" && python api_admissao.py"

echo Aguardando 5 segundos para o backend iniciar...
timeout /t 5 >nul

echo.
echo Iniciando ngrok na porta 5000 (Backend)...
start "Ngrok Backend" cmd /k "ngrok http 5000 --domain=automacaolab.ngrok.dev"

echo Aguardando 3 segundos...
timeout /t 3 >nul

echo.
echo Iniciando Frontend React na porta 3000...
start "Frontend React" cmd /k "cd /d "%~dp0" && npm start"

echo.
echo ========================================
echo   SISTEMA INICIADO COM NGROK!
echo ========================================
echo.
echo Backend Local: http://localhost:5000
echo Backend Ngrok: https://automacaolab.ngrok.dev
echo Frontend: http://localhost:3000
echo.
echo Pressione qualquer tecla para fechar esta janela...
pause >nul
