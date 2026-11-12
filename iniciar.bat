@echo off
cd /d "%~dp0"
chcp 65001 > nul
title Simulador Fisico de Carga Termica e Conforto
echo ============================================================================
echo   SIMULADOR DE CARGA TERMICA E CONFORTO TERMICO DE EDIFICACOES (PYTHON)
echo ============================================================================
echo.
echo [1/3] A verificar o Python e a instalar bibliotecas (aguarde 1 a 2 minutos)...
python -m pip install -r requirements.txt --no-warn-script-location || py -m pip install -r requirements.txt --no-warn-script-location
echo.
echo [2/3] A executar bateria de testes automatizados (pytest)...
python -m pytest test_calculos.py -v || py -m pytest test_calculos.py -v
echo.
echo [3/3] A iniciar a interface grafica no navegador (Streamlit)...
if not exist "%USERPROFILE%\.streamlit" mkdir "%USERPROFILE%\.streamlit"
if not exist "%USERPROFILE%\.streamlit\credentials.toml" (
    echo [general]> "%USERPROFILE%\.streamlit\credentials.toml"
    echo email = "">> "%USERPROFILE%\.streamlit\credentials.toml"
)
python -m streamlit run app.py || py -m streamlit run app.py
echo.
pause
