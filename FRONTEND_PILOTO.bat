@echo off
chcp 65001 >nul
title 🟢 Frontend - Conectar no PILOTO

echo.
echo ============================================================================
echo   🟢 FRONTEND - CONECTAR NO BACKEND PILOTO (LOJA REAL)
echo ============================================================================
echo.
echo Configurando frontend para usar:
echo   Backend PILOTO: http://localhost:8001
echo   Dados: REAIS da loja
echo.
echo ⚠️  ATENÇÃO: Este backend tem DADOS REAIS!
echo.
pause

cd frontend

echo.
echo [1/2] Copiando configuração PILOTO...
copy /Y .env.piloto .env

echo.
echo [2/2] Arquivo .env atualizado!
echo.
echo ============================================================================
echo   ✅ Frontend configurado para PILOTO!
echo ============================================================================
echo.
echo Agora:
echo   1. Se o frontend já está rodando, reinicie (Ctrl+C e npm run dev)
echo   2. Se não está rodando, execute: npm run dev
echo.
echo O frontend vai se conectar em: http://localhost:8001 (PILOTO)
echo.
pause
