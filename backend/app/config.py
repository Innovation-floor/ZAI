"""Configuration. Twelve-factor: everything from environment, nothing in code."""
from __future__ import annotations

from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore",
                                      case_sensitive=False)

    # --- application -------------------------------------------------------
    app_name: str = "ZAI Executive Intelligence Platform"
    environment: str = "development"
    log_level: str = "INFO"
    log_format: str = "json"
    cors_origins: str = "*"
    session_ttl_seconds: int = 7200
    dataset_size: int = 210

    # --- language model ----------------------------------------------------
    llm_provider: str = "mock"          # mock | ollama | anthropic
    # When true, refuse to start if the configured LLM is unreachable rather
    # than silently degrading to the deterministic planner. Use this in any
    # environment where "it answered, but with the mock" would go unnoticed.
    llm_strict: bool = False
    llm_model: str = "claude-sonnet-4-6"
    llm_timeout_seconds: int = 30
    anthropic_api_key: str = ""
    anthropic_base_url: str = "https://api.anthropic.com"
    # MUST fit inside the writer model's context window. 120k chars is roughly
    # 30k tokens; with a 16k context Ollama silently truncates and the summary
    # is generated from a fragment. Keep this at roughly num_ctx * 2.5 chars.
    document_context_chars: int = 40_000

    # --- ollama (self-hosted) ----------------------------------------------
    ollama_base_url: str = "http://host.docker.internal:11434"
    # Planner and writer are split on purpose: planning is a small structured
    # task that must be fast; summarising is a large task that can be slower.
    ollama_planner_model: str = "llama3.2:3b"
    ollama_writer_model: str = "llama3.3:70b"
    # Ollama defaults to a 2048-token context, which silently truncates the
    # vocabulary block. This must be raised or planning degrades to nonsense.
    ollama_num_ctx: int = 8192
    ollama_writer_num_ctx: int = 16384
    # The planner sits in the voice latency budget: fail fast and fall back
    # rather than blocking the turn for two minutes.
    ollama_planner_timeout_seconds: int = 25
    ollama_timeout_seconds: int = 120
    ollama_keep_alive: str = "30m"
    # Reasoning models (qwen3.x, gpt-oss) emit long chain-of-thought before
    # answering. For a structured planning task that is pure latency, and it
    # fights the JSON grammar. Disabled by default.
    ollama_think: bool = False
    ollama_planner_max_tokens: int = 400
    ollama_writer_max_tokens: int = 900

    # --- azure openai (Azure OpenAI-compatible, also works with Core42) ----
    azure_openai_api_key: str = ""
    azure_openai_base_url: str = "https://your-resource.openai.azure.com/openai/deployments"
    azure_openai_model: str = "gpt-4o"
    azure_openai_api_version: str = "2023-05-15"
    azure_openai_max_tokens: int = 600

    # --- speech ------------------------------------------------------------
    stt_provider: str = "browser"       # browser | azure | deepgram | mock
    stt_timeout_seconds: int = 30
    stt_max_boost_terms: int = 90
    deepgram_api_key: str = ""
    deepgram_model: str = "nova-3"

    tts_provider: str = "browser"       # browser | azure
    tts_timeout_seconds: int = 30
    tts_voice_ar: str = "ar-AE-FatimaNeural"
    tts_voice_en: str = "en-GB-SoniaNeural"

    azure_speech_key: str = ""
    azure_speech_region: str = ""

    # --- avatar ------------------------------------------------------------
    avatar_provider: str = "static"     # static | heygen | azure
    avatar_display_name: str = "ZAI"
    avatar_portrait_url: str = "/assets/avatar.svg"
    # Optional looping video avatar. Drop two short MP4s into
    # frontend/static/assets and set these to use a real presenter without a
    # streaming vendor. Leaving them blank uses the animated SVG avatar.
    avatar_idle_video: str = ""
    avatar_speaking_video: str = ""
    # Photo presenter: animates the mouth region of a still portrait in the
    # browser. Gives the approved deck likeness with no video generation and no
    # vendor. Coordinates are fractions of the image, so they need tuning once
    # per portrait — see AVATAR_MOUTH_* below.
    # 3D digital human. Point this at a glTF/GLB carrying ARKit or Oculus
    # viseme morph targets (Ready Player Me and PlayerZero both ship them).
    # Takes priority over video and photo modes when set.
    avatar_model: str = ""
    avatar_model_zoom: float = 1.0
    avatar_model_offset_y: float = 0.0
    avatar_photo: str = "/assets/presenter.jpg"
    avatar_mouth_x: float = 0.505
    avatar_mouth_y: float = 0.567
    avatar_mouth_w: float = 0.155
    avatar_mouth_h: float = 0.058
    avatar_mouth_gain: float = 0.55
    heygen_api_key: str = ""
    heygen_avatar_id: str = "default"
    heygen_quality: str = "high"
    azure_avatar_character: str = "lisa"
    azure_avatar_style: str = "casual-sitting"

    # --- documents ---------------------------------------------------------
    document_provider: str = "local"    # local | azure
    azure_docint_endpoint: str = ""
    azure_docint_key: str = ""
    docint_poll_attempts: int = 30
    docint_poll_interval_seconds: float = 1.5
    max_upload_mb: int = 25

    @property
    def cors_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()