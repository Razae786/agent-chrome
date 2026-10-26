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
    "web-zai",
    "web-kimi"
]

AUDIT_PREPROMPT = (
    "[HOSTILE TECHNICAL AUDIT MODE: ZERO SYCOPHANCY ENFORCED]\n"
    "Role: You are a ruthless, adversarial principal systems architect and defense examiner.\n"
    "Rules:\n"
    "1. Do NOT be polite, agreeable, or reassuring. Eliminate all conversational filler, apologies, and flattery.\n"
    "2. Assume this design/code has fatal flaws, hidden failure modes, unhandled edge cases, or rubric violations.\n"
    "3. Expose every vulnerability, bottleneck, false assumption, and discrepancy directly.\n"
    "4. Prioritize brutal honesty and technical accuracy above all else.\n\n"
    "SUBJECT UNDER AUDIT:\n"
)


def synthesize_council(original_query: str, results: dict, judge_model: str = "web-claude-sonnet") -> dict:
    successful = {m: r["response"] for m, r in results.items() if r.get("ok") and r.get("response")}
    if len(successful) < 2:
        return {"ok": False, "error": "Need at least 2 successful responses to synthesize consensus."}

    print(f"\n[Arbiter] Generating Automated Cross-Model Consensus Synthesis via {judge_model}...")

    summaries = []
    for model_name, text in successful.items():
        # Trim text to keep judge prompt bounded
        trimmed = text.strip()
        if len(trimmed) > 1800:
            trimmed = trimmed[:1800] + "\n...[truncated for synthesis]..."
        summaries.append(f"=== MODEL: {model_name} ===\n{trimmed}\n")

    combined_input = "\n".join(summaries)
    arbiter_prompt = (
        "[COUNCIL CONSENSUS SYNTHESIZER & JUDGE]\n"
        "You are the Chief Arbiter cross-examining multiple independent frontier model evaluations.\n"
        f"Original Query: {original_query}\n\n"
        f"COUNCIL OUTPUTS:\n{combined_input}\n\n"
        "Generate a structured, authoritative 3-part Markdown Verdict:\n"
        "### 1. 🎯 Consensus Ground Truth (Points all/most models agree on)\n"
        "### 2. ⚡ Contradictions & Discrepancies (Where models clash, hallucinated, or diverged)\n"
        "### 3. 🏆 Winning Synthesized Solution (The single best, complete recommendation combining top insights)\n"
    )

    t0 = time.time()
    judge_res = query_single_model(judge_model, arbiter_prompt, timeout=90)
    elapsed = round(time.time() - t0, 1)

    if judge_res.get("ok"):
        print(f"  ✔ Consensus synthesis generated via {judge_model} ({elapsed}s)\n")
        return {"ok": True, "judge": judge_model, "elapsed_s": elapsed, "synthesis": judge_res["response"]}
    else:
        # Fallback to secondary judge if primary fails
        fallback_judge = "web-deepseek-r1" if judge_model != "web-deepseek-r1" else "web-chatgpt"
        print(f"  ⚠ {judge_model} failed, falling back to {fallback_judge}...")
        judge_res = query_single_model(fallback_judge, arbiter_prompt, timeout=90)
        if judge_res.get("ok"):
            return {"ok": True, "judge": fallback_judge, "elapsed_s": elapsed, "synthesis": judge_res["response"]}
        return {"ok": False, "error": f"Synthesis failed: {judge_res.get('error')}"}


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


def query_single_model(model: str, prompt: str, files: list = None, timeout: int = 60) -> dict:
    try:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "files": files or [],
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


def query_council(prompt: str, files: list = None, models: list = None, timeout: int = 60) -> dict:
    target_models = models or DEFAULT_MODELS
    results = {}
    print(f"\n[Council] Querying {len(target_models)} browser models simultaneously:")
    print("  Models:", ", ".join(target_models))
    print(f"  Prompt: {prompt[:80]}...")
    if files:
        print(f"  Deliverables attached ({len(files)}): {', '.join(files)}")
    print()

    for model in target_models:
        print(f"  --> Dispatching to {model}...")
        t0 = time.time()
        res = query_single_model(model, prompt, files=files, timeout=timeout)
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
    parser.add_argument("--audit", action="store_true", help="Enable Hostile Technical Audit mode (strips politeness, hunts fatal flaws)")
    parser.add_argument("--synthesize", "-s", action="store_true", help="Generate 3-part Cross-Model Consensus & Verdict matrix")
    parser.add_argument("--judge", type=str, default="web-claude-sonnet", help="Model to act as Chief Arbiter for synthesis (default: web-claude-sonnet)")
    parser.add_argument("--files", "-f", nargs="+", help="Deliverable files to attach (images, PDF, PPTX, DOCX, TXT)")
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

        raw_query = args.query
        effective_query = (AUDIT_PREPROMPT + raw_query) if args.audit else raw_query
        if args.audit:
            print("[MODE] 🔥 Hostile Technical Audit Activated (Zero-Sycophancy Enforced)\n")

        res = query_council(effective_query, files=args.files, models=args.models, timeout=args.timeout)
        print("\n=== COUNCIL RESPONSES ===")
        print(json.dumps(res, indent=2))

        if args.synthesize or args.audit:
            synthesis = synthesize_council(raw_query, res, judge_model=args.judge)
            if synthesis.get("ok"):
                print("\n" + "=" * 50)
                print("🏆 COUNCIL CONSENSUS VERDICT & SYNTHESIS")
                print("=" * 50 + "\n")
                print(synthesis["synthesis"])
                print("\n" + "=" * 50)

        return

    parser.print_help()


if __name__ == "__main__":
    main()
