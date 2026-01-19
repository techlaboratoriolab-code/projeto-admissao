@echo off
echo ========================================
echo INSTALANDO DEPENDENCIAS DO PROJETO
echo ========================================
echo.

REM Verificar se Python esta instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado! Instale o Python primeiro.
    echo Baixe em: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [OK] Python encontrado!
echo.

REM Atualizar pip
echo [1/2] Atualizando pip...
python -m pip install --upgrade pip
echo.

REM Instalar dependencias do requirements.txt
echo [2/2] Instalando bibliotecas do projeto...
pip install Flask==3.0.0
pip install flask-cors==4.0.0
pip install requests==2.31.0
pip install mysql-connector-python==8.2.0
pip install boto3==1.29.0
pip install python-dotenv==1.0.0
pip install Pillow==10.1.0
pip install google-cloud-aiplatform

echo.
echo ========================================
echo INSTALACAO CONCLUIDA COM SUCESSO!
echo ========================================
echo.
echo Todas as bibliotecas foram instaladas.
echo Agora voce pode executar o projeto normalmente.
echo.
pause
