"""
Agent Chrome — Local Multi-LLM Browser Session Bridge Server
Exposes an OpenAI-compatible /v1/chat/completions endpoint powered by your
live, visible desktop Chrome tabs via Chrome DevTools Protocol (CDP).
"""

import asyncio
import json
import os
import sys
import time
import urllib.request
import uuid
from contextlib import asynccontextmanager
from typing import Dict, List, Optional

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from playwright.async_api import Browser, BrowserContext, Playwright, async_playwright

SELECTORS_PATH = os.path.join(os.path.dirname(__file__), "selectors.json")

def load_providers() -> dict:
    if os.path.exists(SELECTORS_PATH):
        with open(SELECTORS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

PROVIDER_TABS = load_providers()
PROVIDER_LOCKS: Dict[str, asyncio.Lock] = {
    model_name: asyncio.Lock() for model_name in PROVIDER_TABS
}

CDP_PORT = int(os.environ.get("CHROME_CDP_PORT", 9222))
SERVER_PORT = int(os.environ.get("BRIDGE_SERVER_PORT", 8000))


async def check_cdp_available() -> bool:
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{CDP_PORT}/json/version")
        with urllib.request.urlopen(req, timeout=1.0) as r:
            return r.status == 200
    except Exception:
        return False


class BridgeState:
    def __init__(self):
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None

    async def get_context(self) -> BrowserContext:
        if self.browser and self.browser.is_connected() and self.context:
            return self.context

        if not await check_cdp_available():
            raise RuntimeError(
                f"Agent Chrome is not running on port {CDP_PORT}. "
                "Please launch Agent Chrome from your desktop so you can see your live tabs."
            )

        if not self.playwright:
            self.playwright = await async_playwright().start()

        try:
            self.browser = await self.playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{CDP_PORT}")
            if not self.browser.contexts:
                self.context = await self.browser.new_context()
            else:
                self.context = self.browser.contexts[0]
            return self.context
        except Exception as exc:
            raise RuntimeError(f"Cannot connect to Agent Chrome over CDP on port {CDP_PORT}: {exc}")

    async def close(self):
        if self.browser:
            try:
                await self.browser.close()
            except Exception:
                pass
        if self.playwright:
            try:
                await self.playwright.stop()
            except Exception:
                pass


bridge_state = BridgeState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await bridge_state.get_context()
        print(f"[Bridge] Connected to Agent Chrome via CDP port {CDP_PORT} successfully.")
    except Exception as e:
        print(f"[Bridge] Waiting for Agent Chrome: {e}")
    yield
    await bridge_state.close()
    print("[Bridge] CDP connection closed.")


app = FastAPI(
    title="Agent Chrome — Multi-LLM Browser Session Bridge",
    version="1.0.0",
    description="Query ChatGPT, Claude, DeepSeek, Gemini, and Z.ai live in your visible desktop browser.",
    lifespan=lifespan
)


class Message(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    files: Optional[List[str]] = []
    stream: bool = False
    temperature: Optional[float] = 0.7


async def query_browser_tab(model_key: str, prompt: str, files: Optional[List[str]] = None, timeout: int = 60) -> str:
    global PROVIDER_TABS, PROVIDER_LOCKS
    if model_key not in PROVIDER_TABS:
        PROVIDER_TABS = load_providers()
        if model_key not in PROVIDER_TABS:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown model '{model_key}'. Supported: {list(PROVIDER_TABS.keys())}"
            )
        PROVIDER_LOCKS[model_key] = asyncio.Lock()

    config = PROVIDER_TABS[model_key]
    lock = PROVIDER_LOCKS[model_key]

    async with lock:
        try:
            context = await bridge_state.get_context()

            # Find matching open tab
            target_page = next(
                (p for p in context.pages if config["url_match"] in p.url),
                None
            )

            # Auto-open tab if missing
            if not target_page:
                url = config["default_url"]
                print(f"[Bridge] Opening tab for {model_key}: {url}")
                target_page = await context.new_page()
                await target_page.goto(url, wait_until="domcontentloaded")
                await asyncio.sleep(3)

            await target_page.bring_to_front()

            # Record baseline response count & last text
            resp_sel = config["response_selector"]
            baseline_info = await target_page.evaluate(f"""() => {{
                const msgs = Array.from(document.querySelectorAll("{resp_sel}"));
                return {{
                    count: msgs.length,
                    text: msgs.length > 0 ? (msgs[msgs.length - 1].innerText || '').trim() : ''
                }};
            }}""")
            baseline_count = baseline_info.get("count", 0)
            baseline_text = baseline_info.get("text", "")

            # 1. Attach Deliverables (Images, Docs, PPTX, PDFs) if provided
            if files:
                valid_files = [os.path.abspath(f) for f in files if os.path.exists(f)]
                if not valid_files:
                    print(f"[Bridge] Warning: No existing files found in {files}")
                else:
                    print(f"[Bridge] Attaching {len(valid_files)} deliverable(s) to {model_key}...")
                    try:
                        if config.get("upload_trigger_selector"):
                            # Menu-triggered uploads (e.g. Gemini)
                            trigger_btn = target_page.locator(config["upload_trigger_selector"]).first
                            if await trigger_btn.count() > 0:
                                await trigger_btn.click()
                                await asyncio.sleep(0.6)
                                if config.get("file_chooser_selector"):
                                    chooser_item = target_page.locator(config["file_chooser_selector"]).first
                                    if await chooser_item.count() > 0:
                                        async with target_page.expect_file_chooser(timeout=4000) as fc_info:
                                            await chooser_item.click()
                                        fc = await fc_info.value
                                        await fc.set_files(valid_files)
                                else:
                                    inps = await target_page.locator(config.get("file_input_selector", "input[type='file']")).all()
                                    if inps:
                                        await inps[0].set_input_files(valid_files)
                        else:
                            # Direct file inputs (Claude, ChatGPT, DeepSeek, Z.ai)
                            inps = await target_page.locator(config.get("file_input_selector", "input[type='file']")).all()
                            if inps:
                                # For ChatGPT, last input is general deliverables/files
                                target_inp = inps[-1] if ("chatgpt" in model_key and len(inps) > 1) else inps[0]
                                await target_inp.set_input_files(valid_files)
                            else:
                                print(f"[Bridge] Warning: No file input found on {model_key}")
                        # Wait for file upload & preview chips to settle
                        await asyncio.sleep(2.5)
                    except Exception as attach_err:
                        print(f"[Bridge] Error attaching files to {model_key}: {attach_err}")

            # 2. Focus and enter prompt
            input_box = target_page.locator(config["input_selector"]).first
            await input_box.wait_for(state="visible", timeout=8000)
            await input_box.click()
            await asyncio.sleep(0.2)

            try:
                await input_box.fill(prompt)
            except Exception:
                await target_page.keyboard.insert_text(prompt)

            await asyncio.sleep(0.3)

            # 3. Submit query (prefer Send button if present, else Enter)
            send_btn = None
            if config.get("send_button_selector"):
                send_btn = target_page.locator(config["send_button_selector"]).first
            if send_btn and await send_btn.count() > 0 and await send_btn.is_visible() and await send_btn.is_enabled():
                try:
                    await send_btn.click()
                except Exception:
                    await target_page.keyboard.press("Enter")
            else:
                await target_page.keyboard.press("Enter")

            # Polling: wait until new response appears and stabilizes
            last_text = ""
            stable_ticks = 0
            start_wait = time.time()
            stop_sel = config.get("stop_selector", "")

            while (time.time() - start_wait) < timeout:
                await asyncio.sleep(1.0)
                try:
                    curr_info = await target_page.evaluate(f"""() => {{
                        const msgs = Array.from(document.querySelectorAll("{resp_sel}"));
                        const stopEl = "{stop_sel}" ? document.querySelector("{stop_sel}") : null;
                        const isGenerating = stopEl !== null && stopEl.offsetParent !== null;
                        return {{
                            count: msgs.length,
                            text: msgs.length > 0 ? (msgs[msgs.length - 1].innerText || '').trim() : '',
                            is_generating: isGenerating
                        }};
                    }}""")
                    curr_count = curr_info.get("count", 0)
                    curr_text = curr_info.get("text", "")
                    is_generating = curr_info.get("is_generating", False)
                except Exception:
                    curr_count = 0
                    curr_text = ""
                    is_generating = False

                is_new = (curr_count > baseline_count) or (curr_text and curr_text != baseline_text)
                if is_new and curr_text:
                    if is_generating:
                        # Actively generating or deep thinking, do not stop early
                        stable_ticks = 0
                        last_text = curr_text
                    elif curr_text == last_text:
                        stable_ticks += 1
                        if stable_ticks >= 2:
                            return curr_text
                    else:
                        stable_ticks = 0
                        last_text = curr_text

            if last_text:
                return last_text

            raise HTTPException(status_code=504, detail=f"Timed out waiting for response from {model_key}")

        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=500, detail=f"Error executing browser query: {e}")


@app.post("/v1/chat/completions")
async def chat_completions(req: ChatCompletionRequest):
    formatted_prompt = "\n".join([f"{m.role.upper()}: {m.content}" for m in req.messages])
    reply_text = await query_browser_tab(req.model, formatted_prompt, files=req.files)

    return {
        "id": f"chatcmpl-{uuid.uuid4()}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": req.model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": reply_text},
            "finish_reason": "stop"
        }]
    }


@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {"id": model_name, "object": "model", "owned_by": "agent_chrome"}
            for model_name in PROVIDER_TABS
        ]
    }


@app.get("/health")
async def health():
    connected = False
    try:
        await bridge_state.get_context()
        connected = bridge_state.browser is not None and bridge_state.browser.is_connected()
    except Exception:
        pass
    return {
        "status": "ok",
        "cdp_connected": connected,
        "cdp_port": CDP_PORT,
        "providers": list(PROVIDER_TABS.keys())
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=SERVER_PORT)
