"""HTTP surface."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from app.config import settings
from app.core import aggregates, engine
from app.core.engine import sessions
from app.data.repository import load_projects, vocabulary
from app.providers import avatar as avatar_mod
from app.providers import documents as doc_mod
from app.providers import llm as llm_mod
from app.providers import speech as speech_mod
from app.providers.base import ProviderUnavailable

log = logging.getLogger("zai.api")
router = APIRouter()

_llm = llm_mod.get_llm()
_stt = speech_mod.get_stt()
_tts = speech_mod.get_tts()
_avatar = avatar_mod.get_avatar()
_extractor = doc_mod.get_extractor()


# --------------------------------------------------------------------------
# health
# --------------------------------------------------------------------------
@router.get("/health/live", tags=["health"])
def liveness() -> Dict[str, str]:
    return {"status": "alive"}


@router.get("/health/ready", tags=["health"])
def readiness() -> Dict[str, Any]:
    rows = load_projects(settings.dataset_size)
    return {
        "status": "ready",
        "environment": settings.environment,
        "dataset": {"projects": len(rows),
                    "featured": sum(1 for r in rows if r["featured"])},
        "sessions": sessions.count(),
        "providers": {
            "llm": _llm.name, "stt": _stt.name, "tts": _tts.name,
            "avatar": _avatar.name, "documents": _extractor.name,
        },
        # Detailed health for the active LLM. For Ollama this reports whether
        # the daemon is reachable and which models are actually pulled — the
        # two things that break a self-hosted setup.
        "llm_detail": _llm.health(),
    }


# --------------------------------------------------------------------------
# portfolio
# --------------------------------------------------------------------------
@router.get("/portfolio/brief", tags=["portfolio"])
def brief() -> Dict[str, Any]:
    """Today's Executive Brief. Pre-computed; served before any question."""
    return aggregates.executive_brief(load_projects(settings.dataset_size))


@router.get("/portfolio/overview", tags=["portfolio"])
def overview() -> Dict[str, Any]:
    rows = load_projects(settings.dataset_size)
    return {
        "summary": aggregates.summarise(rows),
        "distributions": aggregates.distributions(rows),
        "map": aggregates.map_payload(rows),
        "vocabulary": vocabulary(settings.dataset_size),
    }


@router.get("/portfolio/projects/{project_id}", tags=["portfolio"])
def project_detail(project_id: str) -> Dict[str, Any]:
    for row in load_projects(settings.dataset_size):
        if row["id"] == project_id:
            return row
    raise HTTPException(status_code=404, detail="Project not found")


# --------------------------------------------------------------------------
# conversation
# --------------------------------------------------------------------------
class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    session_id: Optional[str] = None


@router.post("/query", tags=["conversation"])
def query(payload: QueryRequest) -> Dict[str, Any]:
    session = sessions.get_or_create(payload.session_id)
    return engine.run_turn(session, payload.question, _llm)


@router.post("/session/reset", tags=["conversation"])
def reset_session(session_id: Optional[str] = None) -> Dict[str, Any]:
    session = sessions.get_or_create(session_id)
    session.state = engine.QueryState()
    session.history.clear()
    return {"session_id": session.id, "reset": True}


# --------------------------------------------------------------------------
# voice
# --------------------------------------------------------------------------
@router.get("/voice/config", tags=["voice"])
def voice_config() -> Dict[str, Any]:
    """Tells the client whether to recognise locally or post audio."""
    return {
        "stt_provider": _stt.name,
        "tts_provider": _tts.name,
        "client_side_stt": _stt.name == "browser",
        "client_side_tts": _tts.name == "browser",
        "languages": [
            {"code": "en-GB", "label": "English"},
            {"code": "ar-AE", "label": "العربية"},
        ],
        "boost_terms": speech_mod.boost_terms()[:settings.stt_max_boost_terms],
    }


@router.post("/voice/transcribe", tags=["voice"])
async def transcribe(audio: UploadFile = File(...),
                     language: str = Form("en")) -> Dict[str, Any]:
    content = await audio.read()
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Audio payload too large")
    try:
        return await run_in_threadpool(_stt.transcribe, content, language)
    except ProviderUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


class SpeakRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    language: str = "en"


@router.post("/voice/speak", tags=["voice"])
def speak(payload: SpeakRequest) -> Dict[str, Any]:
    try:
        return _tts.synthesise(payload.text, payload.language)
    except ProviderUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


# --------------------------------------------------------------------------
# avatar
# --------------------------------------------------------------------------
class AvatarSessionRequest(BaseModel):
    language: str = "en"


@router.post("/avatar/session", tags=["avatar"])
def avatar_session(payload: AvatarSessionRequest) -> Dict[str, Any]:
    return _avatar.create_session(payload.language)


class AvatarSpeakRequest(BaseModel):
    session_id: str = ""
    text: str = Field(min_length=1, max_length=4000)


@router.post("/avatar/speak", tags=["avatar"])
def avatar_speak(payload: AvatarSpeakRequest) -> Dict[str, Any]:
    return _avatar.speak(payload.session_id, payload.text)


@router.delete("/avatar/session/{session_id}", tags=["avatar"])
def avatar_close(session_id: str) -> Dict[str, Any]:
    return _avatar.close_session(session_id)


# --------------------------------------------------------------------------
# documents
# --------------------------------------------------------------------------
@router.post("/documents/upload", tags=["documents"])
async def upload_document(file: UploadFile = File(...),
                          session_id: str = Form("")) -> Dict[str, Any]:
    content = await file.read()
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Document too large")

    # Extraction and summarisation are synchronous vendor calls taking tens of
    # seconds. Inside an async endpoint they would block the event loop and
    # stall every other request, including health checks.
    try:
        extracted = await run_in_threadpool(
            _extractor.extract, content, file.filename or "document.pdf")
    except ProviderUnavailable as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    language = doc_mod.detect_language(extracted["text"])
    # Summary is generated on upload, not on request: "summarise this report"
    # must return instantly, not run inference while the executive waits.
    summary = await run_in_threadpool(
        _llm.summarise_document, extracted["text"], language)

    session = sessions.get_or_create(session_id or None)
    doc_id = f"D{len(session.documents) + 1:03d}"
    session.documents[doc_id] = {
        "id": doc_id, "filename": file.filename, "text": extracted["text"],
        "pages": extracted["pages"], "language": language, "summary": summary,
    }
    return {"session_id": session.id, "document_id": doc_id,
            "filename": file.filename, "pages": extracted["pages"],
            "language": language, "summary": summary,
            "characters": len(extracted["text"]), "provider": extracted["provider"]}


class DocumentQuestion(BaseModel):
    session_id: str
    document_id: str
    question: str = Field(min_length=1, max_length=1000)


@router.post("/documents/ask", tags=["documents"])
def ask_document(payload: DocumentQuestion) -> Dict[str, Any]:
    session = sessions.get_or_create(payload.session_id)
    document = session.documents.get(payload.document_id)
    if not document:
        raise HTTPException(
            status_code=404,
            detail=("Document not found in this session. Sessions are held in "
                    "process memory, so this happens if the API restarted or is "
                    "running more than one worker. Re-upload the document."))
    language = engine.detect_language(payload.question) or document["language"]
    answer = _llm.answer_document(document["text"], payload.question, language)
    return {"document_id": payload.document_id, "question": payload.question,
            "answer": answer, "language": language}


@router.get("/documents", tags=["documents"])
def list_documents(session_id: str) -> Dict[str, Any]:
    session = sessions.get_or_create(session_id)
    return {"session_id": session.id, "documents": [
        {"id": d["id"], "filename": d["filename"], "pages": d["pages"],
         "language": d["language"]} for d in session.documents.values()]}


# --------------------------------------------------------------------------
# demo mode
# --------------------------------------------------------------------------
DEMO_SCRIPT: List[Dict[str, str]] = [
    {"beat": "welcome", "question": "Show me the entire portfolio"},
    {"beat": "education", "question": "Show education projects"},
    {"beat": "water", "question": "Show water projects in Africa"},
    {"beat": "compare", "question": "Compare Jordan and Egypt"},
    {"beat": "attention", "question": "Which projects require executive attention?"},
    {"beat": "arabic", "question": "أظهر مشاريع التعليم"},
]


@router.get("/demo/script", tags=["demo"])
def demo_script() -> Dict[str, Any]:
    return {"beats": DEMO_SCRIPT, "duration_estimate_seconds": len(DEMO_SCRIPT) * 30}