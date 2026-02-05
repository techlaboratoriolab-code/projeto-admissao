@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

color 0A
cls

echo.
echo ================================================================================
echo.
echo             ██╗███╗   ██╗███████╗████████╗ █████╗ ██╗      █████╗ ██████╗
echo             ██║████╗  ██║██╔════╝╚══██╔══╝██╔══██╗██║     ██╔══██╗██╔══██╗
echo             ██║██╔██╗ ██║███████╗   ██║   ███████║██║     ███████║██████╔╝
echo             ██║██║╚██╗██║╚════██║   ██║   ██╔══██║██║     ██╔══██║██╔══██╗
echo             ██║██║ ╚████║███████║   ██║   ██║  ██║███████╗██║  ██║██║  ██║
echo             ╚═╝╚═╝  ╚═══╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝
echo.
echo                   INSTALADOR COMPLETO - SISTEMA DE ADMISSAO
echo                           Instala TUDO automaticamente
echo.
echo ================================================================================
echo.
timeout /t 2 >nul

:: ============================================================================
:: ETAPA 1: VERIFICAR PYTHON
:: ============================================================================
echo.
echo ================================================================================
echo ETAPA 1/6: VERIFICANDO PYTHON
echo ================================================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [X] Python NAO encontrado!
    echo.
    echo INSTALACAO NECESSARIA:
    echo   1. Baixe Python em: https://www.python.org/downloads/
    echo   2. Durante a instalacao, marque: "Add Python to PATH"
    echo   3. Apos instalar, feche e abra novamente este terminal
    echo   4. Execute este script novamente
    echo.
    pause
    exit /b 1
) else (
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do set python_ver=%%i
    echo [OK] !python_ver! encontrado!
)

timeout /t 1 >nul

:: ============================================================================
:: ETAPA 2: VERIFICAR NODE.JS
:: ============================================================================
echo.
echo ================================================================================
echo ETAPA 2/6: VERIFICANDO NODE.JS
echo ================================================================================
echo.

node --version >nul 2>&1
if errorlevel 1 (
    echo [X] Node.js NAO encontrado!
    echo.
    echo INSTALACAO NECESSARIA:
    echo   1. Baixe Node.js em: https://nodejs.org/
    echo   2. Instale a versao LTS (recomendada)
    echo   3. Apos instalar, feche e abra novamente este terminal
    echo   4. Execute este script novamente
    echo.
    pause
    exit /b 1
) else (
    for /f "tokens=*" %%i in ('node --version 2^>^&1') do set node_ver=%%i
    echo [OK] Node.js !node_ver! encontrado!
)

timeout /t 1 >nul

:: ============================================================================
:: ETAPA 3: INSTALAR DEPENDENCIAS DO PYTHON (BACKEND)
:: ============================================================================
echo.
echo ================================================================================
echo ETAPA 3/6: INSTALANDO DEPENDENCIAS DO BACKEND (Python)
echo ================================================================================
echo.

if not exist "backend\requirements.txt" (
    echo [X] Arquivo backend\requirements.txt nao encontrado!
    pause
    exit /b 1
)

echo [INFO] Atualizando pip...
python -m pip install --upgrade pip --quiet

echo [INFO] Instalando bibliotecas do Python...
echo.

cd backend

echo   [1/12] Flask...
pip install Flask==3.0.0 --quiet
if errorlevel 1 echo [ERRO] Falha ao instalar Flask

echo   [2/12] Flask-CORS...
pip install flask-cors==4.0.0 --quiet
if errorlevel 1 echo [ERRO] Falha ao instalar Flask-CORS

echo   [3/12] Requests...
pip install requests==2.31.0 --quiet
if errorlevel 1 echo [ERRO] Falha ao instalar Requests

echo   [4/12] MySQL Connector...
pip install mysql-connector-python==8.2.0 --quiet
if errorlevel 1 echo [ERRO] Falha ao instalar MySQL Connector

echo   [5/12] Boto3...
pip install boto3==1.29.0 --quiet
if errorlevel 1 echo [ERRO] Falha ao instalar Boto3

echo   [6/12] Python-dotenv...
pip install python-dotenv==1.0.0 --quiet
if errorlevel 1 echo [ERRO] Falha ao instalar Python-dotenv

echo   [7/12] Pillow...
pip install Pillow==10.1.0 --quiet
if errorlevel 1 echo [ERRO] Falha ao instalar Pillow

echo   [8/12] Google Cloud AI Platform...
pip install google-cloud-aiplatform --quiet
if errorlevel 1 echo [ERRO] Falha ao instalar Google Cloud AI Platform

echo   [9/12] Supabase...
pip install supabase --quiet
if errorlevel 1 echo [ERRO] Falha ao instalar Supabase

echo   [10/12] PyJWT (JWT para autenticacao)...
pip install PyJWT==2.8.0 --quiet
if errorlevel 1 echo [ERRO] Falha ao instalar PyJWT

echo   [11/12] Werkzeug (hashing de senhas)...
pip install Werkzeug==3.0.0 --quiet
if errorlevel 1 echo [ERRO] Falha ao instalar Werkzeug

echo   [12/12] Python-dateutil...
pip install python-dateutil --quiet
if errorlevel 1 echo [ERRO] Falha ao instalar Python-dateutil

cd ..

echo.
echo [OK] Dependencias do Python instaladas!

timeout /t 1 >nul

:: ============================================================================
:: ETAPA 4: INSTALAR DEPENDENCIAS DO NODE.JS (FRONTEND)
:: ============================================================================
echo.
echo ================================================================================
echo ETAPA 4/6: INSTALANDO DEPENDENCIAS DO FRONTEND (Node.js)
echo ================================================================================
echo.

if not exist "package.json" (
    echo [X] Arquivo package.json nao encontrado!
    pause
    exit /b 1
)

echo [INFO] Instalando dependencias do Node.js...
echo [INFO] Isso pode demorar alguns minutos...
echo.

npm install

if errorlevel 1 (
    echo.
    echo [X] Erro ao instalar dependencias do Node.js!
    pause
    exit /b 1
) else (
    echo.
    echo [OK] Dependencias do Node.js instaladas!
)

timeout /t 1 >nul

:: ============================================================================
:: ETAPA 5: CONFIGURAR ARQUIVO .ENV
:: ============================================================================
echo.
echo ================================================================================
echo ETAPA 5/6: CONFIGURANDO ARQUIVO .ENV
echo ================================================================================
echo.

if not exist "backend\.env" (
    if exist "backend\.env.example" (
        echo [INFO] Copiando .env.example para .env...
        copy "backend\.env.example" "backend\.env" >nul
        echo [OK] Arquivo .env criado!
        echo.
        echo [IMPORTANTE] Configure o arquivo backend\.env com suas credenciais:
        echo   - SUPABASE_URL
        echo   - SUPABASE_KEY
        echo   - JWT_SECRET_KEY
        echo.
    ) else (
        echo [!] Arquivo .env.example nao encontrado.
        echo [!] Crie manualmente o arquivo backend\.env
    )
) else (
    echo [OK] Arquivo .env ja existe!
)

timeout /t 1 >nul

:: ============================================================================
:: ETAPA 6: CONFIGURAR BANCO DE DADOS E USUARIO ADMIN
:: ============================================================================
echo.
echo ================================================================================
echo ETAPA 6/6: CONFIGURANDO BANCO DE DADOS E USUARIO ADMIN
echo ================================================================================
echo.

echo [INFO] Testando conexao com Supabase...
cd backend

if exist "testar_supabase_completo.py" (
    python testar_supabase_completo.py

    if errorlevel 1 (
        echo.
        echo [X] Falha na conexao com Supabase!
        echo [!] Configure o arquivo backend\.env com suas credenciais do Supabase
        cd ..
        pause
        exit /b 1
    )
) else (
    echo [!] Script de teste nao encontrado
)

echo.
echo [INFO] Resetando senha do usuario admin...
echo.

if exist "resetar_senha_admin.py" (
    python resetar_senha_admin.py

    if errorlevel 1 (
        echo [X] Erro ao resetar senha do admin
    )
) else (
    echo [!] Script resetar_senha_admin.py nao encontrado
)

cd ..

:: ============================================================================
:: CONCLUSAO
:: ============================================================================
cls
color 0A
echo.
echo ================================================================================
echo.
echo                    ███████╗██╗   ██╗ ██████╗███████╗███████╗███████╗ ██████╗
echo                    ██╔════╝██║   ██║██╔════╝██╔════╝██╔════╝██╔════╝██╔═══██╗
echo                    ███████╗██║   ██║██║     █████╗  ███████╗███████╗██║   ██║
echo                    ╚════██║██║   ██║██║     ██╔══╝  ╚════██║╚════██║██║   ██║
echo                    ███████║╚██████╔╝╚██████╗███████╗███████║███████║╚██████╔╝
echo                    ╚══════╝ ╚═════╝  ╚═════╝╚══════╝╚══════╝╚══════╝ ╚═════╝
echo.
echo                        INSTALACAO CONCLUIDA COM SUCESSO!
echo.
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
echo ╔════════════════════════════════════════════════════════════════════════════╗
echo ║                         COMO INICIAR O SISTEMA                             ║
echo ╠════════════════════════════════════════════════════════════════════════════╣
echo ║                                                                            ║
echo ║   OPCAO 1 - AUTOMATICO (Recomendado):                                     ║
echo ║   Execute: iniciar_sistema.bat                                            ║
echo ║                                                                            ║
echo ║   OPCAO 2 - MANUAL:                                                        ║
echo ║   Terminal 1: cd backend ^&^& python api_admissao.py                        ║
echo ║   Terminal 2: npm run dev                                                  ║
echo ║                                                                            ║
echo ║   Depois acesse: http://localhost:5173                                     ║
echo ║                                                                            ║
echo ╚════════════════════════════════════════════════════════════════════════════╝
echo.
echo.
echo ╔════════════════════════════════════════════════════════════════════════════╗
echo ║                         PROBLEMAS COM LOGIN?                               ║
echo ╠════════════════════════════════════════════════════════════════════════════╣
echo ║                                                                            ║
echo ║   Se nao conseguir fazer login, execute:                                   ║
echo ║   cd backend                                                               ║
echo ║   python resetar_senha_admin.py                                            ║
echo ║                                                                            ║
echo ║   Depois use: admin / admin123                                             ║
echo ║                                                                            ║
echo ╚════════════════════════════════════════════════════════════════════════════╝
echo.
echo.
echo [INFO] Pressione qualquer tecla para iniciar o sistema...
pause >nul

:: Iniciar o sistema automaticamente
start "Backend - API" cmd /k "cd backend && python api_admissao.py"
timeout /t 3 >nul
start "Frontend - React" cmd /k "npm run dev"

echo.
echo [OK] Sistema iniciando...
echo [OK] Aguarde as janelas abrirem
echo.
echo Acesse: http://localhost:5173
echo Login: admin / admin123
echo.

timeout /t 5 >nul
exit
