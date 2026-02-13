@echo off
chcp 65001 >nul
title 🔵 Frontend - Conectar no DEV

echo.
echo ============================================================================
echo   🔵 FRONTEND - CONECTAR NO BACKEND DEV (TESTES)
echo ============================================================================
echo.
echo Configurando frontend para usar:
echo   Backend DEV: http://localhost:8000
echo   Dados: FICTÍCIOS (testes)
echo.
pause

cd frontend

echo.
echo [1/2] Copiando configuração DEV...
copy /Y .env.dev .env

echo.
echo [2/2] Arquivo .env atualizado!
echo.
echo ============================================================================
echo   ✅ Frontend configurado para DEV!
echo ============================================================================
echo.
echo Agora:
echo   1. Se o frontend já está rodando, reinicie (Ctrl+C e npm run dev)
echo   2. Se não está rodando, execute: npm run dev
echo.
echo O frontend vai se conectar em: http://localhost:8000 (DEV)
echo.
pause
