"""Provider abstraction.

Every external dependency (LLM, speech, avatar, document AI) sits behind an
interface with at least two implementations: a real vendor and a deterministic
mock. Three consequences:

  1. `docker compose up` yields a complete working demo with zero API keys.
  2. Any vendor can be swapped without touching application code.
  3. Vendor outage during the executive demonstration degrades to the mock
     rather than failing the product.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

log = logging.getLogger("zai.providers")


class ProviderUnavailable(RuntimeError):
    """Raised when a provider is configured but cannot service a request."""


class Provider:
    name: str = "base"
    kind: str = "base"

    def health(self) -> Dict[str, Any]:
        return {"kind": self.kind, "provider": self.name, "ready": True}
