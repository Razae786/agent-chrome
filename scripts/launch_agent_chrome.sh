#!/usr/bin/env bash
set -e

echo "=== Launching Agent Chrome (macOS / Linux) ==="

CHROME_BIN=""
if [[ "$OSTYPE" == "darwin"* ]]; then
    CHROME_BIN="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    PROFILE_DIR="$HOME/Library/Application Support/Google/Chrome/AgentProfile"
else
    for candidate in google-chrome google-chrome-stable chromium-browser chromium; do
        if command -v "$candidate" >/dev/null 2>&1; then
            CHROME_BIN="$candidate"
            break
        fi
    done
    PROFILE_DIR="$HOME/.config/google-chrome/AgentProfile"
fi

if [[ -z "$CHROME_BIN" ]]; then
    echo "[ERROR] Google Chrome / Chromium executable not found."
    exit 1
fi

mkdir -p "$PROFILE_DIR"

echo "Starting Chrome on port 9222 with profile: $PROFILE_DIR"
"$CHROME_BIN" \
    --remote-debugging-port=9222 \
    --user-data-dir="$PROFILE_DIR" \
    "https://chatgpt.com" \
    "https://claude.ai" \
    "https://chat.deepseek.com" \
    "https://gemini.google.com" \
    "https://chat.z.ai" &

echo "Agent Chrome launched. Log into each model once."
