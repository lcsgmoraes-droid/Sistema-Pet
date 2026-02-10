@echo off
REM Script para adicionar permissões a roles de Administrador existentes
REM Útil para corrigir usuários criados antes da implementação automática

echo ========================================
echo CORRIGINDO PERMISSOES DE ADMINISTRADORES
echo ========================================
echo.
echo Este script vai adicionar todas as permissoes
echo as roles de Administrador que ainda nao as possuem
echo.

powershell -Command "Get-Content 'backend\scripts\fix_admin_permissions.sql' | docker exec -i petshop-dev-postgres psql -U postgres -d petshop_dev"

echo.
echo ========================================
echo PERMISSOES ATUALIZADAS COM SUCESSO!
echo ========================================
echo.
pause
