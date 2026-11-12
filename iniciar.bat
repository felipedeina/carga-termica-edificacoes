@echo off
cd /d "%~dp0"
chcp 65001 > nul
title Simulador Fisico de Carga Termica e Conforto - Engenharia Mecanica
echo ============================================================================
echo   SIMULADOR DE CARGA TERMICA E CONFORTO TERMICO DE EDIFICACOES (PYTHON)
echo ============================================================================
echo.
echo [1/3] Verificando instalacao do Python na maquina...
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python nao encontrado no PATH do sistema. Instale o Python 3.9+ para executar.
    pause
    exit /b 1
)

echo [2/3] Verificando e instalando dependencias do requirements.txt...
python -m pip install -r requirements.txt --quiet

echo [3/3] Executando bateria de testes automatizados (pytest)...
python -m pytest test_calculos.py -v

echo.
echo Iniciando interface grafica no navegador (Streamlit)...
python -m streamlit run app.py
pause
