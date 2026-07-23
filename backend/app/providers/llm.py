"""Language understanding: natural language -> filter delta + narrative.

The model is asked for a *structured instruction*, never for figures. See
app/core/aggregates.py for where numbers actually come from.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List

import httpx

from app.config import settings
from app.core.state import DIMENSIONS, QueryState
from app.data.repository import alias_index, vocabulary
from app.providers.base import Provider

log = logging.getLogger("zai.llm")

SYSTEM_PROMPT = """You are the query planner for ZAI, an executive humanitarian intelligence platform.

Convert the executive's question into a JSON instruction. You must NEVER state counts, budgets, beneficiary numbers or percentages — the application computes all figures. Your narrative must describe only what is being shown.

Respond with ONLY a JSON object, no markdown fences, matching:
{
  "intent": "filter" | "compare" | "detail" | "brief" | "greeting" | "unknown",
  "delta": { ... },
  "reset": false,
  "compare": {"dimension": "country", "values": ["Jordan", "Egypt"]},
  "narrative_en": "one short sentence describing what is now shown",
  "narrative_ar": "نفس الجملة بالعربية",
  "map_action": "fit" | "world" | "none"
}

Delta rules:
- Each dimension takes {"op": "set"|"add"|"remove"|"clear", "values": [...]}
- Use "set" when the executive names a new value for a dimension. This REPLACES any previous value for that dimension.
- Use "add" only when the executive explicitly asks to include something in addition.
- Use "clear" when they ask to remove a constraint or see everything.
- Omit a dimension entirely if the question does not mention it. Omitted dimensions keep their current value — this is how follow-up questions accumulate.
- "reset": true only when they ask to start over or show the whole portfolio.
- Non-dimension keys: "year_from" (int|null), "year_to" (int|null), "attention_only" (bool), "text" (string|null).

Values MUST come verbatim from the allowed vocabulary. Never invent a value."""


SUMMARY_PROMPT = """You are briefing a chief executive. Summarise the document in {lang}.

Rules:
- Six sentences maximum.
- Lead with the single most decision-relevant point.
- Plain prose. No headings, no bullet lists, no preamble such as "This document...".
- Use only figures that appear in the text. Never estimate or calculate.
- Write for someone with two minutes, not two hours."""

ANSWER_PROMPT = """You are answering a chief executive's question about a document, in {lang}.

Rules:
- State the answer in the FIRST sentence. Three sentences maximum in total.
- Never show your working. No step-by-step arithmetic, no enumerated lists of
  intermediate values, no "to calculate this we need to...". Give the result only.
- No preamble. Do not restate the question.
- If the document does not contain the answer, say exactly that in one sentence.
- If the answer is a number, give the number and its basis in one clause,
  for example: "Average completion is 54% across the 21 projects."."""


def _lang_name(language: str) -> str:
    return "Arabic" if language.startswith("ar") else "English"


def _vocab_block() -> str:
    vocab = vocabulary()
    lines = [f"- {dim}: {', '.join(values)}" for dim, values in vocab.items()]
    return "ALLOWED VOCABULARY\n" + "\n".join(lines)


THINK_BLOCK = re.compile(r"<(think|thinking|reasoning)>.*?</\1>", re.DOTALL | re.IGNORECASE)


def strip_reasoning(text: str) -> str:
    """Remove chain-of-thought blocks that reasoning models emit inline.

    Without this, thinking output leaks into narratives and gets spoken aloud.
    """
    text = THINK_BLOCK.sub("", text)
    # An unterminated opening tag means the model ran out of tokens mid-thought.
    cut = re.split(r"<(?:think|thinking|reasoning)>", text, maxsplit=1, flags=re.IGNORECASE)
    return cut[0].strip() if len(cut) > 1 and "{" in cut[0] else text.strip()


def _extract_json(text: str) -> Dict[str, Any]:
    text = strip_reasoning(text)
    text = text.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object in model response")
    return json.loads(text[start:end + 1])


class MockLLM(Provider):
    """Deterministic keyword planner.

    Not a toy: it covers the entire scripted demonstration and runs offline in
    a few milliseconds. It is also what Executive Demo Mode replays, so the
    demonstration path never depends on a network call.
    """

    name = "mock"
    kind = "llm"

    def plan(self, question: str, state: QueryState,
             history: List[Dict[str, str]]) -> Dict[str, Any]:
        q = question.lower().strip()
        idx = alias_index()
        delta: Dict[str, Any] = {}
        matched: List[str] = []

        # longest surface form first, so "middle east" beats "east"
        for surface in sorted(idx, key=len, reverse=True):
            if not surface:
                continue
            pattern = r"(?<!\w)" + re.escape(surface) + r"(?!\w)"
            if re.search(pattern, q) or surface in question:
                dim, canonical = idx[surface]
                if dim in delta:
                    continue
                delta[dim] = {"op": "set", "values": [canonical]}
                matched.append(canonical)

        year = re.search(r"\b(20\d{2})\b", q)
        if year:
            y = int(year.group(1))
            delta["year_from"], delta["year_to"] = y, y

        if any(w in q for w in ("attention", "risk", "concern", "انتباه", "خطر")):
            delta["attention_only"] = True

        reset = any(w in q for w in ("everything", "all projects", "whole portfolio",
                                     "start over", "reset", "الكل", "كل المشاريع"))

        intent = "filter"
        compare_spec = None
        if any(w in q for w in ("compare", "versus", " vs ", "قارن")):
            countries = [c for c in vocabulary()["country"] if c.lower() in q]
            if len(countries) >= 2:
                intent = "compare"
                compare_spec = {"dimension": "country", "values": countries[:2]}
                delta.pop("country", None)
        elif any(w in q for w in ("brief", "today", "morning", "موجز", "إحاطة")):
            intent = "brief"
        elif any(w in q for w in ("hello", "hi ", "welcome", "مرحبا", "السلام")):
            intent = "greeting"

        if matched:
            shown = " and ".join(matched)
            en = f"Showing {shown} projects."
            ar = f"عرض مشاريع {shown}."
        elif reset:
            en, ar = "Showing the entire portfolio.", "عرض المحفظة بالكامل."
        else:
            en, ar = "Updating the view.", "تحديث العرض."

        return {
            "intent": intent, "delta": delta, "reset": reset,
            "compare": compare_spec, "narrative_en": en, "narrative_ar": ar,
            "map_action": "world" if reset else ("fit" if delta else "none"),
            "_source": "mock",
        }

    def summarise_document(self, text: str, language: str) -> str:
        words = len(text.split())
        head = " ".join(text.split()[:60])
        return (f"[Mock summary — configure an LLM provider for real summaries] "
                f"Document contains approximately {words} words. Opening extract: {head}...")

    # NOTE: the mock cannot summarise. Its output is deliberately marked so a
    # fallback is never mistaken for a poor-quality real summary.

    def answer_document(self, text: str, question: str, language: str) -> str:
        needle = question.lower().split()
        best = ""
        for para in text.split("\n"):
            score = sum(1 for w in needle if w in para.lower())
            if score > 0 and len(para) > len(best):
                best = para
        return best[:600] if best else "[Mock] No matching passage found in the document."


class AnthropicLLM(Provider):
    name = "anthropic"
    kind = "llm"

    def __init__(self) -> None:
        self._fallback = MockLLM()

    def _call(self, system: str, user: str, max_tokens: int = 1200) -> str:
        response = httpx.post(
            f"{settings.anthropic_base_url}/v1/messages",
            headers={
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": settings.llm_model,
                "max_tokens": max_tokens,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            },
            timeout=settings.llm_timeout_seconds,
        )
        response.raise_for_status()
        blocks = response.json().get("content", [])
        return "".join(b.get("text", "") for b in blocks if b.get("type") == "text")

    def plan(self, question: str, state: QueryState,
             history: List[Dict[str, str]]) -> Dict[str, Any]:
        turns = "\n".join(f"{h['role']}: {h['content']}" for h in history[-6:])
        user = (
            f"{_vocab_block()}\n\n"
            f"CURRENT VIEW: {state.describe()}\n\n"
            f"RECENT CONVERSATION:\n{turns or '(none)'}\n\n"
            f"EXECUTIVE QUESTION: {question}"
        )
        try:
            return _extract_json(self._call(SYSTEM_PROMPT, user))
        except Exception as exc:  # noqa: BLE001 - degrade, never fail the turn
            log.warning("llm plan failed, falling back to mock: %s", exc)
            return self._fallback.plan(question, state, history)

    def summarise_document(self, text: str, language: str) -> str:
        system = SUMMARY_PROMPT.format(lang=_lang_name(language))
        try:
            return self._call(system, text[:settings.document_context_chars])
        except Exception as exc:  # noqa: BLE001
            log.warning("llm summarise failed: %s", exc)
            return self._fallback.summarise_document(text, language)

    def answer_document(self, text: str, question: str, language: str) -> str:
        system = ANSWER_PROMPT.format(lang=_lang_name(language))
        user = f"DOCUMENT:\n{text[:settings.document_context_chars]}\n\nQUESTION: {question}"
        try:
            return self._call(system, user)
        except Exception as exc:  # noqa: BLE001
            log.warning("llm document answer failed: %s", exc)
            return self._fallback.answer_document(text, question, language)


class AzureOpenAILLM(Provider):
    """Azure OpenAI-compatible API (also works with Core42, AI21, etc.).

    Uses the Azure chat completions protocol with ``api-key`` header auth.
    Configure via AZURE_OPENAI_* variables in .env.
    """

    name = "azure"
    kind = "llm"

    def __init__(self) -> None:
        self._fallback = MockLLM()
        self._base = settings.azure_openai_base_url.rstrip("/")
        self._model = settings.azure_openai_model
        self._api_version = settings.azure_openai_api_version

    def _chat(self, system: str, user: str, max_tokens: int = 1200) -> str:
        url = (f"{self._base}/{self._model}/chat/completions"
               f"?api-version={self._api_version}")
        response = httpx.post(
            url,
            headers={
                "api-key": settings.azure_openai_api_key,
                "Content-Type": "application/json",
            },
            json={
                "stream": False,
                "temperature": 0.1,
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            timeout=settings.llm_timeout_seconds,
        )
        response.raise_for_status()
        choices = response.json().get("choices", [])
        if not choices:
            raise ValueError("Azure OpenAI returned no choices")
        return choices[0]["message"]["content"]

    def health(self) -> Dict[str, Any]:
        try:
            self._chat("Reply OK", "health check", max_tokens=4)
            ready = True
        except Exception:  # noqa: BLE001
            ready = False
        return {
            "kind": self.kind, "provider": self.name, "ready": ready,
            "base_url": self._base, "model": self._model,
        }

    def plan(self, question: str, state: QueryState,
             history: List[Dict[str, str]]) -> Dict[str, Any]:
        turns = "\n".join(f"{h['role']}: {h['content']}" for h in history[-6:])
        user = (
            f"{_vocab_block()}\n\n"
            f"CURRENT VIEW: {state.describe()}\n\n"
            f"RECENT CONVERSATION:\n{turns or '(none)'}\n\n"
            f"EXECUTIVE QUESTION: {question}"
        )
        try:
            raw = self._chat(SYSTEM_PROMPT, user,
                             max_tokens=settings.azure_openai_max_tokens)
            plan = _extract_json(raw)
            plan["_source"] = f"azure:{self._model}"
            return plan
        except Exception as exc:  # noqa: BLE001
            log.warning("azure openai plan failed, falling back to mock: %s", exc)
            plan = self._fallback.plan(question, state, history)
            plan["_source"] = "mock (azure unavailable)"
            return plan

    def summarise_document(self, text: str, language: str) -> str:
        system = SUMMARY_PROMPT.format(lang=_lang_name(language))
        try:
            return self._chat(system, text[:settings.document_context_chars])
        except Exception as exc:  # noqa: BLE001
            log.warning("azure openai summarise failed: %s", exc)
            return self._fallback.summarise_document(text, language)

    def answer_document(self, text: str, question: str, language: str) -> str:
        system = ANSWER_PROMPT.format(lang=_lang_name(language))
        user = f"DOCUMENT:\n{text[:settings.document_context_chars]}\n\nQUESTION: {question}"
        try:
            return self._chat(system, user)
        except Exception as exc:  # noqa: BLE001
            log.warning("azure openai document answer failed: %s", exc)
            return self._fallback.answer_document(text, question, language)




# ---------------------------------------------------------------------------
# Ollama (self-hosted)
# ---------------------------------------------------------------------------

def _plan_schema() -> Dict[str, Any]:
    """JSON schema handed to Ollama so the planner cannot emit malformed output.

    Ollama constrains generation to the schema, which removes almost all of the
    JSON-parsing failures that smaller local models otherwise produce. The
    delta itself is still validated in core/state.py — the schema guarantees
    shape, not that the values exist in the vocabulary.
    """
    dim_op = {
        "type": "object",
        "properties": {
            "op": {"type": "string", "enum": ["set", "add", "remove", "clear"]},
            "values": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["op"],
    }
    return {
        "type": "object",
        "properties": {
            "intent": {"type": "string",
                       "enum": ["filter", "compare", "detail", "brief",
                                "greeting", "unknown"]},
            "delta": {
                "type": "object",
                "properties": {
                    **{dim: dim_op for dim in DIMENSIONS},
                    "year_from": {"type": ["integer", "null"]},
                    "year_to": {"type": ["integer", "null"]},
                    "attention_only": {"type": "boolean"},
                    "text": {"type": ["string", "null"]},
                },
            },
            "reset": {"type": "boolean"},
            "compare": {
                "type": ["object", "null"],
                "properties": {
                    "dimension": {"type": "string"},
                    "values": {"type": "array", "items": {"type": "string"}},
                },
            },
            "narrative_en": {"type": "string"},
            "narrative_ar": {"type": "string"},
            "map_action": {"type": "string", "enum": ["fit", "world", "none"]},
        },
        "required": ["intent", "delta", "narrative_en", "map_action"],
    }


class OllamaLLM(Provider):
    """Self-hosted models via the Ollama chat API.

    Two models are used deliberately:
      planner  small and fast - the planning task is easy and sits directly in
               the voice latency budget
      writer   large and slower - document summaries and answers, where quality
               matters and a few extra seconds are acceptable

    Set OLLAMA_PLANNER_MODEL and OLLAMA_WRITER_MODEL to the same value to use
    one model for both.
    """

    name = "ollama"
    kind = "llm"

    def __init__(self) -> None:
        self._fallback = MockLLM()
        self._base = settings.ollama_base_url.rstrip("/")

    def _chat(self, system: str, user: str, *, model: str, num_ctx: int,
              max_tokens: int, schema: Dict[str, Any] | None = None,
              timeout: float | None = None) -> str:
        # "/no_think" is Qwen's documented soft switch; the "think" field is
        # Ollama's native one. Both are sent because model support varies.
        if not settings.ollama_think:
            system = f"{system}\n\n/no_think"

        body: Dict[str, Any] = {
            "model": model,
            "stream": False,
            "keep_alive": settings.ollama_keep_alive,
            "think": settings.ollama_think,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "options": {
                "temperature": 0.1,
                "num_ctx": num_ctx,
                "num_predict": max_tokens,
            },
        }
        if schema is not None:
            body["format"] = schema

        url = f"{self._base}/api/chat"
        timeout = timeout or settings.ollama_timeout_seconds

        response = httpx.post(url, json=body, timeout=timeout)
        if response.status_code == 400:
            # Older Ollama builds and non-reasoning models reject "think".
            body.pop("think", None)
            response = httpx.post(url, json=body, timeout=timeout)
        response.raise_for_status()
        return response.json()["message"]["content"]

    def available_models(self) -> List[str]:
        try:
            tags = httpx.get(f"{self._base}/api/tags", timeout=5).json()
            return [m["name"] for m in tags.get("models", [])]
        except Exception:  # noqa: BLE001
            return []

    def health(self) -> Dict[str, Any]:
        models = self.available_models()
        return {
            "kind": self.kind, "provider": self.name, "ready": bool(models),
            "base_url": self._base, "models": models,
            "planner": settings.ollama_planner_model,
            "writer": settings.ollama_writer_model,
        }

    def plan(self, question: str, state: QueryState,
             history: List[Dict[str, str]]) -> Dict[str, Any]:
        turns = "\n".join(f"{h['role']}: {h['content']}" for h in history[-6:])
        user = (
            f"{_vocab_block()}\n\n"
            f"CURRENT VIEW: {state.describe()}\n\n"
            f"RECENT CONVERSATION:\n{turns or '(none)'}\n\n"
            f"EXECUTIVE QUESTION: {question}"
        )
        try:
            raw = self._chat(SYSTEM_PROMPT, user,
                             model=settings.ollama_planner_model,
                             num_ctx=settings.ollama_num_ctx,
                             max_tokens=settings.ollama_planner_max_tokens,
                             schema=_plan_schema(),
                             timeout=settings.ollama_planner_timeout_seconds)
            plan = _extract_json(raw)
            plan["_source"] = f"ollama:{settings.ollama_planner_model}"
            return plan
        except Exception as exc:  # noqa: BLE001 - degrade, never fail the turn
            log.warning("ollama plan failed after %ss, falling back to keyword "
                        "planner: %s", settings.ollama_planner_timeout_seconds, exc)
            plan = self._fallback.plan(question, state, history)
            plan["_source"] = "mock (ollama unavailable)"
            return plan

    def summarise_document(self, text: str, language: str) -> str:
        system = SUMMARY_PROMPT.format(lang=_lang_name(language))
        try:
            return strip_reasoning(self._chat(
                system, text[:settings.document_context_chars],
                model=settings.ollama_writer_model,
                num_ctx=settings.ollama_writer_num_ctx,
                max_tokens=settings.ollama_writer_max_tokens))
        except Exception as exc:  # noqa: BLE001
            log.warning("ollama summarise failed: %s", exc)
            return self._fallback.summarise_document(text, language)

    def answer_document(self, text: str, question: str, language: str) -> str:
        system = ANSWER_PROMPT.format(lang=_lang_name(language))
        user = f"DOCUMENT:\n{text[:settings.document_context_chars]}\n\nQUESTION: {question}"
        try:
            return strip_reasoning(self._chat(
                system, user,
                model=settings.ollama_writer_model,
                num_ctx=settings.ollama_writer_num_ctx,
                max_tokens=settings.ollama_writer_max_tokens))
        except Exception as exc:  # noqa: BLE001
            log.warning("ollama document answer failed: %s", exc)
            return self._fallback.answer_document(text, question, language)


def get_llm() -> Provider:
    if settings.llm_provider == "azure" and settings.azure_openai_api_key:
        provider = AzureOpenAILLM()
        info = provider.health()
        if info["ready"]:
            log.info("azure openai ready: model=%s", settings.azure_openai_model)
            return provider
        message = f"Azure OpenAI unreachable at {settings.azure_openai_base_url}."
        if settings.llm_strict:
            raise RuntimeError(message)
        log.warning("%s Using mock planner.", message)
        return MockLLM()
    if settings.llm_provider == "ollama":
        provider = OllamaLLM()
        models = provider.available_models()
        if models:
            for role, wanted in (("planner", settings.ollama_planner_model),
                                 ("writer", settings.ollama_writer_model)):
                if wanted not in models:
                    log.warning("ollama %s model '%s' not pulled; available: %s",
                                role, wanted, ", ".join(models) or "none")
            return provider
        message = (f"Ollama unreachable at {settings.ollama_base_url}. "
                   "Check the daemon is running and started with OLLAMA_HOST=0.0.0.0.")
        if settings.llm_strict:
            raise RuntimeError(message)
        log.warning("%s Using mock planner.", message)
        return MockLLM()
    if settings.llm_provider == "anthropic" and settings.anthropic_api_key:
        return AnthropicLLM()
    if settings.llm_provider != "mock":
        message = (f"llm_provider={settings.llm_provider} but no credentials are present.")
        if settings.llm_strict:
            raise RuntimeError(message)
        log.warning("%s Using mock planner.", message)
    return MockLLM()