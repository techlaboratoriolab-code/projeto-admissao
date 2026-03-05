@echo off
chcp 65001 >nul
echo ========================================
echo   DESINSTALAR SERVICO DO BACKEND
echo ========================================

net session >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Execute como ADMINISTRADOR!
    pause
    exit /b 1
)

schtasks /delete /tn "LaboratorioAdmissao_Backend" /f
if errorlevel 1 (
    echo [AVISO] Tarefa nao encontrada ou ja removida.
) else (
    echo [OK] Tarefa removida com sucesso!
)

echo.
echo O backend NAO vai mais iniciar automaticamente.
echo Para reiniciar manualmente, rode: iniciar_publico.bat
echo.
pause
