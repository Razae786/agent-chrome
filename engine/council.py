"""
Agent Chrome — Multi-LLM Consensus Council Orchestrator
CLI tool to query browser-session LLMs, evaluate consensus, and cross-reference answers.
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BRIDGE_URL = os.environ.get("BRIDGE_SERVER_URL", "http://127.0.0.1:8000/v1/chat/completions")
HEALTH_URL = os.environ.get("BRIDGE_HEALTH_URL", "http://127.0.0.1:8000/health")
DEFAULT_MODELS = [
    "web-claude-sonnet",
    "web-deepseek-r1",
    "web-chatgpt",
    "web-gemini",
    "web-zai"
]


def check_status() -> dict:
    status = {"agent_chrome": {}, "bridge_server": {}}
    # 1. Check Chrome CDP
    cdp_port = int(os.environ.get("CHROME_CDP_PORT", 9222))
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{cdp_port}/json/version")
        with urllib.request.urlopen(req, timeout=1.5) as r:
            status["agent_chrome"] = {
                "status": "ONLINE",
                "cdp_port": cdp_port,
                "message": "Agent Chrome is open on your desktop."
            }
    except Exception:
        status["agent_chrome"] = {
            "status": "OFFLINE",
            "cdp_port": cdp_port,
            "message": "Launch Agent Chrome from your desktop or run scripts/launch_agent_chrome."
        }

    # 2. Check Bridge Server
    try:
        r = requests.get(HEALTH_URL, timeout=2.0)
        if r.status_code == 200:
            data = r.json()
            status["bridge_server"] = {
                "status": "ONLINE",
                "cdp_connected": data.get("cdp_connected", False),
                "providers": data.get("providers", [])
            }
        else:
            status["bridge_server"] = {"status": f"HTTP {r.status_code}"}
    except Exception:
        status["bridge_server"] = {
            "status": "OFFLINE",
            "message": "Run 'python engine/bridge_server.py' to start the local bridge."
        }

    return status


def query_single_model(model: str, prompt: str, timeout: int = 60) -> dict:
    try:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1024
        }
        res = requests.post(BRIDGE_URL, json=payload, timeout=timeout)
        if res.status_code == 200:
            data = res.json()
            content = data["choices"][0]["message"]["content"]
            return {"ok": True, "response": content}
        return {"ok": False, "error": f"HTTP {res.status_code}: {res.text[:120]}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def query_council(prompt: str, models: list = None, timeout: int = 60) -> dict:
    target_models = models or DEFAULT_MODELS
    results = {}
    print(f"\n[Council] Querying {len(target_models)} browser models simultaneously:")
    print("  Models:", ", ".join(target_models))
    print(f"  Prompt: {prompt[:80]}...\n")

    for model in target_models:
        print(f"  --> Dispatching to {model}...")
        t0 = time.time()
        res = query_single_model(model, prompt, timeout=timeout)
        elapsed = round(time.time() - t0, 1)
        if res.get("ok"):
            text = res["response"]
            results[model] = {"ok": True, "elapsed_s": elapsed, "response": text}
            print(f"  ✔ {model}: Received answer ({len(text)} chars, {elapsed}s)")
        else:
            err = res.get("error", "Unknown error")
            results[model] = {"ok": False, "elapsed_s": elapsed, "error": err}
            print(f"  ✗ {model}: Failed ({err})")

    return results


def main():
    parser = argparse.ArgumentParser(description="Agent Chrome — Multi-LLM Consensus Council")
    parser.add_argument("--status", action="store_true", help="Check Agent Chrome & Bridge health")
    parser.add_argument("--query", "-q", type=str, help="Prompt to dispatch to the model council")
    parser.add_argument("--models", "-m", nargs="+", help="Specific models to query")
    parser.add_argument("--timeout", "-t", type=int, default=60, help="Per-model timeout in seconds")
    args = parser.parse_args()

    if args.status:
        st = check_status()
        print(json.dumps(st, indent=2))
        return

    if args.query:
        st = check_status()
        if st["agent_chrome"]["status"] != "ONLINE":
            print("\n[ERROR] Agent Chrome is not running!")
            print("Please open Agent Chrome from your desktop so you can see your live tabs.")
            sys.exit(1)

        res = query_council(args.query, models=args.models, timeout=args.timeout)
        print("\n=== COUNCIL CONSENSUS RESPONSES ===")
        print(json.dumps(res, indent=2))
        return

    parser.print_help()


if __name__ == "__main__":
    main()
