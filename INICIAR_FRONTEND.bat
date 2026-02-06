@echo off
echo ========================================
echo   INICIAR FRONTEND - Sistema Pet Shop
echo ========================================
echo.
echo Iniciando servidor Vite (Frontend)...
echo.

cd frontend
start "Frontend - Vite" npm run dev

echo.
echo ========================================
echo   Frontend iniciado!
echo   Acesse: http://localhost:5173
echo ========================================
echo.
pause
