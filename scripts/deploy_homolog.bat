@echo off
chcp 65001 >nul
echo ============================================
echo   DEPLOY PARA HOMOLOGAÇÃO
echo ============================================
echo.

REM Verificar se está no branch certo
for /f "tokens=*" %%b in ('git rev-parse --abbrev-ref HEAD') do set BRANCH=%%b
echo Branch atual: %BRANCH%

IF "%BRANCH%"=="main" (
    echo.
    echo [AVISO] Você está na main. O deploy de homolog vai para o branch 'homolog'.
    echo Isso nao afeta a producao.
    echo.
)

REM Criar branch homolog se nao existir
git show-ref --verify --quiet refs/heads/homolog
IF %ERRORLEVEL% NEQ 0 (
    echo Criando branch homolog a partir da main...
    git checkout main
    git pull origin main
    git checkout -b homolog
    echo Branch homolog criado!
) ELSE (
    echo Branch homolog ja existe.
)

REM Atualizar homolog com as mudancas da main
echo.
echo Atualizando homolog com a main...
git checkout homolog
git merge main --no-edit
IF %ERRORLEVEL% NEQ 0 (
    echo [ERRO] Conflito ao fazer merge. Resolva manualmente.
    pause
    exit /b 1
)

REM Push para o remote
echo.
echo Enviando branch homolog para o GitHub...
git push origin homolog
IF %ERRORLEVEL% NEQ 0 (
    echo [ERRO] Falha no push. Verifique suas credenciais.
    pause
    exit /b 1
)

REM Voltar para main
git checkout %BRANCH%

echo.
echo ============================================
echo  FEITO! Branch homolog atualizado.
echo.
echo  O Render vai detectar o push automaticamente
echo  e iniciar o deploy de homologacao.
echo.
echo  URLs (apos o deploy terminar):
echo  Frontend: https://automacao-admissao-frontend-homolog.onrender.com
echo  Backend:  https://automacao-admissao-backend-homolog.onrender.com
echo ============================================
pause
