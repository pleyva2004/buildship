"""FastAPI bridge — thin shell over AgentSession (design 04 §5).

Routes only translate HTTP <-> AgentSession; no agent logic lives here.
Run:  make serve   ->  http://localhost:8001  (docs at /docs)
The Vite dev server proxies /api here.
"""

import io

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from agent import config, interview
from agent.clients.mem0_client import Mem0Client
from agent.core import AgentSession, load_listings

app = FastAPI(title="VISTA Agent API", version="0.1.0")

memory = Mem0Client()  # shared across sessions (mock self-seeds at startup)
sessions: dict[str, AgentSession] = {}


class ChatRequest(BaseModel):
    profile_id: str = "jake_v1"
    message: str


class Memory(BaseModel):
    id: str
    text: str
    category: str
    score: float = 0.0


class ChatTurn(BaseModel):
    reply: str
    action: dict | None = None
    recalled: list[Memory]
    new_facts: list[dict] = []  # learned mid-conversation → "✓ Saved to memory" chips
    researching: list[str] = []  # background area research underway
    trace: list[str] = []  # tool activity this turn ("behind the scenes")


@app.post("/api/chat", response_model=ChatTurn)
def chat(req: ChatRequest):
    session = sessions.setdefault(req.profile_id, AgentSession(req.profile_id, memory))
    return session.turn(req.message)


@app.get("/api/context/{profile_id}")
def context(profile_id: str):
    return {"profile_id": profile_id, "memories": memory.all(profile_id)}


@app.get("/api/listings")
def listings():
    return load_listings()


@app.post("/api/reset/{profile_id}")
def reset(profile_id: str):
    """Fresh conversation for rehearsals; memories are untouched."""
    sessions.pop(profile_id, None)
    interview.reset(profile_id)
    return {"ok": True}


# ---- interview surface (designs 08b §6, 09 §4) -------------------------------
# Stateless: the client passes its answers[] on every call. Shapes mirror
# app/src/mock/interview.js exactly — the app falls back to that twin on failure.


class InterviewNextRequest(BaseModel):
    profile_id: str = "jake_v1"
    answers: list[dict] = []


class InterviewAnswerRequest(BaseModel):
    profile_id: str = "jake_v1"
    answers: list[dict] = []
    question_id: str
    answer: str


@app.post("/api/interview/next")
def interview_next(req: InterviewNextRequest):
    return interview.next_question(req.profile_id, req.answers)


@app.post("/api/interview/answer")
def interview_answer(req: InterviewAnswerRequest):
    return interview.record_answer(
        req.profile_id, req.answers, req.question_id, req.answer, memory
    )


@app.post("/api/interview/finish")
def interview_finish(req: InterviewNextRequest):
    """The exit artifact: a style spec distilled from THIS conversation.
    Returned, never persisted — /specs stays frozen (CLAUDE.md §4)."""
    return {"style_spec": interview.finish_profile(req.profile_id, req.answers, memory)}


# ---- voice v1 (design 09 §5): audio blob -> transcript ------------------------
# Local faster-whisper — offline, zero keys, stage-wifi-proof. Lazy-loaded so the
# server runs without the dep; the client treats any failure as "fall back to text".

_whisper = None


def _whisper_model():
    global _whisper
    if _whisper is None:
        from faster_whisper import WhisperModel  # lazy: optional dependency

        _whisper = WhisperModel("base.en", device="cpu", compute_type="int8")
    return _whisper


@app.post("/api/voice/transcribe")
async def voice_transcribe(audio: UploadFile = File(...)):
    try:
        model = _whisper_model()
    except Exception as exc:
        raise HTTPException(501, f"speech-to-text unavailable ({exc})")
    data = await audio.read()
    try:
        segments, _ = model.transcribe(io.BytesIO(data), language="en", beam_size=1, vad_filter=True)
        text = " ".join(s.text.strip() for s in segments).strip()
    except Exception as exc:
        raise HTTPException(422, f"could not transcribe audio ({exc})")
    return {"text": text}


# ---- memory hygiene (design 08 — rail confirm / edit / remove) ---------------


class MemoryUpdateRequest(BaseModel):
    memory_id: str
    text: str


class MemoryDeleteRequest(BaseModel):
    memory_id: str


@app.post("/api/memory/{profile_id}/update")
def memory_update(profile_id: str, req: MemoryUpdateRequest):
    memory.update(profile_id, req.memory_id, req.text)
    return {"ok": True}


@app.post("/api/memory/{profile_id}/delete")
def memory_delete(profile_id: str, req: MemoryDeleteRequest):
    memory.delete(profile_id, req.memory_id)
    return {"ok": True}


# ---- background research status — the chat bubble polls this until research
# settles ('pending' always clears, even on a failed run), then flips to done.


@app.get("/api/research/status")
def research_status(areas: str = ""):
    from agent import researcher

    names = [a.strip() for a in areas.split(",") if a.strip()]
    return {"areas": {a: researcher.status(a) for a in names}}


@app.get("/api/health")
def health():
    return {
        "llm": config.backend("nebius"),
        "memory": config.backend("mem0"),
        "model": config.NEBIUS_MODEL,
    }
