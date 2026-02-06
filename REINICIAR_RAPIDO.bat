@echo off
chcp 65001 > nul
color 0A
cls

echo.
echo ╔═══════════════════════════════════════════════════════════════╗
echo ║            🚀 REINÍCIO RÁPIDO - SISTEMA CORRIGIDO            ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.

REM 1. Matar processos
echo [1/4] Encerrando processos antigos...
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM node.exe >nul 2>&1
timeout /t 2 /nobreak >nul
echo       ✓ Processos encerrados
echo.

REM 2. Iniciar Backend
echo [2/4] Iniciando Backend (porta 5000)...
cd /d "%~dp0backend"
start "🔧 Backend API" cmd /k "color 0E && python api_admissao.py"
timeout /t 3 /nobreak >nul
echo       ✓ Backend rodando
echo.

REM 3. Iniciar Frontend
echo [3/4] Iniciando Frontend (porta 3000)...
cd /d "%~dp0build"
start "🌐 Frontend" cmd /k "color 0B && npx serve -s . -l 3000"
timeout /t 2 /nobreak >nul
echo       ✓ Frontend rodando
echo.

REM 4. Abrir navegador
echo [4/4] Abrindo navegador...
timeout /t 3 /nobreak >nul
start http://localhost:3000
echo       ✓ Navegador aberto
echo.

echo ╔═══════════════════════════════════════════════════════════════╗
echo ║                    ✓ SISTEMA PRONTO!                         ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.
echo   📍 Frontend:  http://localhost:3000
echo   📍 Backend:   http://localhost:5000
echo   📍 Público:   http://automacaolab.ngrok.dev
echo.
echo ⚠️  IMPORTANTE: Se der erro 429 (limite de requisições):
echo    → Aguarde 10-15 segundos entre buscas
echo    → O apLIS tem rate limiting ativo
echo.
echo Pressione qualquer tecla para fechar...
pause >nul
