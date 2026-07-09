@echo off
title Instagram Scraper Bot
echo ============================================================
echo      EXECUTANDO VARREDURA AUTOMATIZADA DO INSTAGRAM
echo ============================================================
echo.

:: Garante que estamos na pasta correta do script (onde scraper.py está localizado) para execução correta via Agendador de Tarefas
cd /d "%~dp0"

:: Executa o script do scraper
python scraper.py

echo.
echo ============================================================
echo         VARREDURA DO INSTAGRAM CONCLUIDA COM SUCESSO!
echo ============================================================
echo.

:: Se o script foi chamado com --no-pause (por exemplo, pelo Agendador de Tarefas), pula o pause
if "%1"=="--no-pause" goto end
pause
:end
