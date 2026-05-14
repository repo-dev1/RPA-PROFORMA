@echo off
REM ============================================================
REM  ACONIC - Build Script para generar el .exe
REM  Ejecuta este script cuando hagas cambios al codigo.
REM ============================================================
echo.
echo ========================================
echo   ACONIC Proforma - Compilando .exe
echo ========================================
echo.

REM Activate venv
call venv\Scripts\activate.bat

REM Clean previous build
if exist "dist" (
    echo Limpiando build anterior...
    rmdir /s /q dist
)
if exist "build" (
    rmdir /s /q build
)

echo Compilando con PyInstaller...
echo (Esto puede tardar 1-2 minutos)
echo.

pyinstaller proforma.spec --noconfirm

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ==========================================
    echo   ERROR: La compilacion fallo.
    echo   Revisa los errores arriba.
    echo ==========================================
    pause
    exit /b 1
)

REM Copy VERSION.txt into the dist folder
copy /Y VERSION.txt dist\ACONIC_Proforma\VERSION.txt >nul

echo.
echo ==========================================
echo   EXITO! .exe generado en:
echo   dist\ACONIC_Proforma\ACONIC_Proforma.exe
echo.
echo   Para desplegar en la red, copia:
echo   - La carpeta dist\ACONIC_Proforma\
echo   - INICIAR_PROFORMA.bat
echo   - VERSION.txt
echo   A: \\Aconic-nas\it\64Bits\HERRAMIENTAS\RPA PROFORMA\
echo ==========================================
echo.
pause
