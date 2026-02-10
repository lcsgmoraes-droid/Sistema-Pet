@echo off
REM Script para resetar sequences do PostgreSQL
REM Útil quando há erros de duplicate key

echo ========================================
echo RESETANDO SEQUENCES DO POSTGRESQL
echo ========================================
echo.

Get-Content "backend\scripts\reset_sequences.sql" | docker exec -i petshop-dev-postgres psql -U postgres -d petshop_dev

echo.
echo ========================================
echo SEQUENCES RESETADAS COM SUCESSO!
echo ========================================
pause
