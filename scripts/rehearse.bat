@echo off
REM Dress rehearsal for the demo video: runs EVERY command listed in
REM docs\08 (video script) in one go, so you know the take will be clean
REM BEFORE you hit record. ASCII-only on purpose: non-ASCII .bat files get
REM garbled by the Windows console codepage.
REM
REM Note: this uses an English requirement because .bat cannot safely carry
REM Chinese text. In the real take you type the Chinese sentence yourself -
REM both parse to the same Arduino board (that is part of the demo).
cd /d "%~dp0.."

echo === [0/6] UTF-8 console (as the video script requires: chcp 65001) ===
chcp 65001 >nul

echo === [1/6] Reset out\ so the take grows artifacts from zero ===
if exist out rmdir /s /q out

echo === [2/6] Main pipeline: one sentence - KiCad project ===
python src/pipeline.py "Arduino minimal system board"
if errorlevel 1 goto failed

echo === [3/6] Artifacts list (the 8 outputs) ===
dir /b out

echo === [4/6] Machine acceptance A: KiCad ERC on the three boards ===
python scripts/kicad_check.py
if errorlevel 1 goto failed

echo === [5/6] Machine acceptance B: schematic netlist == design netlist ===
REM ERC only checks rules; this compares the netlist KiCad exports from the
REM drawn schematic against the netlist we meant to implement. This is the
REM check that catches "two nets silently merged into one".
python scripts/sch_netlist_check.py
if errorlevel 1 goto failed

echo === [6/6] Closed-loop demo: 5 fault scenarios ===
python scripts/demo_loop.py
if errorlevel 1 goto failed

echo.
echo REHEARSAL OK - every command in the video script is green.
echo You can start recording now. Shot list: docs\08 video script (.md)
echo Reminder: in the real take type the Chinese requirement sentence.
pause
exit /b 0

:failed
echo.
echo REHEARSAL FAILED - fix this before recording, do not edit during take.
pause
exit /b 1
