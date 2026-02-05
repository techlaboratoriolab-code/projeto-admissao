@echo off
REM ========================================
REM    CRIAR PRIMEIRO ADMINISTRADOR
REM ========================================

echo.
echo ======================================
echo    CRIAR PRIMEIRO ADMINISTRADOR
echo ======================================
echo.

echo Este script ira ajudar voce a criar o primeiro admin do sistema.
echo.

echo OPCAO 1: Promover usuario existente
echo   - Ja tem um usuario cadastrado? 
echo   - Vamos promove-lo a administrador!
echo.

echo OPCAO 2: Criar novo usuario admin
echo   - Ainda nao tem usuarios?
echo   - Vamos criar um novo diretamente!
echo.

echo ----------------------------------------
echo  Escolha uma opcao:
echo ----------------------------------------
echo.
echo  [1] Promover usuario existente
echo  [2] Criar novo usuario admin
echo  [3] Abrir SQL Editor do Supabase
echo  [0] Cancelar
echo.

set /p opcao="Digite o numero da opcao: "

if "%opcao%"=="1" goto promover
if "%opcao%"=="2" goto criar
if "%opcao%"=="3" goto sql
if "%opcao%"=="0" goto fim

:promover
echo.
echo ========================================
echo  PROMOVER USUARIO EXISTENTE
echo ========================================
echo.
echo Abra o SQL Editor no Supabase e execute:
echo.
echo UPDATE auth.users
echo SET raw_user_meta_data = jsonb_set(
echo   COALESCE(raw_user_meta_data, '{}'::jsonb),
echo   '{role}',
echo   '"admin"'
echo )
echo WHERE email = 'seu@email.com';
echo.
echo Nao esqueca de substituir 'seu@email.com' pelo email do usuario!
echo.
start https://supabase.com/dashboard/project/vwcfgbjuayeugcqrpbma/editor
goto fim

:criar
echo.
echo ========================================
echo  CRIAR NOVO USUARIO ADMIN
echo ========================================
echo.
echo 1. Acesse: http://localhost:3000/login
echo 2. Clique em "Criar conta"
echo 3. Preencha os dados do novo usuario
echo 4. Depois, execute a OPCAO 1 para promover a admin
echo.
start http://localhost:3000/login
goto fim

:sql
echo.
echo Abrindo SQL Editor do Supabase...
start https://supabase.com/dashboard/project/vwcfgbjuayeugcqrpbma/editor
goto fim

:fim
echo.
echo Arquivo promover_admin.sql esta disponivel na raiz do projeto!
echo.
pause
