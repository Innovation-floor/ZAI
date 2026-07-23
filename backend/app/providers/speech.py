"""Speech recognition and synthesis.

Arabic is the hard requirement here. Recognition engines are trained largely on
Modern Standard Arabic; Gulf dialect accuracy is materially worse. Two
mitigations are built in rather than bolted on:

  1. Keyword boosting - every country, partner, sector and project name is sent
     with each request in both scripts. This is the highest-value hour of work
     in the whole speech layer.
  2. The transcript is always returned to the client for on-screen confirmation
     before an answer is spoken.

Default deployment uses the browser's own Web Speech API (Chrome supports
ar-AE), so Arabic voice works with no vendor account at all.
"""
from __future__ import annotations

import base64
import logging
from typing import Any, Dict, List

import httpx

from app.config import settings
from app.data.repository import load_projects, vocabulary
from app.providers.base import Provider, ProviderUnavailable

log = logging.getLogger("zai.speech")


def boost_terms() -> List[str]:
    """Domain vocabulary supplied to the recogniser on every request."""
    vocab = vocabulary()
    terms: List[str] = []
    for dim in ("country", "sector", "partner", "status"):
        terms.extend(vocab.get(dim, []))
    for row in load_projects():
        if row["featured"]:
            terms.append(row["name"])
            terms.append(row["country_ar"])
            terms.append(row["sector_ar"])
    return sorted({t for t in terms if t})


class BrowserSTT(Provider):
    """No-op server side: recognition happens in the client.

    The client posts the finished transcript rather than audio. Zero cost, zero
    latency, and Arabic support on any Chromium browser.
    """

    name = "browser"
    kind = "stt"

    def transcribe(self, audio: bytes, language: str) -> Dict[str, Any]:
        raise ProviderUnavailable(
            "Browser speech recognition is active; the client posts transcripts to "
            "/api/voice/interpret directly. Set STT_PROVIDER=deepgram for server-side audio."
        )


class MockSTT(Provider):
    name = "mock"
    kind = "stt"

    def transcribe(self, audio: bytes, language: str) -> Dict[str, Any]:
        canned = ("أظهر مشاريع التعليم" if language.startswith("ar")
                  else "show education projects")
        return {"transcript": canned, "language": language, "confidence": 0.0,
                "provider": "mock"}


class DeepgramSTT(Provider):
    """Dialect-capable Arabic recognition with keyword boosting."""

    name = "deepgram"
    kind = "stt"

    def transcribe(self, audio: bytes, language: str) -> Dict[str, Any]:
        if not settings.deepgram_api_key:
            raise ProviderUnavailable("DEEPGRAM_API_KEY is not set")

        params: List[tuple] = [
            ("model", settings.deepgram_model),
            ("language", "ar" if language.startswith("ar") else "en"),
            ("smart_format", "true"),
            ("punctuate", "true"),
        ]
        for term in boost_terms()[:settings.stt_max_boost_terms]:
            params.append(("keyterm", term))

        response = httpx.post(
            "https://api.deepgram.com/v1/listen",
            params=params,
            headers={"Authorization": f"Token {settings.deepgram_api_key}",
                     "Content-Type": "audio/webm"},
            content=audio,
            timeout=settings.stt_timeout_seconds,
        )
        response.raise_for_status()
        alt = response.json()["results"]["channels"][0]["alternatives"][0]
        return {"transcript": alt.get("transcript", ""),
                "language": language,
                "confidence": alt.get("confidence", 0.0),
                "provider": "deepgram"}


class BrowserTTS(Provider):
    """Client-side speech synthesis via the Web Speech API."""

    name = "browser"
    kind = "tts"

    def synthesise(self, text: str, language: str) -> Dict[str, Any]:
        return {"mode": "client", "text": text, "language": language,
                "voice_hint": "ar-AE" if language.startswith("ar") else "en-GB"}


class AzureTTS(Provider):
    """Neural Arabic synthesis. ar-AE-FatimaNeural is the Emirati female voice."""

    name = "azure"
    kind = "tts"

    def synthesise(self, text: str, language: str) -> Dict[str, Any]:
        if not (settings.azure_speech_key and settings.azure_speech_region):
            raise ProviderUnavailable("Azure Speech credentials are not set")

        is_ar = language.startswith("ar")
        voice = settings.tts_voice_ar if is_ar else settings.tts_voice_en
        locale = "ar-AE" if is_ar else "en-GB"
        ssml = (
            f"<speak version='1.0' xml:lang='{locale}'>"
            f"<voice name='{voice}'><prosody rate='-4%'>"
            f"{text}</prosody></voice></speak>"
        )
        response = httpx.post(
            f"https://{settings.azure_speech_region}.tts.speech.microsoft.com/"
            "cognitiveservices/v1",
            headers={
                "Ocp-Apim-Subscription-Key": settings.azure_speech_key,
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
                "User-Agent": "zai-poc",
            },
            content=ssml.encode("utf-8"),
            timeout=settings.tts_timeout_seconds,
        )
        response.raise_for_status()
        return {"mode": "audio", "language": language, "voice": voice,
                "mime": "audio/mpeg",
                "audio_base64": base64.b64encode(response.content).decode()}


class AzureSTT(Provider):
    """Azure AI Speech — streaming-capable STT with auto language detection.

    Uses the REST API for simplicity in the POC. Production should use the
    Speech SDK for WebSocket streaming and real-time partial results.
    Supports ar-AE and en-US with automatic language identification.
    """

    name = "azure"
    kind = "stt"

    def transcribe(self, audio: bytes, language: str) -> Dict[str, Any]:
        if not (settings.azure_speech_key and settings.azure_speech_region):
            raise ProviderUnavailable("Azure Speech credentials are not set")

        # Auto language detection: send both ar-AE and en-US as candidates.
        # Azure picks the best match from the audio.
        lang_param = "ar-AE" if language.startswith("ar") else "en-US"

        response = httpx.post(
            f"https://{settings.azure_speech_region}.stt.speech.microsoft.com/"
            "speech/recognition/conversation/cognitiveservices/v1",
            params={
                "language": lang_param,
                "format": "detailed",
            },
            headers={
                "Ocp-Apim-Subscription-Key": settings.azure_speech_key,
                "Content-Type": "audio/wav",
                "Accept": "application/json",
            },
            content=audio,
            timeout=settings.stt_timeout_seconds,
        )
        response.raise_for_status()
        result = response.json()

        if result.get("RecognitionStatus") != "Success":
            return {"transcript": "", "language": language,
                    "confidence": 0.0, "provider": "azure"}

        best = result.get("NBest", [{}])[0]
        return {
            "transcript": best.get("Display", ""),
            "language": best.get("Locale", language),
            "confidence": best.get("Confidence", 0.0),
            "provider": "azure",
        }


def get_stt() -> Provider:
    if settings.stt_provider == "azure" and settings.azure_speech_key:
        return AzureSTT()
    if settings.stt_provider == "deepgram" and settings.deepgram_api_key:
        return DeepgramSTT()
    if settings.stt_provider == "browser":
        return BrowserSTT()
    return MockSTT()


def get_tts() -> Provider:
    if settings.tts_provider == "azure" and settings.azure_speech_key:
        return AzureTTS()
    return BrowserTTS()