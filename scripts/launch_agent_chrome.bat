@echo off
setlocal
echo ========================================================
echo   Launching Agent Chrome with Multi-LLM Web Tabs...
echo ========================================================

set CHROME_PATH="%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not exist %CHROME_PATH% (
    set CHROME_PATH="%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
)
if not exist %CHROME_PATH% (
    set CHROME_PATH="%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
)

if not exist %CHROME_PATH% (
    echo [ERROR] Google Chrome was not found in standard paths.
    echo Please install Chrome or specify its path.
    pause
    exit /b 1
)

if "%AGENT_CHROME_PROFILE_DIR%"=="" (
    set PROFILE_DIR="%USERPROFILE%\.agent-chrome-profile"
) else (
    set PROFILE_DIR="%AGENT_CHROME_PROFILE_DIR%"
)

echo Starting visible Agent Chrome on port 9222...
start "" %CHROME_PATH% --remote-debugging-port=9222 --user-data-dir=%PROFILE_DIR% https://chatgpt.com https://claude.ai https://chat.deepseek.com https://gemini.google.com https://chat.z.ai

echo Done. Log in to each tab once.
endlocal
