@echo off
REM One-click push (v2).
REM Handles the case where the GitHub repo already contains commits we do not
REM have locally (typically an initial README created from the web UI). A plain
REM "git push" then fails with:  ! [rejected] main -> main (fetch first).
REM Fix: fetch, merge the unrelated history preferring OUR files, then push.
REM ASCII-only on purpose: .bat with non-ASCII gets garbled by the console codepage.
cd /d "%~dp0.."

echo === branch ===
git branch --show-current
echo.
echo === recent local commits ===
git log --oneline -3
echo.

echo === [1/3] fetch remote ===
git fetch origin
if errorlevel 1 goto netfail

git rev-parse --verify origin/main >nul 2>&1
if errorlevel 1 goto pushnow

echo === [2/3] merge remote commits (our files win on conflict) ===
git merge -X ours origin/main --allow-unrelated-histories -m "chore: merge GitHub initial commit"
if errorlevel 1 goto mergefail
goto pushnow

:pushnow
echo === [3/3] push ===
git push -u origin main
if errorlevel 1 goto pushfail

echo.
echo OK: pushed. Open https://github.com/yw-youth/AI-LLM- and check the commit list.
echo If the repo page still shows nothing, press Ctrl+F5 to hard refresh.
pause
exit /b 0

:netfail
echo.
echo FETCH FAILED - network problem.
echo  1. Retry once.
echo  2. Still failing: switch to a proxy or a mobile hotspot, then run this again.
pause
exit /b 1

:mergefail
echo.
echo MERGE FAILED - do not panic, nothing is lost.
echo  Run these two commands in this folder, then run this script again:
echo     git merge --abort
echo     git status
pause
exit /b 1

:pushfail
echo.
echo PUSH FAILED - login or network.
echo  1. A browser window may have opened for GitHub login: finish it, run again.
echo  2. If it says "remote already has work", run this script again - it merges first.
pause
exit /b 1
