@echo off
REM =========================================
REM SCRIPT DE BUILD PARA PRODUÇÃO (Windows)
REM =========================================

echo ==========================================
echo BUILD DE PRODUCAO - PET SHOP PRO
echo ==========================================

REM Verificar se estamos na pasta frontend
if not exist "package.json" (
  echo ERRO: Execute este script na pasta frontend/
  exit /b 1
)

echo.
echo Configuracao:
echo    - Modo: production
echo    - Arquivo .env: .env.production
echo    - VITE_API_URL esperado: /api
echo.

REM Verificar se .env.production existe
if not exist ".env.production" (
  echo ERRO: Arquivo .env.production nao encontrado!
  echo    Crie o arquivo com: VITE_API_URL=/api
  exit /b 1
)

REM Mostrar conteúdo do .env.production
echo Conteudo do .env.production:
type .env.production
echo.

pause

REM Remover build anterior
echo Limpando build anterior...
if exist "dist" rd /s /q dist

REM Build de produção
echo Iniciando build de producao...
call npm run build

REM Verificar se build foi bem-sucedido
if %ERRORLEVEL% EQU 0 (
  echo.
  echo ==========================================
  echo BUILD CONCLUIDO COM SUCESSO!
  echo ==========================================
  echo.
  echo Pasta: dist/
  echo.
  echo Proximos passos:
  echo    1. Copiar dist/ para o servidor
  echo    2. Reiniciar o nginx
  echo.
  echo Comando de deploy:
  echo    scp -r dist/* root@mlprohub.com.br:/opt/petshop/frontend/dist/
  echo.
) else (
  echo.
  echo ERRO NO BUILD!
  echo Verifique os erros acima
  exit /b 1
)

pause
