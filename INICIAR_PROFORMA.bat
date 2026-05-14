@echo off
REM ============================================================
REM  ACONIC - Cuadro Comparativo de Proformas
REM  Launcher para ejecucion desde red
REM
REM  Copia el programa a disco local para velocidad maxima.
REM  Solo copia la primera vez o cuando hay actualizacion.
REM ============================================================
setlocal EnableDelayedExpansion

REM ── Configuracion ──────────────────────────────────────────
set "APP_NAME=ACONIC_Proforma"
set "LOCAL_DIR=%LOCALAPPDATA%\%APP_NAME%"
set "NETWORK_DIR=%~dp0"
set "EXE_FOLDER=ACONIC_Proforma"
set "EXE_NAME=ACONIC_Proforma.exe"
set "OUTPUT_DIR=%USERPROFILE%\Documents\ACONIC_Proforma_Output"

REM ── Atajo rapido: si ya existe local y version es igual, lanzar directo ──
if exist "%LOCAL_DIR%\%EXE_FOLDER%\%EXE_NAME%" (
    if exist "%LOCAL_DIR%\VERSION.txt" (
        if exist "%NETWORK_DIR%VERSION.txt" (
            set /p NET_VER=<"%NETWORK_DIR%VERSION.txt"
            set /p LOC_VER=<"%LOCAL_DIR%\VERSION.txt"
            REM Quitar espacios en blanco
            for /f "tokens=*" %%a in ("!NET_VER!") do set "NET_VER=%%a"
            for /f "tokens=*" %%a in ("!LOC_VER!") do set "LOC_VER=%%a"
            if "!NET_VER!" == "!LOC_VER!" (
                REM Versiones iguales - lanzar INMEDIATAMENTE sin mostrar nada
                if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"
                start "" "%LOCAL_DIR%\%EXE_FOLDER%\%EXE_NAME%" --output-dir "%OUTPUT_DIR%"
                exit
            )
        )
    )
)

REM ── Si llegamos aqui, necesitamos instalar o actualizar ────
echo.
echo   ========================================
echo    ACONIC S.A - Cuadro Comparativo
echo   ========================================
echo.

REM ── Verificar que existe el .exe en la red ─────────────────
if not exist "%NETWORK_DIR%%EXE_FOLDER%\%EXE_NAME%" (
    echo   [ERROR] No se encontro el programa en la red.
    echo   Ruta: %NETWORK_DIR%%EXE_FOLDER%\%EXE_NAME%
    echo   Contacta a IT.
    pause
    exit /b 1
)

REM ── Crear directorio de salida ─────────────────────────────
if not exist "%OUTPUT_DIR%" (
    mkdir "%OUTPUT_DIR%"
)

REM ── Verificar si es primera vez o actualizacion ────────────
if not exist "%LOCAL_DIR%\%EXE_FOLDER%\%EXE_NAME%" (
    echo   [INFO] Primera ejecucion - instalando localmente...
    echo   [INFO] Esto solo pasa UNA VEZ. Despues abre instantaneo.
) else (
    echo   [INFO] Actualizacion detectada, sincronizando...
)
echo.

REM ── Crear directorio local ─────────────────────────────────
if not exist "%LOCAL_DIR%" mkdir "%LOCAL_DIR%"
if not exist "%LOCAL_DIR%\%EXE_FOLDER%" mkdir "%LOCAL_DIR%\%EXE_FOLDER%"

REM ── Copiar con ROBOCOPY (solo archivos nuevos/cambiados) ───
echo   Copiando archivos (solo los nuevos o modificados)...
robocopy "%NETWORK_DIR%%EXE_FOLDER%" "%LOCAL_DIR%\%EXE_FOLDER%" /E /NFL /NDL /NJH /NJS /NC /NS /NP
REM robocopy retorna 0-7 como exito
if %ERRORLEVEL% GEQ 8 (
    echo   [ERROR] Fallo al copiar archivos.
    pause
    exit /b 1
)

REM ── Copiar VERSION.txt ─────────────────────────────────────
copy /Y "%NETWORK_DIR%VERSION.txt" "%LOCAL_DIR%\VERSION.txt" >nul 2>nul

echo   [OK] Listo!
echo.

REM ── Ejecutar ───────────────────────────────────────────────
echo   Iniciando ACONIC Proforma...
start "" "%LOCAL_DIR%\%EXE_FOLDER%\%EXE_NAME%" --output-dir "%OUTPUT_DIR%"
exit
