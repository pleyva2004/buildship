"""API surface smoke tests — every route the app calls, in mock mode."""

import io
import struct
import wave

import pytest
from fastapi.testclient import TestClient

from agent.server import app

client = TestClient(app)


def test_health():
    data = client.get("/api/health").json()
    assert data["llm"] == "mock" and data["memory"] == "mock"


def test_listings_passthrough():
    data = client.get("/api/listings").json()
    ids = [l["listing_id"] for l in data["listings"]]
    assert ids == ["hero", "alt1", "alt2", "alt3", "alt4", "alt5", "alt6"]
    assert all("features" in l for l in data["listings"])
    assert all("traits" in l for l in data["listings"])


def test_chat_shape():
    data = client.post("/api/chat", json={"profile_id": "jake_v1", "message": "what did you find"}).json()
    assert set(data) == {"reply", "action", "recalled", "new_facts"}
    assert data["action"]["type"] == "recommend"


def test_context_and_hygiene():
    memories = client.get("/api/context/jake_v1").json()["memories"]
    assert memories
    target = memories[0]["id"]
    assert client.post("/api/memory/jake_v1/update", json={"memory_id": target, "text": "edited"}).json()["ok"]
    assert client.post(f"/api/memory/jake_v1/delete", json={"memory_id": target}).json()["ok"]
    after = client.get("/api/context/jake_v1").json()["memories"]
    assert all(m["id"] != target for m in after)


def test_interview_surface():
    q = client.post("/api/interview/next", json={"profile_id": "guest_v1", "answers": []}).json()
    assert q["id"] == "q_who" and q["total"] == 6
    res = client.post("/api/interview/answer", json={
        "profile_id": "guest_v1", "answers": [], "question_id": "q_who", "answer": "Partner + a dog",
    }).json()
    assert set(res) == {"new_facts", "profile_delta", "ranked", "next"}
    assert res["next"]["id"] == "q_dog"
    assert [r["listing_id"] for r in res["ranked"]][0] == "alt5"


def test_reset():
    assert client.post("/api/reset/jake_v1").json()["ok"]


def _tone_wav(seconds=0.4, rate=16000):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        n = int(seconds * rate)
        w.writeframes(b"".join(struct.pack("<h", int(8000 * ((i // 40) % 2 * 2 - 1))) for i in range(n)))
    return buf.getvalue()


def test_transcribe_accepts_audio_and_returns_text_key():
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        pytest.skip("faster-whisper not installed")
    r = client.post("/api/voice/transcribe", files={"audio": ("t.wav", _tone_wav(), "audio/wav")})
    assert r.status_code == 200
    assert "text" in r.json()  # a tone transcribes to "" — shape is the contract


def test_interview_finish_returns_spec():
    res = client.post("/api/interview/finish", json={
        "profile_id": "guest_v1",
        "answers": [{"questionId": "q_light", "answer": "Cozy & warm"}],
    }).json()
    spec = res["style_spec"]
    assert spec["aesthetic_name"] == "warm & collected"
    assert len(spec["palette_hex"]) >= 3
