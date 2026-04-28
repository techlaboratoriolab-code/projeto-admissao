@echo off
chcp 65001 >nul
echo ========================================
echo   INICIANDO SISTEMA - ACESSO PUBLICO
echo ========================================
echo.

REM Fazer backup do config.js original se não existir
if not exist "%~dp0..\src\config.js.backup" (
    echo [!] Fazendo backup do config.js...
    copy "%~dp0..\src\config.js" "%~dp0..\src\config.js.backup" >nul
    echo [✓] Backup criado!
    echo.
)

echo [1/5] Configurando modo NGROK no config.js...
powershell -Command "$content = Get-Content '%~dp0..\src\config.js' -Raw; $content = $content -replace 'const USE_NGROK = false', 'const USE_NGROK = true' -replace 'const USE_NETWORK = true', 'const USE_NETWORK = false'; Set-Content '%~dp0..\src\config.js' -Value $content -NoNewline"
echo [✓] Modo NGROK ativado!
timeout /t 1 /nobreak >nul

echo [2/5] Gerando build de produção atualizado...
cd /d "%~dp0.."
call npm run build
if errorlevel 1 (
    echo.
    echo [ERRO] Falha ao gerar build!
    echo [!] Restaurando config.js original...
    copy "%~dp0..\src\config.js.backup" "%~dp0..\src\config.js" >nul
    pause
    exit /b 1
)
echo [✓] Build gerado com sucesso!
echo.

echo [3/5] Iniciando Backend na porta 5000...
start "Backend API (Porta 5000)" cmd /k "cd /d %~dp0.. && .venv\Scripts\activate && cd backend && python api_admissao.py"
timeout /t 3 /nobreak >nul

echo [4/5] Iniciando Frontend (Build Produção) na porta 3000...
start "Frontend (Porta 3000)" cmd /k "cd /d %~dp0.. && npx serve -s build -p 3000 -n"
timeout /t 3 /nobreak >nul

echo [5/5] Iniciando Ngrok com domínio fixo...
set "NGROK_EXE=%LOCALAPPDATA%\Microsoft\WinGet\Packages\Ngrok.Ngrok_Microsoft.Winget.Source_8wekyb3d8bbwe\ngrok.exe"
if exist "%NGROK_EXE%" (
    echo [✓] Usando ngrok do winget: %NGROK_EXE%

    if defined NGROK_AUTHTOKEN (
        echo [i] Configurando authtoken do ngrok via variavel de ambiente NGROK_AUTHTOKEN...
        "%NGROK_EXE%" config add-authtoken %NGROK_AUTHTOKEN% >nul 2>&1
    ) else (
        echo [!] NGROK_AUTHTOKEN nao definido. Se o tunel falhar com ERR_NGROK_4018, configure seu token.
    )

    start "Ngrok Tunnel" cmd /k ""%NGROK_EXE%" http --domain=automacaolab.ngrok.dev 5000"
) else (
    echo [!] Ngrok do winget não encontrado. Usando ngrok do PATH...

    if defined NGROK_AUTHTOKEN (
        echo [i] Configurando authtoken do ngrok via variavel de ambiente NGROK_AUTHTOKEN...
        ngrok config add-authtoken %NGROK_AUTHTOKEN% >nul 2>&1
    ) else (
        echo [!] NGROK_AUTHTOKEN nao definido. Se o tunel falhar com ERR_NGROK_4018, configure seu token.
    )

    start "Ngrok Tunnel" cmd /k "ngrok http --domain=automacaolab.ngrok.dev 5000"
)
timeout /t 2 /nobreak >nul

echo.
echo ========================================
echo   SISTEMA INICIADO COM SUCESSO!
echo ========================================
echo.
echo 📍 ACESSO LOCAL:
echo    Frontend: http://localhost:3000
echo    Backend:  http://localhost:5000
echo.
echo 🌐 ACESSO PÚBLICO (Internet):
echo    Backend:  https://automacaolab.ngrok.dev
echo    Frontend: http://localhost:3000
echo.
echo ⚠️  O frontend está configurado para usar NGROK
echo     (conecta automaticamente ao backend público)
echo.
echo 💡 COMPARTILHAR COM OUTRAS PESSOAS:
echo    1. Elas devem acessar: http://localhost:3000
echo       (se estiverem na mesma máquina)
echo
echo    2. OU compartilhe seu IP local:
echo       - Abra outro terminal e digite: ipconfig
echo       - Procure "Endereço IPv4" (ex: 192.168.1.100)
echo       - Compartilhe: http://[SEU_IP]:3000
echo.
echo 🔧 RESTAURAR CONFIGURAÇÃO ORIGINAL:
echo    - Execute: iniciar_sistema.bat
echo    - Ou restaure manualmente:
echo      copy src\config.js.backup src\config.js
echo.
echo ========================================
echo.
pause
