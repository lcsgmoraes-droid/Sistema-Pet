@echo off
echo ========================================
echo  Sistema Pet Shop Pro - Iniciando...
echo ========================================
echo.

cd backend
echo [1/2] Ativando ambiente virtual Python...
call ..\.venv\Scripts\activate.bat

echo [2/2] Iniciando backend (FastAPI)...
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

pause
