@echo off
chcp 65001 >nul
title 🟢 LOCAL PILOTO - Loja Real

echo.
echo ============================================================================
echo   🟢 AMBIENTE LOCAL PILOTO (LOJA REAL)
echo ============================================================================
echo.
echo Subindo:
echo   - Banco PILOTO (porta 5434)
echo   - Backend PILOTO (porta 8001)
echo.
echo Frontend: http://localhost:5173
echo Backend:  http://localhost:8001
echo Docs:     http://localhost:8001/docs
echo.
echo ⚠️  Este é o ambiente de PRODUÇÃO LOCAL!
echo ⚠️  Use para vendas REAIS da loja
echo ⚠️  NÃO use para testes!
echo.
pause

echo.
echo Subindo containers...
docker-compose -f docker-compose.local-piloto.yml up -d

echo.
echo ✅ Ambiente PILOTO iniciado!
echo.
echo Aguardando backend ficar pronto (20 segundos)...
timeout /t 20 /nobreak >nul

echo.
echo ============================================================================
echo   Acesse: http://localhost:5173
echo   Backend: http://localhost:8001/docs
echo   
echo   Login:
echo   Email: admin@petshop.com
echo   Senha: admin123
echo   
echo   🔴 IMPORTANTE: Altere a senha após o primeiro login!
echo ============================================================================
echo.
echo Para ver logs: docker-compose -f docker-compose.local-piloto.yml logs -f
echo Para parar: docker-compose -f docker-compose.local-piloto.yml down
echo.
pause
