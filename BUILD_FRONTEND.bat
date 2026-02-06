@echo off
chcp 65001 > nul
color 0A
cls

REM ═══════════════════════════════════════════════════════════════
REM  INSTRUÇÕES DE USO:
REM  
REM  OPÇÃO 1: Use BUILD_FRONTEND.local.bat (arquivo com suas chaves)
REM  - Copie suas chaves reais no BUILD_FRONTEND.local.bat
REM  - Este arquivo está no .gitignore e não será commitado
REM  
REM  OPÇÃO 2: Configure as variáveis de ambiente no sistema
REM  - Defina REACT_APP_SUPABASE_URL
REM  - Defina REACT_APP_SUPABASE_ANON_KEY
REM  - Defina REACT_APP_SUPABASE_SERVICE_KEY
REM  
REM  OPÇÃO 3: Use arquivo .env.production na raiz do projeto
REM ═══════════════════════════════════════════════════════════════

echo.
echo ╔═══════════════════════════════════════════════════════════════╗
echo ║        BUILD COMPLETO COM VARIÁVEIS DE AMBIENTE              ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.

REM Definir variáveis de ambiente para o build
echo [1/4] Configurando variáveis de ambiente...
REM IMPORTANTE: Configure suas chaves no arquivo .env.local ou .env.production
REM OU defina as variáveis abaixo (não commitar este arquivo com chaves reais!)
if not defined REACT_APP_SUPABASE_URL (
    echo ⚠️  AVISO: REACT_APP_SUPABASE_URL não definida
    set REACT_APP_SUPABASE_URL=CONFIGURE_NO_ENV_OU_AQUI
)
if not defined REACT_APP_SUPABASE_ANON_KEY (
    echo ⚠️  AVISO: REACT_APP_SUPABASE_ANON_KEY não definida
    set REACT_APP_SUPABASE_ANON_KEY=CONFIGURE_NO_ENV_OU_AQUI
)
if not defined REACT_APP_SUPABASE_SERVICE_KEY (
    echo ⚠️  AVISO: REACT_APP_SUPABASE_SERVICE_KEY não definida
    set REACT_APP_SUPABASE_SERVICE_KEY=CONFIGURE_NO_ENV_OU_AQUI
)
echo       ✓ Variáveis configuradas
echo.

REM Limpar build anterior
echo [2/4] Limpando build anterior...
if exist "%~dp0build" (
    rmdir /s /q "%~dp0build" 2>nul
    echo       ✓ Build anterior removido
) else (
    echo       ℹ Nenhum build anterior encontrado
)
echo.

REM Executar build
echo [3/4] Executando npm run build...
echo       (Isso pode levar 30-60 segundos)
echo.
cd /d "%~dp0"
call npm run build
echo.

if errorlevel 1 (
    color 0C
    echo.
    echo ✗ ERRO NO BUILD!
    echo   Verifique os erros acima
    pause
    exit /b 1
)

echo       ✓ Build concluído com sucesso!
echo.

REM Matar processos do frontend
echo [4/4] Reiniciando servidor frontend...
taskkill /F /IM node.exe /FI "WINDOWTITLE eq Frontend*" 2>nul
timeout /t 2 /nobreak > nul

REM Iniciar servidor
cd /d "%~dp0build"
start "Frontend React (Porta 3000)" cmd /k "npx serve -s . -l 3000"
timeout /t 3 /nobreak > nul
echo       ✓ Servidor iniciado na porta 3000
echo.

echo ╔═══════════════════════════════════════════════════════════════╗
echo ║                    BUILD FINALIZADO!                         ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.
echo  Frontend disponível em: http://localhost:3000
echo.
echo  Abrindo navegador em 3 segundos...
timeout /t 3 /nobreak > nul

start http://localhost:3000

echo.
echo Pressione qualquer tecla para fechar...
pause > nul
