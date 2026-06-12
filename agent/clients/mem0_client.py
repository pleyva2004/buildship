"""mem0 client — MOCK | LIVE (design 01 §3).

Interface: seed / search / all / add. Memories are atomic facts with a
category in {life_situation, taste, mood_board, constraint} — the category
drives the app's context-panel grouping.

MOCK: in-memory store seeded from agent/profiles/*.json; naive keyword scoring.
      Deterministic — doubles as the stage fallback.
LIVE: mem0 platform REST API (stdlib urllib, zero deps). profile_id -> user_id.
"""

import json
import re
import urllib.request
from pathlib import Path

from agent import config

API_BASE = "https://api.mem0.ai/v1"

PROFILE_FILES = {
    "jake_v1": config.REPO_ROOT / "agent" / "profiles" / "jake.json",
    "pablo_v1": config.REPO_ROOT / "agent" / "profiles" / "pablo.json",
}

_STOPWORDS = {"the", "a", "an", "in", "to", "for", "of", "and", "we", "i", "my", "is", "are"}


def flatten_profile(profile: dict) -> list[dict]:
    """Profile seed JSON -> atomic memory facts [{text, category}]."""
    name = profile["name"]
    life = profile["life_situation"]
    facts = [
        {"text": f"{name}: {life['summary']}", "category": "life_situation"},
        {"text": f"Household: {life['household']}", "category": "life_situation"},
        {"text": f"Budget band: {life['budget_band']}", "category": "life_situation"},
    ]
    facts += [{"text": f"Must-have: {m}", "category": "life_situation"} for m in life["must_haves"]]
    facts += [{"text": t, "category": "taste"} for t in profile["taste_descriptors"]]
    facts += [
        {
            "text": f"Mood board: “{ref['label']}” ({ref['source']}, via {ref['imported_via']})",
            "category": "mood_board",
        }
        for ref in profile["mood_board_refs"]
    ]
    facts += [{"text": c, "category": "constraint"} for c in profile["hard_constraints"]]
    return facts


class Mem0Client:
    def __init__(self):
        self.live = config.backend("mem0") == "live"
        self._store: dict[str, list[dict]] = {}  # mock store
        if not self.live:
            for pid, path in PROFILE_FILES.items():
                self.seed(pid, flatten_profile(json.loads(path.read_text())))

    # -- interface ------------------------------------------------------

    def seed(self, profile_id: str, facts: list[dict]) -> int:
        if self.live:
            for fact in facts:
                self._api(
                    "POST",
                    "/memories/",
                    {
                        "messages": [{"role": "user", "content": fact["text"]}],
                        "user_id": profile_id,
                        "metadata": {"category": fact["category"]},
                        "infer": False,  # store verbatim — seeds are already atomic
                    },
                )
            return len(facts)
        self._store[profile_id] = [
            {"id": f"{profile_id}-{i}", "text": f["text"], "category": f["category"], "score": 1.0}
            for i, f in enumerate(facts)
        ]
        return len(facts)

    def search(self, profile_id: str, query: str, k: int = 4) -> list[dict]:
        if self.live:
            data = self._api("POST", "/memories/search/", {"query": query, "user_id": profile_id, "limit": k})
            return [self._norm(m) for m in data[:k]]  # API can ignore limit; enforce here
        # mock: keyword-overlap scoring, deterministic tie-break by id
        words = {w for w in re.findall(r"[a-z']+", query.lower()) if w not in _STOPWORDS}
        scored = []
        for mem in self._store.get(profile_id, []):
            hits = sum(1 for w in words if w in mem["text"].lower())
            if hits:
                scored.append({**mem, "score": hits})
        scored.sort(key=lambda m: (-m["score"], m["id"]))
        return scored[:k]

    def all(self, profile_id: str) -> list[dict]:
        if self.live:
            data = self._api("GET", f"/memories/?user_id={profile_id}")
            return [self._norm(m) for m in data]
        return list(self._store.get(profile_id, []))

    def add(
        self,
        profile_id: str,
        text: str,
        category: str = "life_situation",
        source: str = "stated",
        question_id: str | None = None,
    ) -> dict:
        """One new fact learned mid-conversation (interview or property talk).
        source: stated | inferred — honest provenance, rendered in the rails."""
        metadata = {"category": category, "source": source}
        if question_id:
            metadata["question_id"] = question_id
        if self.live:
            self._api(
                "POST",
                "/memories/",
                {
                    "messages": [{"role": "user", "content": text}],
                    "user_id": profile_id,
                    "metadata": metadata,
                    "infer": False,
                },
            )
            return {"text": text, "category": category, "source": source}
        mem = {
            "id": f"{profile_id}-{len(self._store.get(profile_id, []))}",
            "text": text,
            "category": category,
            "source": source,
            "score": 1.0,
        }
        self._store.setdefault(profile_id, []).append(mem)
        return mem

    def update(self, profile_id: str, memory_id: str, text: str) -> None:
        """Memory hygiene: rail edit/confirm → revised fact text."""
        if self.live:
            self._api("PUT", f"/memories/{memory_id}/", {"text": text})
            return
        for mem in self._store.get(profile_id, []):
            if mem["id"] == memory_id:
                mem["text"] = text

    def delete(self, profile_id: str, memory_id: str) -> None:
        """Memory hygiene: rail remove → gone from mem0 too."""
        if self.live:
            self._api("DELETE", f"/memories/{memory_id}/")
            return
        self._store[profile_id] = [
            m for m in self._store.get(profile_id, []) if m["id"] != memory_id
        ]

    def delete_all(self, profile_id: str) -> None:
        """Reset before re-seeding (idempotent rehearsals)."""
        if self.live:
            self._api("DELETE", f"/memories/?user_id={profile_id}")
        else:
            self._store[profile_id] = []

    # -- internals ------------------------------------------------------

    @staticmethod
    def _norm(m: dict) -> dict:
        meta = m.get("metadata") or {}
        return {
            "id": m.get("id", ""),
            "text": m.get("memory") or m.get("text", ""),
            "category": meta.get("category", "life_situation"),
            "source": meta.get("source", "stated"),
            "score": m.get("score", 0.0),
        }

    def _api(self, method: str, path: str, body: dict | None = None):
        if not config.MEM0_API_KEY:
            raise RuntimeError("MEM0_API_KEY not set")
        req = urllib.request.Request(
            API_BASE + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers={
                "Authorization": f"Token {config.MEM0_API_KEY}",
                "Content-Type": "application/json",
            },
            method=method,
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read()
        return json.loads(raw) if raw else None
