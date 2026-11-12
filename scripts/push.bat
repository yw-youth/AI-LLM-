@echo off
REM One-click push for the pcb-agent repo.
REM Run by double-clicking. ASCII-only on purpose: .bat files with non-ASCII
REM content get garbled by the Windows console codepage.
cd /d "%~dp0.."
echo === current branch ===
git branch --show-current
echo.
echo === recent commits ===
git log --oneline -5
echo.
echo === pushing to origin ===
git push -u origin main
if errorlevel 1 goto failed
echo.
echo OK: pushed. Open the repo page and check the Actions tab for a green check.
pause
exit /b 0

:failed
echo.
echo Push failed. Most likely reasons:
echo   1. Network blocked  - retry, or use a proxy / mobile hotspot.
echo   2. Remote has files - run:  git pull --rebase origin main   then retry.
echo   3. Login required   - a browser window should have opened; finish it and retry.
pause
exit /b 1
