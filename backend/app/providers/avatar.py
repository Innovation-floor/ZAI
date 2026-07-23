"""AI Avatar.

A photorealistic talking presence is a vendor dependency, not something built
in-house. That makes it the single largest delivery risk in the project:
someone else's uptime, someone else's latency, and someone else's approval
queue on the critical path.

Three implementations behind one interface:
  heygen  - self-serve streaming, primary
  azure   - platform-native, swap in if custom-avatar approval completes
  static  - branded portrait plus speech, guaranteed to work

The static fallback is not a consolation prize. It is the reason the executive
demonstration cannot fail: if streaming degrades, flip AVATAR_PROVIDER=static
and the product still works end to end.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

import httpx

from app.config import settings
from app.providers.base import Provider, ProviderUnavailable

log = logging.getLogger("zai.avatar")


class StaticAvatar(Provider):
    name = "static"
    kind = "avatar"

    def create_session(self, language: str) -> Dict[str, Any]:
        # If looping videos are configured the client uses those; otherwise it
        # animates the SVG avatar with viseme-approximate lip movement driven
        # by the speech synthesis timeline.
        if settings.avatar_model:
            mode = "model3d"
        elif settings.avatar_idle_video:
            mode = "video"
        elif settings.avatar_photo:
            mode = "photo"
        else:
            mode = "static"

        return {
            "mode": mode,
            "photo_url": settings.avatar_photo,
            "model_url": settings.avatar_model,
            "model_zoom": settings.avatar_model_zoom,
            "model_offset_y": settings.avatar_model_offset_y,
            "mouth": {
                "x": settings.avatar_mouth_x, "y": settings.avatar_mouth_y,
                "w": settings.avatar_mouth_w, "h": settings.avatar_mouth_h,
                "gain": settings.avatar_mouth_gain,
            },
            "portrait_url": settings.avatar_portrait_url,
            "idle_video": settings.avatar_idle_video,
            # Falls back to the idle clip so a single loop is enough to start.
            "speaking_video": settings.avatar_speaking_video or settings.avatar_idle_video,
            "display_name": settings.avatar_display_name,
            "language": language,
        }

    def speak(self, session_id: str, text: str) -> Dict[str, Any]:
        return {"mode": "static", "text": text, "delivered": True}

    def close_session(self, session_id: str) -> Dict[str, Any]:
        return {"closed": True}


class HeyGenAvatar(Provider):
    """Streaming interactive avatar over WebRTC (LiveKit transport)."""

    name = "heygen"
    kind = "avatar"

    BASE = "https://api.heygen.com"

    def __init__(self) -> None:
        self._fallback = StaticAvatar()

    def _headers(self) -> Dict[str, str]:
        if not settings.heygen_api_key:
            raise ProviderUnavailable("HEYGEN_API_KEY is not set")
        return {"x-api-key": settings.heygen_api_key,
                "content-type": "application/json"}

    def create_session(self, language: str) -> Dict[str, Any]:
        try:
            token = httpx.post(f"{self.BASE}/v1/streaming.create_token",
                               headers=self._headers(), timeout=20).json()
            session_token = token["data"]["token"]

            new = httpx.post(
                f"{self.BASE}/v1/streaming.new",
                headers={"authorization": f"Bearer {session_token}",
                         "content-type": "application/json"},
                json={"avatar_id": settings.heygen_avatar_id,
                      "quality": settings.heygen_quality,
                      "version": "v2"},
                timeout=30,
            ).json()["data"]

            httpx.post(f"{self.BASE}/v1/streaming.start",
                       headers={"authorization": f"Bearer {session_token}",
                                "content-type": "application/json"},
                       json={"session_id": new["session_id"]}, timeout=30)

            return {"mode": "stream", "provider": "heygen",
                    "session_id": new["session_id"],
                    # LiveKit room URL and join token, consumed by the client.
                    "url": new["url"], "access_token": new["access_token"],
                    "portrait_url": settings.avatar_portrait_url,
                    "display_name": settings.avatar_display_name,
                    "language": language}
        except Exception as exc:  # noqa: BLE001 - never fail the session
            log.warning("heygen session failed, degrading to static avatar: %s", exc)
            payload = self._fallback.create_session(language)
            payload["degraded_from"] = "heygen"
            return payload

    def speak(self, session_id: str, text: str) -> Dict[str, Any]:
        try:
            token = httpx.post(f"{self.BASE}/v1/streaming.create_token",
                               headers=self._headers(), timeout=20).json()["data"]["token"]
            httpx.post(f"{self.BASE}/v1/streaming.task",
                       headers={"authorization": f"Bearer {token}",
                                "content-type": "application/json"},
                       json={"session_id": session_id, "text": text,
                             "task_type": "repeat"}, timeout=30)
            return {"mode": "stream", "delivered": True}
        except Exception as exc:  # noqa: BLE001
            log.warning("heygen speak failed: %s", exc)
            return self._fallback.speak(session_id, text)

    def close_session(self, session_id: str) -> Dict[str, Any]:
        try:
            token = httpx.post(f"{self.BASE}/v1/streaming.create_token",
                               headers=self._headers(), timeout=20).json()["data"]["token"]
            httpx.post(f"{self.BASE}/v1/streaming.stop",
                       headers={"authorization": f"Bearer {token}",
                                "content-type": "application/json"},
                       json={"session_id": session_id}, timeout=20)
        except Exception as exc:  # noqa: BLE001
            log.warning("heygen close failed: %s", exc)
        return {"closed": True}


class AzureAvatar(Provider):
    """Azure text-to-speech avatar.

    Real-time avatar requires the S0 tier and outbound WebRTC to
    relay.communication.microsoft.com on UDP 3478 and TCP 443. Confirm that
    firewall rule on the demonstration network before week three.
    """

    name = "azure"
    kind = "avatar"

    def __init__(self) -> None:
        self._fallback = StaticAvatar()

    def create_session(self, language: str) -> Dict[str, Any]:
        if not (settings.azure_speech_key and settings.azure_speech_region):
            log.warning("azure avatar requested without credentials; using static")
            return self._fallback.create_session(language)
        try:
            response = httpx.get(
                f"https://{settings.azure_speech_region}.tts.speech.microsoft.com/"
                "cognitiveservices/avatar/relay/token/v1",
                headers={"Ocp-Apim-Subscription-Key": settings.azure_speech_key},
                timeout=20,
            )
            response.raise_for_status()
            ice = response.json()
            return {"mode": "webrtc", "provider": "azure", "ice": ice,
                    "character": settings.azure_avatar_character,
                    "style": settings.azure_avatar_style,
                    "voice": (settings.tts_voice_ar if language.startswith("ar")
                              else settings.tts_voice_en),
                    "language": language}
        except Exception as exc:  # noqa: BLE001
            log.warning("azure avatar relay failed, degrading to static: %s", exc)
            payload = self._fallback.create_session(language)
            payload["degraded_from"] = "azure"
            return payload

    def speak(self, session_id: str, text: str) -> Dict[str, Any]:
        # Azure avatar speech is driven client-side over the negotiated peer
        # connection; the server only issues the relay token.
        return {"mode": "webrtc", "text": text, "delivered": True}

    def close_session(self, session_id: str) -> Dict[str, Any]:
        return {"closed": True}


def get_avatar() -> Provider:
    if settings.avatar_provider == "heygen" and settings.heygen_api_key:
        return HeyGenAvatar()
    if settings.avatar_provider == "azure" and settings.azure_speech_key:
        return AzureAvatar()
    return StaticAvatar()