@echo off
chcp 65001 >nul
cls
color 0E

echo.
echo ================================================================================
echo.
echo          ██████╗ ███████╗███████╗███████╗████████╗ █████╗ ██████╗
echo          ██╔══██╗██╔════╝██╔════╝██╔════╝╚══██╔══╝██╔══██╗██╔══██╗
echo          ██████╔╝█████╗  ███████╗█████╗     ██║   ███████║██████╔╝
echo          ██╔══██╗██╔══╝  ╚════██║██╔══╝     ██║   ██╔══██║██╔══██╗
echo          ██║  ██║███████╗███████║███████╗   ██║   ██║  ██║██║  ██║
echo          ╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝
echo.
echo                         RESETAR SENHA DO ADMIN
echo                    Sistema de Admissao - Primeiro Acesso
echo.
echo ================================================================================
echo.
echo.

echo [INFO] Este script vai resetar a senha do usuario admin
echo [INFO] Use este script se:
echo   - Voce esqueceu a senha
echo   - Nao consegue fazer login
echo   - E o primeiro acesso ao sistema
echo.
echo ================================================================================
echo.

timeout /t 2 >nul

:: Verificar se Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [X] ERRO: Python nao encontrado!
    echo.
    echo Por favor, instale o Python primeiro:
    echo https://www.python.org/downloads/
    echo.
    echo Ou execute: instalar_tudo.bat
    echo.
    pause
    exit /b 1
)

:: Verificar se o arquivo de reset existe
if not exist "backend\resetar_senha_admin.py" (
    echo.
    echo [X] ERRO: Script resetar_senha_admin.py nao encontrado!
    echo.
    echo Certifique-se de estar na pasta correta do projeto.
    echo.
    pause
    exit /b 1
)

:: Verificar se o .env existe
if not exist "backend\.env" (
    echo.
    echo [!] AVISO: Arquivo .env nao encontrado!
    echo.
    echo Configure o arquivo backend\.env antes de continuar.
    echo Se voce nao configurou ainda, execute: instalar_tudo.bat
    echo.
    pause
    exit /b 1
)

echo [INFO] Resetando senha do admin...
echo.

cd backend
python resetar_senha_admin.py

if errorlevel 1 (
    echo.
    echo ================================================================================
    echo [X] ERRO AO RESETAR SENHA
    echo ================================================================================
    echo.
    echo Possiveis problemas:
    echo   1. Arquivo .env nao configurado corretamente
    echo   2. Supabase nao acessivel
    echo   3. Tabela 'usuarios' nao existe no banco
    echo.
    echo Solucoes:
    echo   1. Configure o arquivo backend\.env com suas credenciais Supabase
    echo   2. Execute: instalar_tudo.bat para configurar tudo
    echo   3. Verifique a conexao com a internet
    echo.
    cd ..
    pause
    exit /b 1
)

cd ..

echo.
echo ================================================================================
echo [OK] SENHA RESETADA COM SUCESSO!
echo ================================================================================
echo.
echo.
echo ╔════════════════════════════════════════════════════════════════════════════╗
echo ║                         CREDENCIAIS DE ACESSO                              ║
echo ╠════════════════════════════════════════════════════════════════════════════╣
echo ║                                                                            ║
echo ║   Usuario: admin                                                           ║
echo ║   Senha:   admin123                                                        ║
echo ║                                                                            ║
echo ╚════════════════════════════════════════════════════════════════════════════╝
echo.
echo.
echo [INFO] Agora voce pode fazer login no sistema!
echo.
echo Para iniciar o sistema:
echo   1. Execute: iniciar_sistema.bat
echo   2. Acesse: http://localhost:5173
echo   3. Faca login com: admin / admin123
echo.
echo ================================================================================
echo.
pause
