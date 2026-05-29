@echo off
title Configurar Agendamento do Scraper
echo ============================================================
echo      CONFIGURANDO AGENDAMENTO AUTOMATICO NO WINDOWS
echo ============================================================
echo.
echo Este script configurará o scraper do Instagram para rodar
echo automaticamente todos os dias às 10:00 e às 17:00.
echo.
echo [INFO] Certifique-se de executar este script como Administrador.
echo.

:: Caminho absoluto do atalho de execução do scraper
set SCRAPER_PATH="c:\Users\titoc\OneDrive\Documentos\instagram_scrapper\run_scraper.bat"

echo [1/2] Agendando execução para às 10:00...
schtasks /create /tn "Instagram_Scraper_Daily_10h" /tr %SCRAPER_PATH% /sc daily /st 10:00 /f

echo.
echo [2/2] Agendando execução para às 17:00...
schtasks /create /tn "Instagram_Scraper_Daily_17h" /tr %SCRAPER_PATH% /sc daily /st 17:00 /f

echo.
echo ============================================================
echo      AGENDAMENTO CONCLUIDO COM SUCESSO!
echo ============================================================
echo As tarefas "Instagram_Scraper_Daily_10h" e "Instagram_Scraper_Daily_17h"
echo foram criadas com sucesso no Agendador de Tarefas do Windows.
echo.
pause
