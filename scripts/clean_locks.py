"""
Utility to safely clean stale LevelDB and Chromium singleton locks
Run this if Agent Chrome refuses to start due to an abrupt shutdown or crash.
"""

import json
import os
import sys

def clean():
    profile_dir = os.environ.get("AGENT_CHROME_PROFILE_DIR", os.path.expanduser("~/.agent-chrome-profile"))
    if not os.path.exists(profile_dir):
        print(f"Profile directory not found: {profile_dir}")
        return

    removed = 0
    for root, _, files in os.walk(profile_dir):
        for f in files:
            if f.lower() in ["lock", "singletonlock", "singletoncookie", "singletonsocket"]:
                path = os.path.join(root, f)
                try:
                    os.remove(path)
                    removed += 1
                except Exception as e:
                    print(f"Could not remove {path}: {e}")

    # Reset Preferences crash flag
    pref_file = os.path.join(profile_dir, "Default", "Preferences")
    if os.path.exists(pref_file):
        try:
            with open(pref_file, "r", encoding="utf-8") as pf:
                data = json.load(pf)
            if "profile" in data:
                data["profile"]["exit_type"] = "Normal"
                data["profile"]["exited_cleanly"] = True
            with open(pref_file, "w", encoding="utf-8") as pf:
                json.dump(data, pf)
            print("Reset Preferences exit_type to Normal.")
        except Exception as e:
            print(f"Could not update Preferences: {e}")

    print(f"Cleaned {removed} stale lock file(s). Agent Chrome is unblocked!")

if __name__ == "__main__":
    clean()
