$candidates = @(
    "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
)

$chromePath = $null
foreach ($c in $candidates) {
    if (Test-Path $c) {
        $chromePath = $c
        break
    }
}

if (-not $chromePath) {
    Write-Error "Google Chrome executable not found in standard paths."
    exit 1
}

$profileDir = if ($env:AGENT_CHROME_PROFILE_DIR) { $env:AGENT_CHROME_PROFILE_DIR } else { "$env:USERPROFILE\.agent-chrome-profile" }
Write-Host "Starting visible Agent Chrome on port 9222..." -ForegroundColor Cyan

Start-Process -FilePath $chromePath -ArgumentList `
    "--remote-debugging-port=9222", `
    "--user-data-dir=$profileDir", `
    "https://chatgpt.com", `
    "https://claude.ai", `
    "https://chat.deepseek.com", `
    "https://gemini.google.com", `
    "https://chat.z.ai"

Write-Host "Agent Chrome launched successfully. Log in once to save your session." -ForegroundColor Green
