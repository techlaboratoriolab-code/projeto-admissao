@echo off
chcp 65001 >nul
echo.
echo ╔════════════════════════════════════════════════════════╗
echo ║     🚀 PREPARAR PROJETO PARA O GIT                     ║
echo ╚════════════════════════════════════════════════════════╝
echo.

echo 📋 Este script irá preparar o projeto para o primeiro commit no Git
echo.
pause

echo.
echo ════════════════════════════════════════════════════════
echo 🔍 PASSO 1: Verificando status atual...
echo ════════════════════════════════════════════════════════
git status
echo.

echo.
echo ════════════════════════════════════════════════════════
echo ⚠️  ATENÇÃO: Verifique se há arquivos sensíveis acima!
echo ════════════════════════════════════════════════════════
echo.
echo Arquivos que NÃO devem ser commitados:
echo   - .env (variáveis de ambiente)
echo   - node_modules/ (dependências)
echo   - __pycache__/ (cache Python)
echo   - .venv/ (ambiente virtual)
echo   - build/ (build de produção)
echo   - logs/ (arquivos de log)
echo.

set /p continuar="Tudo certo? Deseja continuar? (s/n): "
if /i not "%continuar%"=="s" (
    echo.
    echo ❌ Operação cancelada!
    pause
    exit /b
)

echo.
echo ════════════════════════════════════════════════════════
echo 📦 PASSO 2: Adicionando arquivos ao Git...
echo ════════════════════════════════════════════════════════
git add .
echo ✅ Arquivos adicionados!
echo.

echo.
echo ════════════════════════════════════════════════════════
echo 💾 PASSO 3: Criando commit inicial...
echo ════════════════════════════════════════════════════════
git commit -m "feat: initial commit with complete documentation

- Complete React frontend with Tailwind CSS
- Flask backend with Supabase authentication
- Integration with apLIS system
- AWS S3 for documents
- Google Vertex AI for OCR
- Complete documentation (10 MD files)
- Installation, API, Deploy and Architecture guides
- Ready for production deployment"
echo.
echo ✅ Commit criado!
echo.

echo.
echo ════════════════════════════════════════════════════════
echo 🌐 PASSO 4: Conectando ao repositório remoto...
echo ════════════════════════════════════════════════════════
echo.
set /p repo_url="Digite a URL do repositório Git (ex: https://github.com/usuario/repo.git): "

if "%repo_url%"=="" (
    echo.
    echo ⚠️  URL não fornecida. Você pode adicionar depois com:
    echo    git remote add origin [URL]
    echo.
) else (
    git remote add origin %repo_url%
    echo ✅ Remote adicionado!
    echo.
    
    echo ════════════════════════════════════════════════════════
    echo 🚀 PASSO 5: Enviando para o GitHub...
    echo ════════════════════════════════════════════════════════
    git push -u origin main
    
    if errorlevel 1 (
        echo.
        echo ⚠️  Se der erro, pode ser porque a branch principal é 'master':
        echo    git push -u origin master
        echo.
    ) else (
        echo.
        echo ✅ Código enviado com sucesso!
        echo.
    )
)

echo.
echo ════════════════════════════════════════════════════════
echo ✅ PROCESSO CONCLUÍDO!
echo ════════════════════════════════════════════════════════
echo.
echo 📚 Documentação criada:
echo   - README.md (visão geral)
echo   - INSTALACAO.md (guia de instalação)
echo   - API.md (documentação da API)
echo   - DEPLOY.md (guia de deploy)
echo   - CONTRIBUTING.md (guia de contribuição)
echo   - ARCHITECTURE.md (arquitetura do sistema)
echo   - E mais 4 documentos!
echo.
echo 🎯 Próximos passos:
echo   1. Acesse o repositório no GitHub
echo   2. Configure as GitHub Actions (se necessário)
echo   3. Adicione colaboradores
echo   4. Configure proteções de branch
echo   5. Comece a desenvolver!
echo.
echo 🔗 URL do repositório: %repo_url%
echo.

pause
