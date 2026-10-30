@echo off
setlocal enabledelayedexpansion

:: Formula 1 ERS Simulation Suite Windows Launcher
:: Automatically finds Python on the machine and executes CLI or Web App

set "PY_CMD="

:: Check if KiCad Python exists
if exist "C:\Users\shaan\AppData\Local\Programs\KiCad\10.0\bin\python.exe" (
    set "PY_CMD=C:\Users\shaan\AppData\Local\Programs\KiCad\10.0\bin\python.exe"
) else (
    :: Try standard python or py
    where py >nul 2>nul
    if !errorlevel! equ 0 (
        set "PY_CMD=py"
    ) else (
        set "PY_CMD=python"
    )
)

if "%~1"=="" (
    echo.
    echo =========================================================================
    echo  Formula 1 ERS Simulation & Driver Comparison Suite
    echo =========================================================================
    echo  [1] Run CLI Monza Driver Comparison (VER, HAM, ALO, NOR)
    echo  [2] Run CLI Silverstone Driver Comparison
    echo  [3] Run CLI Spa-Francorchamps Driver Comparison
    echo  [4] Launch Interactive Web Dashboard (http://localhost:8050)
    echo  [5] Run Unit Test Suite
    echo =========================================================================
    echo.
    set /p choice="Select an option (1-5, or press Enter for Web Dashboard): "
    if "!choice!"=="1" "%PY_CMD%" cli.py compare --drivers ver,ham,alo,nor --track monza --html-report monza_report.html
    if "!choice!"=="2" "%PY_CMD%" cli.py compare --drivers ver,ham,alo,nor --track silverstone --html-report silverstone_report.html
    if "!choice!"=="3" "%PY_CMD%" cli.py compare --drivers ver,ham,alo,nor --track spa --html-report spa_report.html
    if "!choice!"=="4" "%PY_CMD%" app.py
    if "!choice!"=="5" "%PY_CMD%" -m unittest discover tests
    if "!choice!"=="" "%PY_CMD%" app.py
) else (
    "%PY_CMD%" cli.py %*
)
