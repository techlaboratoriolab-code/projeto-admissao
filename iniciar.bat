@echo off
chcp 65001 >nul
echo ========================================
echo   SISTEMA DE ADMISSAO - LAB
echo ========================================
echo.

REM Verificar se Python esta instalado
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERRO] Python nao encontrado! Instale o Python e adicione ao PATH.
    pause
    exit /b 1
)

REM Verificar se npm esta instalado
where npm >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERRO] npm nao encontrado! Instale o Node.js.
    pause
    exit /b 1
)

REM Verificar se a pasta backend existe
if not exist "backend" (
    echo [ERRO] Pasta 'backend' nao encontrada!
    pause
    exit /b 1
)

REM Verificar se api_admissao.py existe
if not exist "backend\api_admissao.py" (
    echo [ERRO] Arquivo 'backend\api_admissao.py' nao encontrado!
    pause
    exit /b 1
)

REM Verificar se package.json existe
if not exist "package.json" (
    echo [ERRO] Arquivo 'package.json' nao encontrado!
    pause
    exit /b 1
)

echo [OK] Todas as verificacoes passaram!
echo.
echo Iniciando Backend Flask...
start "Backend Flask" cmd /k "cd /d "%~dp0backend" && python api_admissao.py"

echo Aguardando 3 segundos...
timeout /t 3 >nul

echo.
echo Iniciando Frontend React...
start "Frontend React" cmd /k "cd /d "%~dp0" && npm start"

echo.
echo ========================================
echo   SISTEMA INICIADO!
echo ========================================
echo.
echo Backend: http://localhost:5000
echo Frontend: http://localhost:3000
echo.
echo Pressione qualquer tecla para fechar esta janela...
pause >nul
