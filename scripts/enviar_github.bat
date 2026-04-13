@echo off
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
    echo ✅ Origin atualizado.
)
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
echo 💾 PASSO 4: Criando commit...
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
echo 🚀 PASSO 5: Enviando para o GitHub...
echo ════════════════════════════════════════════════════════
for /f "delims=" %%b in ('git branch --show-current') do set "BRANCH=%%b"
if "%BRANCH%"=="" set "BRANCH=main"

echo Tentando push normal...
git push -u origin %BRANCH%
if errorlevel 1 (
    echo.
    echo [AVISO] Push normal falhou, tentando com --force-with-lease...
    git push --force-with-lease -u origin %BRANCH%
    if errorlevel 1 (
        echo.
        echo [ERRO] Falha no push mesmo com --force-with-lease.
        echo Dicas:
        echo  - Verifique login/autenticacao no GitHub
        echo  - Verifique permissao de escrita no repositorio
        echo  - Se a branch remota for outra, ajuste manualmente
        echo.
        pause
        exit /b 1
    )
)

echo.
echo ✅ Envio concluido com sucesso!
echo 🌿 Branch enviada: %BRANCH%
echo 🔗 %REPO_URL%
echo.
pause
