"""Document intelligence: extract, summarise, answer.

Deliberately no RAG. At this corpus size, chunking and vector search cost days
of work, add retrieval-miss failures, and buy nothing — the whole document fits
in a modern context window. Extract once, cache, pass the full text.

Arabic PDFs break naive extractors on right-to-left ordering and ligatures, and
scanned reports have no text layer at all. Azure Document Intelligence handles
both; pypdf is the offline fallback for born-digital English documents.

Note: handwritten Arabic OCR is not supported by any current service. Keep
handwritten scans out of the demonstration corpus.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict

import httpx

from app.config import settings
from app.providers.base import Provider, ProviderUnavailable

log = logging.getLogger("zai.documents")


def detect_language(text: str) -> str:
    """Code-side language detection. Never delegated to the model."""
    arabic = sum(1 for ch in text[:2000] if "\u0600" <= ch <= "\u06FF")
    latin = sum(1 for ch in text[:2000] if ch.isascii() and ch.isalpha())
    return "ar" if arabic > latin * 0.3 else "en"


class LocalExtractor(Provider):
    name = "local"
    kind = "documents"

    def extract(self, content: bytes, filename: str) -> Dict[str, Any]:
        if filename.lower().endswith(".txt"):
            text = content.decode("utf-8", errors="replace")
            return {"text": text, "pages": 1, "provider": "local"}
        try:
            import io
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(content))
            pages = [(p.extract_text() or "") for p in reader.pages]
            text = "\n\n".join(pages)
            if not text.strip():
                raise ProviderUnavailable(
                    "No text layer found. This is likely a scanned document — "
                    "configure Azure Document Intelligence for OCR."
                )
            return {"text": text, "pages": len(pages), "provider": "local"}
        except ProviderUnavailable:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ProviderUnavailable(f"Local extraction failed: {exc}") from exc


class AzureDocumentIntelligence(Provider):
    """Layout model. Handles Arabic print OCR and scanned pages."""

    name = "azure"
    kind = "documents"

    def __init__(self) -> None:
        self._fallback = LocalExtractor()

    def extract(self, content: bytes, filename: str) -> Dict[str, Any]:
        if not (settings.azure_docint_endpoint and settings.azure_docint_key):
            return self._fallback.extract(content, filename)
        try:
            endpoint = settings.azure_docint_endpoint.rstrip("/")
            # Language is deliberately NOT specified: the universal models
            # auto-detect, and forcing a locale can return incomplete text.
            submit = httpx.post(
                f"{endpoint}/documentintelligence/documentModels/"
                "prebuilt-layout:analyze?api-version=2024-11-30&outputContentFormat=markdown",
                headers={"Ocp-Apim-Subscription-Key": settings.azure_docint_key,
                         "Content-Type": "application/octet-stream"},
                content=content, timeout=60,
            )
            submit.raise_for_status()
            operation = submit.headers["operation-location"]

            for _ in range(settings.docint_poll_attempts):
                time.sleep(settings.docint_poll_interval_seconds)
                poll = httpx.get(operation,
                                 headers={"Ocp-Apim-Subscription-Key": settings.azure_docint_key},
                                 timeout=30).json()
                if poll.get("status") == "succeeded":
                    result = poll["analyzeResult"]
                    return {"text": result.get("content", ""),
                            "pages": len(result.get("pages", [])),
                            "provider": "azure"}
                if poll.get("status") == "failed":
                    raise ProviderUnavailable("Azure Document Intelligence reported failure")
            raise ProviderUnavailable("Azure Document Intelligence timed out")
        except ProviderUnavailable:
            raise
        except Exception as exc:  # noqa: BLE001
            log.warning("azure extraction failed, falling back to local: %s", exc)
            return self._fallback.extract(content, filename)


def get_extractor() -> Provider:
    if settings.document_provider == "azure" and settings.azure_docint_key:
        return AzureDocumentIntelligence()
    return LocalExtractor()
