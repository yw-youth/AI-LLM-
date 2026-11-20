@echo off
rem Double-click launcher for the PCB agent demo.
rem %~dp0 = the folder this .bat sits in, so it works no matter where you copy it.
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo  PCB Agent demo: one sentence in, KiCad out
echo ============================================
echo.

rem Prefer python on PATH; fall back to the py launcher.
set "PY=python"
where python >nul 2>nul
if errorlevel 1 set "PY=py"

%PY% src\pipeline.py "Arduino minimal system board"
if errorlevel 1 goto fail

echo.
echo ============================================
echo  DONE. Files are in the "out" folder.
echo  Now open out\board.kicad_pro with KiCad.
echo ============================================
echo.
pause
exit /b 0

:fail
echo.
echo FAILED - take a screenshot of this window and send it back.
pause
