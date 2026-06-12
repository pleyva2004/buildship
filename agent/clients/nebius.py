"""Nebius Token Factory LLM client — MOCK | LIVE (design 04 §3).

One function: chat(messages) -> str. Live path is OpenAI-compatible chat
completions. Mock path serves canned, deterministic replies keyed by keywords —
it doubles as the on-stage fallback, so a live failure degrades to mock for
that turn instead of stalling the demo.
"""

import json
import urllib.request

from agent import config

_TURNS = None  # lazy-loaded mock turns


def chat(messages: list[dict], temperature: float = 0.2, model: str | None = None) -> str:
    """One chat completion. messages = [{role, content}, ...] incl. system."""
    if config.backend("nebius") == "live":
        try:
            return _chat_live(messages, temperature, model or config.NEBIUS_MODEL)
        except Exception as exc:  # never stall the demo on a network blip
            print(f"[nebius] live call failed ({exc}); falling back to mock turn")
    return _chat_mock(messages)


def _chat_live(messages: list[dict], temperature: float, model: str) -> str:
    if not config.NEBIUS_API_KEY:
        raise RuntimeError("NEBIUS_API_KEY not set")
    body = json.dumps(
        {"model": model, "messages": messages, "temperature": temperature}
    ).encode()
    req = urllib.request.Request(
        config.NEBIUS_BASE_URL.rstrip("/") + "/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {config.NEBIUS_API_KEY}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.load(resp)
    return data["choices"][0]["message"]["content"]


def _chat_mock(messages: list[dict]) -> str:
    """Deterministic canned reply: first turn whose keywords all appear in the
    last user message wins; turns are checked in file order; falls back to the
    'default' turn."""
    global _TURNS
    if _TURNS is None:
        _TURNS = json.loads((config.MOCKS_DIR / "turns.json").read_text())
    last_user = next(
        (m["content"].lower() for m in reversed(messages) if m["role"] == "user"), ""
    )
    for turn in _TURNS["turns"]:
        if turn["keywords"] and all(kw in last_user for kw in turn["keywords"]):
            return turn["reply"]
    return _TURNS["default"]
