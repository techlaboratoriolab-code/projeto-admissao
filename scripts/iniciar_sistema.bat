@echo off
cls
echo ╔════════════════════════════════════════════════════════════╗
echo ║         SISTEMA DE ADMISSAO LAB - INICIALIZADOR            ║
echo ║            (Com Autenticação Supabase)                     ║
echo ╚════════════════════════════════════════════════════════════╝
echo.
echo [INFO] Verificando arquivos de configuração...

REM Restaurar config.js original se houver backup
if exist "%~dp0src\config.js.backup" (
    echo [!] Restaurando config.js original (modo LOCALHOST)...
    copy "%~dp0src\config.js.backup" "%~dp0src\config.js" >nul
    echo [✓] Config.js restaurado para modo LOCALHOST!
    echo.
)

if not exist "%~dp0.env" echo [AVISO] .env não encontrado - Configure Supabase!
if not exist "%~dp0backend\.env" echo [AVISO] backend\.env não encontrado!
echo.

REM Verificar se esta na pasta correta
if not exist "backend\api_admissao.py" (
    echo [ERRO] Arquivo backend\api_admissao.py nao encontrado!
    echo Por favor, execute este script na pasta raiz do projeto.
    echo.
    pause
    exit /b 1
)

echo [1/2] Iniciando Backend (Python/Flask)...
start "Backend - Flask API" cmd /k "cd /d "%~dp0" && .venv\Scripts\activate && cd backend && echo ====================================== && echo   Backend - http://localhost:5000 && echo ====================================== && echo. && python api_admissao.py"

echo      Aguardando backend inicializar...
timeout /t 5 /nobreak >nul

echo.
echo [2/2] Iniciando Frontend (React)...
start "Frontend - React App" cmd /k "cd /d "%~dp0" && echo ====================================== && echo   Frontend - http://localhost:3000 && echo ====================================== && echo. && npm start"

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║                  SISTEMA INICIADO!                         ║
echo ╚════════════════════════════════════════════════════════════╝
echo.
echo   Backend:  http://localhost:5000
echo   Frontend: http://localhost:3000
echo   Login:    http://localhost:3000/login
echo.
echo   AUTENTICACAO:
echo     - Sistema usa Supabase Auth
echo     - Gerencie usuarios em /usuarios (admin only)
echo     - Roles: admin, supervisor, usuario
echo.
echo   PRIMEIRO USO:
echo     1. Execute: criar_admin.bat
echo     2. Ou execute: promover_admin.sql no Supabase
echo     3. Acesse /login e entre como admin
echo     4. Gerencie usuarios em /usuarios
echo.
echo ════════════════════════════════════════════════════════════
echo.
echo Aguardando o React abrir automaticamente...
echo (Se nao abrir em 30 segundos, pressione qualquer tecla)
echo.
timeout /t 30 /nobreak >nul 2>nul

echo Abrindo navegador...
start http://localhost:3000

echo.
echo Sistema rodando!
echo Para parar, feche as janelas do Backend e Frontend.
echo.
pause
