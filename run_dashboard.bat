@echo off
title Painel Instagram Curadorias
echo ============================================================
echo      INICIANDO O PAINEL DE CURADORIAS DO INSTAGRAM
echo ============================================================
echo.
echo [INFO] Abrindo o painel administrativo no seu navegador padrão...
echo.

:: Abre o navegador padrão na rota local do servidor
start http://localhost:5000

:: Inicia o servidor local Flask
python app.py

echo.
pause
