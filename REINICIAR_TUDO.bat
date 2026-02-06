@echo off
chcp 65001 > nul
color 0E
cls

echo.
echo ========================================================================
echo   REINICIANDO SISTEMA - CORREÇÃO APLICADA
echo ========================================================================
echo.
echo  Este script vai:
echo    1. Parar todos os processos Python e Node rodando
echo    2. Reiniciar o backend Flask na porta 5000
echo    3. Reiniciar o frontend React na porta 3000
echo.
echo ========================================================================
echo.

REM Matar processos antigos
echo [1/3] Parando processos antigos...
taskkill /F /IM python.exe 2>nul
taskkill /F /IM node.exe 2>nul
timeout /t 2 /nobreak > nul
echo       OK - Processos anteriores encerrados
echo.

REM Iniciar backend
echo [2/3] Iniciando backend Flask (porta 5000)...
cd /d "%~dp0backend"
start "Backend API (Porta 5000)" cmd /k "python api_admissao.py"
timeout /t 3 /nobreak > nul
echo       OK - Backend iniciado
echo.

REM Iniciar frontend
echo [3/3] Iniciando frontend React (porta 3000)...
cd /d "%~dp0"
start "Frontend React (Porta 3000)" cmd /k "cd build && npx serve -s . -l 3000"
timeout /t 2 /nobreak > nul
echo       OK - Frontend iniciado
echo.

echo ========================================================================
echo   SISTEMA REINICIADO COM SUCESSO!
echo ========================================================================
echo.
echo  Backend:  http://localhost:5000
echo  Frontend: http://localhost:3000
echo.
echo  Aguarde 5 segundos e o navegador será aberto...
echo ========================================================================
timeout /t 5 /nobreak > nul

start http://localhost:3000

echo.
echo Pressione qualquer tecla para fechar esta janela...
pause > nul
