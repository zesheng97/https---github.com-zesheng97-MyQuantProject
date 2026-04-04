@echo off
REM Force activate base environment and reject kth
setx CONDA_DEFAULT_ENV base
setx CONDA_PREFIX D:\Anaconda

REM Kill any running VS Code instances
taskkill /F /IM code.exe 2>nul

REM Delete VS Code workspace cache
PowerShell -NoProfile -ExecutionPolicy Bypass -Command ^
  "if(Test-Path 'C:\Users\12434\AppData\Roaming\Code\User\workspaceStorage\ca4e7f0fc4d6b7b2135070e2312de395') { ^
    Remove-Item -Path 'C:\Users\12434\AppData\Roaming\Code\User\workspaceStorage\ca4e7f0fc4d6b7b2135070e2312de395\*' -Recurse -Force -ErrorAction SilentlyContinue; ^
  }"

echo.
echo ========================================
echo VS Code cache cleaned and kth disabled
echo ========================================
echo.
echo Close this window and reopen VS Code
pause
