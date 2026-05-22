"""OpenAI-compatible chat completion client using only the Python standard library."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMConfig:
    api_key: str
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"

    @classmethod
    def from_env(cls) -> "LLMConfig | None":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None
        return cls(
            api_key=api_key,
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        )


class OpenAICompatibleClient:
    """Minimal client for /chat/completions endpoints."""

    def __init__(self, config: LLMConfig) -> None:
        self.config = config

    def chat(self, messages: list[dict[str, str]], temperature: float = 0.4) -> str:
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature,
        }
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url=f"{self.config.base_url}/chat/completions",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"LLM request failed: HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"LLM request failed: {exc.reason}") from exc

        return data["choices"][0]["message"]["content"].strip()
