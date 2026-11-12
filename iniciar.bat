@echo off
cd /d "%~dp0"
chcp 65001 > nul
title Simulador Fisico de Carga Termica e Conforto - Engenharia Mecanica
echo ============================================================================
echo   SIMULADOR DE CARGA TERMICA E CONFORTO TERMICO DE EDIFICACOES (PYTHON)
echo ============================================================================
echo.

if not exist "app.py" (
    echo [AVISO] O arquivo app.py nao foi encontrado nesta pasta.
    echo Certifique-se de EXTRAIR (descompactar) todo o arquivo .ZIP para uma pasta
    echo antes de dar dois cliques no iniciar.bat!
    pause
    exit /b 1
)

echo [1/3] Localizando instalacao do Python na maquina...
set PYTHON_CMD=

python --version > nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python
    goto :encontrou_python
)

py --version > nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py
    goto :encontrou_python
)

echo [AVISO] O Python nao foi encontrado neste computador.
echo Tentando instalar o Python 3.12 automaticamente via Windows (winget)...
winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
if %errorlevel% equ 0 (
    echo.
    echo [SUCESSO] Python instalado! Feche esta janela e abra o iniciar.bat novamente.
    pause
    exit /b 0
) else (
    echo.
    echo [ERRO] Nao foi possivel instalar automaticamente.
    echo Baixe o Python em https://www.python.org/downloads/ marcando a opcao "Add python.exe to PATH".
    pause
    exit /b 1
)

:encontrou_python
echo Python detectado com sucesso usando o comando: %PYTHON_CMD%
echo.
echo [2/3] Verificando e instalando dependencias do requirements.txt...
%PYTHON_CMD% -m pip install -r requirements.txt --quiet

echo [3/3] Executando bateria de testes automatizados (pytest)...
%PYTHON_CMD% -m pytest test_calculos.py -v

echo.
echo Iniciando interface grafica no navegador (Streamlit)...
%PYTHON_CMD% -m streamlit run app.py
pause
