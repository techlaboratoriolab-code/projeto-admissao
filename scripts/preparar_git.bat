@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo.
echo ╔════════════════════════════════════════════════════════╗
echo ║      🚀 PREPARAR E ENVIAR PROJETO PARA O GITHUB       ║
echo ╚════════════════════════════════════════════════════════╝
echo.

REM Ir para a raiz do projeto (script está em scripts\)
cd /d "%~dp0.."

echo 📁 Pasta atual: %CD%
echo.

where git >nul 2>nul
if errorlevel 1 (
    echo [ERRO] Git não encontrado no PATH.
    echo Instale o Git e tente novamente.
    echo.
    pause
    exit /b 1
)

git rev-parse --is-inside-work-tree >nul 2>nul
if errorlevel 1 (
    echo [ERRO] Esta pasta não é um repositório Git.
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

echo ⚠️  Revise arquivos sensíveis antes de enviar.
echo.
set /p continuar="Deseja continuar? (s/n): "
if /i not "%continuar%"=="s" (
    echo.
    echo Operação cancelada.
    pause
    exit /b 0
)

echo.
echo ════════════════════════════════════════════════════════
echo 📦 PASSO 2: Adicionando alterações...
echo ════════════════════════════════════════════════════════
git add .
if errorlevel 1 (
    echo [ERRO] Falha no git add.
    pause
    exit /b 1
)
echo ✅ Alterações adicionadas.
echo.

echo ════════════════════════════════════════════════════════
echo 💾 PASSO 3: Criando commit...
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
    echo ℹ️ Nenhuma alteração para commit.
)
echo.

echo ════════════════════════════════════════════════════════
echo 🌐 PASSO 4: Configurando remote origin...
echo ════════════════════════════════════════════════════════
set "repo_url="
for /f "delims=" %%r in ('git remote get-url origin 2^>nul') do set "repo_url=%%r"

if "%repo_url%"=="" (
    set /p repo_url="URL do repositório GitHub (https://github.com/usuario/repo.git): "
    if "%repo_url%"=="" (
        echo [ERRO] URL não informada.
        pause
        exit /b 1
    )
    git remote add origin "%repo_url%"
    if errorlevel 1 (
        echo [ERRO] Falha ao adicionar remote origin.
        pause
        exit /b 1
    )
    echo ✅ Origin adicionado: %repo_url%
) else (
    echo ✅ Origin já configurado: %repo_url%
)
echo.

echo ════════════════════════════════════════════════════════
echo 🚀 PASSO 5: Enviando para o GitHub...
echo ════════════════════════════════════════════════════════
set "BRANCH="
for /f "delims=" %%b in ('git branch --show-current') do set "BRANCH=%%b"
if "%BRANCH%"=="" set "BRANCH=main"

git push -u origin %BRANCH%
if errorlevel 1 (
    echo.
    echo [ERRO] Falha no push.
    echo Dicas:
    echo  - Verifique autenticação do GitHub
    echo  - Verifique permissão de escrita
    echo  - Confirme se a branch remota correta é %BRANCH%
    echo.
    pause
    exit /b 1
)

echo.
echo ✅ Envio concluído com sucesso!
echo 🌿 Branch enviada: %BRANCH%
echo 🔗 Repositório: %repo_url%
echo.
pause
