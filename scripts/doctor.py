"""
Agent Chrome Doctor — System Diagnostics & Readiness Check
Run this script to verify your local environment before launching Agent Chrome.
Usage:
    python scripts/doctor.py
"""

import json
import os
import shutil
import socket
import sys
import urllib.request

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def print_check(name: str, passed: bool, detail: str = ""):
    symbol = f"{GREEN}✔{RESET}" if passed else f"{RED}✗{RESET}"
    msg = f"[{symbol}] {BOLD}{name}{RESET}"
    if detail:
        msg += f" — {detail}"
    print(msg)


def find_chrome():
    if sys.platform == "win32":
        candidates = [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
    elif sys.platform == "darwin":
        c = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        if os.path.exists(c):
            return c
    else:
        for name in ["google-chrome", "google-chrome-stable", "chromium-browser", "chromium"]:
            path = shutil.which(name)
            if path:
                return path
    return None


def check_port(port: int) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.5)
    try:
        s.connect(("127.0.0.1", port))
        s.close()
        return True
    except Exception:
        s.close()
        return False


def main():
    print(f"\n{CYAN}{BOLD}=== Agent Chrome Diagnostics (doctor) ==={RESET}\n")
    all_ok = True

    # 1. Python version
    py_ver = sys.version_info
    py_ok = py_ver >= (3, 10)
    print_check("Python 3.10+", py_ok, f"Found {py_ver.major}.{py_ver.minor}.{py_ver.micro}")
    if not py_ok:
        all_ok = False

    # 2. Dependencies
    required_packages = ["fastapi", "uvicorn", "playwright", "httpx", "requests", "pydantic"]
    missing = []
    for pkg in required_packages:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    deps_ok = len(missing) == 0
    print_check("Required Python Packages", deps_ok, "All installed" if deps_ok else f"Missing: {', '.join(missing)}")
    if not deps_ok:
        all_ok = False
        print(f"    {YELLOW}Fix: pip install -r requirements.txt{RESET}")

    # 3. Chrome Executable
    chrome_path = find_chrome()
    chrome_ok = chrome_path is not None
    print_check("Google Chrome Executable", chrome_ok, chrome_path or "Not found in standard paths")
    if not chrome_ok:
        all_ok = False
        print(f"    {YELLOW}Fix: Install Google Chrome from https://google.com/chrome{RESET}")

    # 4. Chrome CDP Port (9222)
    cdp_ok = check_port(9222)
    print_check(
        "Agent Chrome CDP (:9222)",
        cdp_ok,
        "Active & listening" if cdp_ok else "Not running (start via scripts/launch_agent_chrome)"
    )

    # 5. Bridge Server Port (8000)
    bridge_ok = check_port(8000)
    print_check(
        "Bridge Server (:8000)",
        bridge_ok,
        "Active & ready" if bridge_ok else "Not running (start via 'python engine/bridge_server.py')"
    )

    # 6. Profile lock check
    profile_dir = os.environ.get("AGENT_CHROME_PROFILE_DIR", os.path.expanduser("~/.agent-chrome-profile"))
    locks_found = []
    if os.path.exists(profile_dir):
        for root, _, files in os.walk(profile_dir):
            for f in files:
                if f.lower() in ["lock", "singletonlock"]:
                    locks_found.append(os.path.join(root, f))
    if cdp_ok:
        print_check(
            "Browser Profile Health",
            True,
            f"Active session running ({len(locks_found)} normal database locks)"
        )
    else:
        locks_ok = len(locks_found) == 0
        print_check(
            "Browser Profile Health",
            locks_ok,
            "Clean, 0 stale locks" if locks_ok else f"{len(locks_found)} stale lock file(s) detected"
        )
        if not locks_ok:
            print(f"    {YELLOW}Fix: Run 'python scripts/clean_locks.py' to remove stale lock files.{RESET}")

    print("\n" + "=" * 42)
    if all_ok and cdp_ok and bridge_ok:
        print(f"{GREEN}{BOLD}✔ All systems go! Agent Chrome is ready for multi-agent querying.{RESET}\n")
    else:
        print(f"{YELLOW}{BOLD}⚠ Next steps:{RESET}")
        if not cdp_ok:
            print("  1. Launch Agent Chrome: run 'scripts/launch_agent_chrome.bat' (or .sh / .ps1)")
        if not bridge_ok:
            print("  2. Start the Bridge:    run 'python engine/bridge_server.py'")
        print("  3. Query the Council:   run 'python engine/council.py -q \"Your question here\"'\n")


if __name__ == "__main__":
    main()
