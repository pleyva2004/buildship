"""FastAPI bridge — thin shell over AgentSession (design 04 §5).

Routes only translate HTTP <-> AgentSession; no agent logic lives here.
Run:  make serve   ->  http://localhost:8001  (docs at /docs)
The Vite dev server proxies /api here.
"""

from fastapi import FastAPI
from pydantic import BaseModel

from agent import config
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
    return {"ok": True}


@app.get("/api/health")
def health():
    return {
        "llm": config.backend("nebius"),
        "memory": config.backend("mem0"),
        "model": config.NEBIUS_MODEL,
    }
