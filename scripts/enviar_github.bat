xx'x    @echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo.
echo ╔════════════════════════════════════════════════════════╗
echo ║      🚀 ENVIAR PROJETO PARA O GITHUB                 ║
echo ╚════════════════════════════════════════════════════════╝
echo.

REM Ir para a raiz do projeto (script está em scripts\)
cd /d "%~dp0.."

set "REPO_URL=https://github.com/laboratoriolab/projeto-admissao"

echo 📁 Pasta atual: %CD%
echo 🔗 Repositório: %REPO_URL%
echo.

git rev-parse --is-inside-work-tree >nul 2>nul
if errorlevel 1 (
    echo [ERRO] Esta pasta nao e um repositorio Git.
    echo Execute primeiro: git init
    echo.
    pause
    exit /b 1
)

echo ════════════════════════════════════════════════════════
echo 🔍 PASSO 1: Verificando status atual...
echo ════════════════════════════════════════════════════════
git status
echo.

echo ════════════════════════════════════════════════════════
echo ⚠️  Revise arquivos sensiveis antes de enviar
echo ════════════════════════════════════════════════════════
echo.
set /p continuar="Deseja continuar com o envio? (s/n): "
if /i not "%continuar%"=="s" (
    echo.
    echo Operacao cancelada.
    pause
    exit /b 0
)

echo.
echo ════════════════════════════════════════════════════════
echo 🌐 PASSO 2: Configurando remote origin...
echo ════════════════════════════════════════════════════════
git remote get-url origin >nul 2>nul
if errorlevel 1 (
    git remote add origin %REPO_URL%
    echo ✅ Origin adicionado.
) else (
    git remote set-url origin %REPO_URL%
    echo ✅ Origin verificado/atualizado.
)

REM Limpar cache de credenciais (força nova autenticação se necessário)
REM git credential-manager delete https://github.com
echo.

echo ════════════════════════════════════════════════════════
echo 📦 PASSO 3: Adicionando alteracoes...
echo ════════════════════════════════════════════════════════
git add .
if errorlevel 1 (
    echo [ERRO] Falha no git add.
    pause
    exit /b 1
)
echo ✅ Alteracoes adicionadas.
echo.

echo ════════════════════════════════════════════════════════
echo 💾 PASSO 4: Criando commit (se necessario)...
echo ════════════════════════════════════════════════════════
set "MSG="
set /p MSG="Mensagem do commit (vazio = update): "
if "%MSG%"=="" set "MSG=update"

git diff --cached --quiet
if errorlevel 1 (
    git commit -m "%MSG%"
    if errorlevel 1 (
        echo [ERRO] Falha ao criar commit.
        pause
        exit /b 1
    )
    echo ✅ Commit criado.
) else (
    echo ℹ️ Nenhuma alteracao para commit.
)
echo.

echo ════════════════════════════════════════════════════════
echo 🚀 PASSO 5: Fazendo fetch do remoto...
echo ════════════════════════════════════════════════════════
git fetch origin main
if errorlevel 1 (
    echo [AVISO] Falha no fetch, continuando...
)
echo.

echo ════════════════════════════════════════════════════════
echo 📤 PASSO 6: Enviando para o GitHub (normal)...
echo ════════════════════════════════════════════════════════
for /f "delims=" %%b in ('git branch --show-current') do set "BRANCH=%%b"
if "%BRANCH%"=="" set "BRANCH=main"

echo.
echo [DEBUG] Branch local: %BRANCH%
echo [DEBUG] Verificando commits locais vs remotos...
echo.

REM Tentativa 1: push normal
git push origin %BRANCH% --verbose
if errorlevel 1 (
    echo.
    echo [AVISO] Push normal nao funcionou, tentando force-with-lease...
    echo.
    
    REM Tentativa 2: force-with-lease
    git push --force-with-lease origin %BRANCH% --verbose
    if errorlevel 1 (
        echo.
        echo [ERRO] Falha em ambas tentativas.
        echo.
        echo Debug: verificando remoto...
        git ls-remote origin %BRANCH%
        echo.
        echo Dicas:
        echo  - Verifique autenticacao no GitHub
        echo  - Verifique permissao de escrita no repositorio
        echo  - Verifique se a branch remota existe
        echo.
        pause
        exit /b 1
    )
)

echo.
echo ════════════════════════════════════════════════════════
echo ✅ SUCESSO! Envio concluido
echo ════════════════════════════════════════════════════════
echo.
echo 🔗 Repositorio: %REPO_URL%
echo 🌿 Branch: %BRANCH%
echo.
echo Verificando resultado...
git ls-remote origin %BRANCH%
echo.
echo ⏳ Nota: O GitHub pode levar alguns segundos para atualizar
echo Pressione Ctrl+F5 no navegador para limpar cache
echo.
pause
