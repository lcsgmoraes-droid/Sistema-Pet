@echo off
chcp 65001 >nul
echo.
echo ╔════════════════════════════════════════╗
echo ║       PetShop App - Iniciar DEV        ║
echo ╚════════════════════════════════════════╝
echo.

REM 1. Verificar se o backend esta rodando
echo [1/3] Verificando backend...
curl -s http://192.168.15.138:8000/health >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ⚠️  ATENÇÃO: Backend nao parece estar rodando.
    echo     Inicie primeiro o ambiente DEV com: FLUXO_UNICO.bat dev-up
    echo     Depois rode este arquivo novamente.
    echo.
    pause
    exit /b 1
)
echo     ✓ Backend respondendo em http://192.168.15.138:8000

echo.
echo [2/3] Verificando dependencias...
if not exist "app-mobile\node_modules" (
    echo     Instalando dependencias pela primeira vez...
    cd app-mobile
    npm install
    cd ..
) else (
    echo     ✓ Dependencias OK
)

echo.
echo [3/3] Iniciando Expo...
echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo  PRÓXIMOS PASSOS:
echo  1. Um QR Code vai aparecer aqui
echo  2. No Android: abra "Expo Go" e escaneie
echo  3. No iPhone: abra a Camera e escaneie
echo  4. O app abre no celular em segundos!
echo.
echo  Para parar: pressione Ctrl+C
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

cd app-mobile
npx expo start --clear
