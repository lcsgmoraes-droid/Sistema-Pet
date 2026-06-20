@echo off
cd /d "%~dp0backend"

echo === E2E oficial: Plano Basico ===
echo.
echo Este teste usa backend/tests/test_plano_basico_e2e.py.
echo Configure E2E_BASE_URL, E2E_USER_EMAIL, E2E_USER_PASSWORD e E2E_TENANT_ID.
echo Contra producao, tambem configure E2E_ALLOW_PRODUCTION=true.
echo.

python -m pytest tests/test_plano_basico_e2e.py -m e2e_long -q

if errorlevel 1 (
    echo.
    echo E2E falhou ou foi pulado por falta de variaveis.
    exit /b 1
)

echo.
echo E2E concluido.
